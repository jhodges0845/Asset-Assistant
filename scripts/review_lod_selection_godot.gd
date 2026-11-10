# SPDX-License-Identifier: GPL-3.0-or-later
# Rendering-enabled Godot: --path BUNDLE --script /absolute/this_script.gd
# Shared two-level scene builder and diagnostic verifier. Never rewrites GLBs.
extends SceneTree

func _initialize():
    call_deferred("review")

func fail(message):
    push_error(message)
    quit(1)

func review():
    var arguments = OS.get_cmdline_user_args()
    if arguments.size() > 1:
        fail("Supply at most one clip name after --")
        return
    var clip = arguments[0] if arguments.size() == 1 else ""
    await build_scene(clip)

func build_scene(clip, scene_path = "res://lod-selection-review.tscn", switch_distance = 0.0, diagnostic = true, loop_clip = false):
    var players = []
    var skeletons = []
    var output_path = "res://godot-lod-selection.json"
    if (diagnostic and FileAccess.file_exists(output_path)) or FileAccess.file_exists(scene_path):
        fail("Choose a bundle copy without an existing selection report or review scene")
        return
    var manifest = JSON.parse_string(FileAccess.get_file_as_string("res://lod-manifest.json"))
    if not manifest is Dictionary or not manifest.get("levels") is Array or manifest.levels.size() != 2:
        fail("Selection probe requires exactly two bundle levels")
        return
    var viewport = SubViewport.new()
    viewport.size = Vector2i(128, 128)
    viewport.own_world_3d = true
    viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    root.add_child(viewport)
    var camera = Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.near = 0.01
    camera.far = 1000.0
    viewport.add_child(camera)
    camera.current = true
    var setup = Node3D.new()
    setup.name = "LODSelectionReview"
    viewport.add_child(setup)
    var groups = []
    var bounds = AABB()
    var have_bounds = false
    for index in range(2):
        var level = manifest.levels[index]
        if int(level.index) != index or str(level.file).get_file() != level.file or not str(level.file).ends_with(".glb"):
            fail("Invalid level order or bundle path")
            return
        var document = GLTFDocument.new()
        var state = GLTFState.new()
        if document.append_from_file("res://" + level.file, state) != OK:
            fail("Cannot load bundle GLB")
            return
        var scene = document.generate_scene(state)
        if scene == null:
            fail("Cannot instantiate GLB")
            return
        setup.add_child(scene)
        var pending = [scene]
        var meshes = []
        var level_players = []
        var level_skeletons = []
        var triangles = 0
        while not pending.is_empty():
            var node = pending.pop_back()
            pending.append_array(node.get_children())
            if node is AnimationPlayer:
                node.stop()
                node.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
                level_players.append(node)
            if node is Skeleton3D:
                level_skeletons.append(node)
            if node is MeshInstance3D:
                meshes.append(node)
                var box = node.global_transform * node.get_aabb()
                bounds = bounds.merge(box) if have_bounds else box
                have_bounds = true
                for surface in range(node.mesh.get_surface_count()):
                    if node.mesh.surface_get_primitive_type(surface) != Mesh.PRIMITIVE_TRIANGLES:
                        fail("Expected triangle surfaces")
                        return
                    var arrays = node.mesh.surface_get_arrays(surface)
                    var count = arrays[Mesh.ARRAY_INDEX].size()
                    triangles += (count if count else arrays[Mesh.ARRAY_VERTEX].size()) / 3
                if diagnostic:
                    var material = StandardMaterial3D.new()
                    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
                    material.albedo_color = Color.RED if index == 0 else Color.GREEN
                    material.cull_mode = BaseMaterial3D.CULL_DISABLED
                    node.material_override = material
        if meshes.size() != int(level.mesh_count) or triangles != int(level.triangles):
            fail("Imported counts differ from manifest")
            return
        if clip != "":
            if level_players.size() != 1 or level_skeletons.size() != 1 or not level_players[0].has_animation(clip):
                fail("Each level requires one skeleton and one player with the requested clip")
                return
            var player = level_players[0]
            if player.get_animation(clip).length <= 0:
                fail("Clip must have positive duration")
                return
            player.play(clip)
            player.advance(0)
            players.append(player)
            skeletons.append(level_skeletons[0])
        groups.append(meshes)
    if not have_bounds or bounds.size.length() == 0:
        fail("Missing nonempty mesh bounds")
        return
    var center = bounds.get_center()
    var scale = maxf(bounds.size.length(), 1.0)
    var boundary = scale * 4.0 if diagnostic else switch_distance
    if not is_finite(boundary) or boundary <= 0:
        fail("Switch distance must be finite and positive")
        return
    camera.size = scale * 1.2
    camera.far = scale * 20.0
    # Shared world-space bounds avoid per-mesh centers changing switch distances.
    for index in range(2):
        for mesh in groups[index]:
            mesh.custom_aabb = mesh.global_transform.affine_inverse() * bounds
            mesh.visibility_range_begin = boundary if index == 1 else 0.0
            mesh.visibility_range_end = boundary if index == 0 else 0.0
            mesh.visibility_range_begin_margin = 0.0
            mesh.visibility_range_end_margin = 0.0
    # Persist and reload the configured diagnostic scene before measuring it.
    # Color overrides are deliberately diagnostic, not production materials.
    var group_paths = []
    for group in groups:
        var paths = []
        for mesh in group:
            paths.append(setup.get_path_to(mesh))
        group_paths.append(paths)
    var player_paths = []
    var skeleton_paths = []
    for index in range(players.size()):
        player_paths.append(setup.get_path_to(players[index]))
        skeleton_paths.append(setup.get_path_to(skeletons[index]))
    var pending_ownership = setup.get_children()
    while not pending_ownership.is_empty():
        var node = pending_ownership.pop_back()
        node.owner = setup
        pending_ownership.append_array(node.get_children())
    if not diagnostic and not players.is_empty():
        if not is_equal_approx(players[0].get_animation(clip).length, players[1].get_animation(clip).length):
            fail("Engine scene requires matching clip durations across levels")
            return
        viewport.remove_child(setup)
        for player in players:
            player.stop()
            player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_IDLE
            if loop_clip:
                player.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
            player.autoplay = clip
    setup.set_meta("lod_selection_review", {
        "version": 1, "diagnostic_materials": diagnostic, "clip": clip, "center": center, "scale": scale,
        "boundary": boundary, "group_paths": group_paths,
        "player_paths": player_paths, "skeleton_paths": skeleton_paths})
    var packed = PackedScene.new()
    if packed.pack(setup) != OK or ResourceSaver.save(packed, scene_path) != OK:
        fail("Cannot save configured LOD review scene")
        return
    setup.free()
    if not diagnostic:
        print("PASS: saved material-preserving engine scene: ", scene_path)
        quit(0)
        return
    await verify_saved_scene(scene_path, output_path, viewport, camera)

func verify_saved_scene(scene_path, output_path, viewport, camera):
    if FileAccess.file_exists(output_path):
        fail("Choose a new report path")
        return
    var restored_resource = ResourceLoader.load(scene_path, "PackedScene", ResourceLoader.CACHE_MODE_IGNORE)
    if not restored_resource is PackedScene:
        fail("Cannot reload configured LOD review scene")
        return
    var setup = restored_resource.instantiate()
    viewport.add_child(setup)
    var metadata = setup.get_meta("lod_selection_review", {})
    if not metadata is Dictionary or metadata.get("version") != 1:
        fail("Saved scene lacks supported LOD review metadata")
        return
    for key in ["clip", "center", "scale", "boundary", "group_paths", "player_paths", "skeleton_paths"]:
        if not metadata.has(key):
            fail("Incomplete saved LOD review metadata")
            return
    var clip = metadata.clip
    var center = metadata.center
    var scale = metadata.scale
    var boundary = metadata.boundary
    var group_paths = metadata.group_paths
    var player_paths = metadata.player_paths
    var skeleton_paths = metadata.skeleton_paths
    if not center is Vector3 or not center.is_finite() or not is_finite(scale) or scale <= 0 or not is_finite(boundary) or boundary <= 0:
        fail("Invalid saved camera bounds")
        return
    if not group_paths is Array or group_paths.size() != 2 or not player_paths is Array or not skeleton_paths is Array or player_paths.size() != skeleton_paths.size():
        fail("Invalid saved level paths")
        return
    if (clip != "" and player_paths.size() != 2) or (clip == "" and not player_paths.is_empty()):
        fail("Saved clip and player paths disagree")
        return
    camera.size = scale * 1.2
    camera.far = scale * 20.0
    var groups = []
    var players = []
    var skeletons = []
    var pose_signatures = [[], []]
    for index in range(group_paths.size()):
        var group = []
        if not group_paths[index] is Array or group_paths[index].is_empty():
            fail("Empty saved mesh group")
            return
        for path in group_paths[index]:
            var mesh = setup.get_node_or_null(path)
            if not mesh is MeshInstance3D or mesh.mesh == null:
                fail("Saved LOD mesh was not restored")
                return
            var begin = boundary if index == 1 else 0.0
            var end = boundary if index == 0 else 0.0
            if not is_equal_approx(mesh.visibility_range_begin, begin) or not is_equal_approx(mesh.visibility_range_end, end):
                fail("Saved LOD visibility ranges changed")
                return
            if not metadata.get("diagnostic_materials", true):
                if mesh.material_override != null:
                    fail("Engine scene unexpectedly contains a material override")
                    return
                # Diagnostic colors affect only this loaded verification instance.
                var material = StandardMaterial3D.new()
                material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
                material.albedo_color = Color.RED if index == 0 else Color.GREEN
                material.cull_mode = BaseMaterial3D.CULL_DISABLED
                mesh.material_override = material
            group.append(mesh)
        groups.append(group)
    for index in range(player_paths.size()):
        var player = setup.get_node_or_null(player_paths[index])
        var skeleton = setup.get_node_or_null(skeleton_paths[index])
        if not player is AnimationPlayer or not skeleton is Skeleton3D or not player.has_animation(clip):
            fail("Saved LOD rig or clip was not restored")
            return
        if not metadata.get("diagnostic_materials", true) and (player.autoplay != clip or not player.is_playing()):
            fail("Engine scene did not start its configured clip")
            return
        player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
        player.play(clip)
        player.advance(0)
        players.append(player)
        skeletons.append(skeleton)
    var results = []
    var phases = [0.0] if clip == "" else [0.0, 0.25, 0.5, 0.75]
    for phase in phases:
        for index in range(players.size()):
            players[index].seek(players[index].get_animation(clip).length * phase, true)
            skeletons[index].force_update_all_bone_transforms()
            var signature = []
            for bone in range(skeletons[index].get_bone_count()):
                signature.append(skeletons[index].get_bone_global_pose(bone))
            pose_signatures[index].append(str(signature))
        for multiplier in [0.8, 0.99, 1.01, 1.2, 1.01, 0.99, 0.8]:
            camera.position = center + Vector3(0, 0, boundary * multiplier)
            camera.look_at(center)
            for frame in range(4):
                await process_frame
                await RenderingServer.frame_post_draw
            var image = viewport.get_texture().get_image()
            if image == null or image.is_empty():
                fail("Rendering unavailable: no viewport image")
                return
            var red = 0
            var green = 0
            for y in range(image.get_height()):
                for x in range(image.get_width()):
                    var color = image.get_pixel(x, y)
                    red += int(color.r > 0.5 and color.g < 0.2 and color.b < 0.2)
                    green += int(color.g > 0.5 and color.r < 0.2 and color.b < 0.2)
            var expected = 0 if multiplier < 1 else 1
            var mismatch = (red < 20 or green != 0) if expected == 0 else (green < 20 or red != 0)
            if mismatch:
                fail("Rendered level mismatch: red=%s green=%s expected=%s" % [red, green, expected])
                return
            results.append({"phase": phase, "distance": boundary * multiplier, "expected_level": expected, "red_pixels": red, "green_pixels": green})
    if clip != "":
        for signatures in pose_signatures:
            if signatures.all(func(value): return value == signatures[0]):
                fail("Requested clip did not change sampled bone poses")
                return
    var output = FileAccess.open(output_path, FileAccess.WRITE)
    output.store_string(JSON.stringify({"scope": "Sampled phase-synchronized distance selection; not continuous transition or visual-quality acceptance", "clip": clip if clip != "" else "rest", "scene_reloaded": true, "scene_file": scene_path, "godot_version": Engine.get_version_info().string, "samples": results}, "  "))
    output.close()
    print("PASS: reloaded scene rendered LOD selection across phases and boundary approach/retreat")
    quit(0)
