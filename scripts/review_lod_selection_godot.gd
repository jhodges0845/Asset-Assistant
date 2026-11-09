# SPDX-License-Identifier: GPL-3.0-or-later
# Rendering-enabled Godot: --path BUNDLE --script /absolute/this_script.gd
# Two-level diagnostic only. Never rewrites GLBs or their exchange manifest.
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
    var players = []
    var skeletons = []
    var pose_signatures = [[], []]
    var output_path = "res://godot-lod-selection.json"
    if FileAccess.file_exists(output_path):
        fail("Choose a bundle copy without an existing selection report")
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
        viewport.add_child(scene)
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
    var boundary = scale * 4.0
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
    output.store_string(JSON.stringify({"scope": "Sampled phase-synchronized distance selection; not continuous transition or visual-quality acceptance", "clip": clip if clip != "" else "rest", "godot_version": Engine.get_version_info().string, "samples": results}, "  "))
    output.close()
    print("PASS: rendered LOD selection across phases and boundary approach/retreat")
    quit(0)
