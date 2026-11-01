# SPDX-License-Identifier: GPL-3.0-or-later
# Godot --headless --path BUNDLE --script /absolute/path/to/this/script
extends SceneTree

func _initialize():
    call_deferred("review")

func fail(message):
    push_error(message)
    quit(1)

func review():
    var skin_review = "--skin" in OS.get_cmdline_user_args()
    if skin_review and DisplayServer.get_name() == "headless":
        fail("Skin review requires a rendering-enabled display; omit --headless")
        return
    var report_path = "res://godot-skin-lod-report.json"
    if skin_review:
        report_path = "res://godot-skin-lod-surface-report.json"
    if FileAccess.file_exists(report_path):
        DirAccess.remove_absolute(report_path)
    var expected = JSON.parse_string(FileAccess.get_file_as_string("res://expected.json"))
    var manifest = JSON.parse_string(FileAccess.get_file_as_string("res://lod-manifest.json"))
    if not expected is Dictionary or not manifest is Dictionary:
        fail("Missing fixture oracle or manifest")
        return
    var results = []
    for level in manifest.levels:
        var document = GLTFDocument.new()
        var state = GLTFState.new()
        if document.append_from_file("res://" + level.file, state) != OK:
            fail("Could not import " + level.file)
            return
        var asset = document.generate_scene(state, 800, false, false)
        root.add_child(asset)
        var players = asset.find_children("*", "AnimationPlayer", true, false)
        var skeletons = asset.find_children("*", "Skeleton3D", true, false)
        if players.size() != 1 or skeletons.size() != 1:
            fail("Expected one player and skeleton")
            return
        var player = players[0]
        player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
        var skeleton = skeletons[0]
        var bone = skeleton.find_bone(expected.bone)
        if bone < 0 or not player.has_animation("ProbeMotion"):
            fail("Missing bone or clip")
            return
        player.play("ProbeMotion")
        player.advance(0)
        var maximum = 0.0
        var maximum_axis = 0.0
        var maximum_skin = 0.0
        var bodies = asset.find_children("*", "MeshInstance3D", true, false)
        if skin_review and bodies.size() != 1:
            fail("Expected one skinned mesh")
            return
        for sample in expected.samples:
            player.seek(sample.seconds, true)
            skeleton.force_update_all_bone_transforms()
            var pose = skeleton.global_transform * skeleton.get_bone_global_pose(bone)
            var actual = pose.origin
            var reference = Vector3(sample.head[0], sample.head[1], sample.head[2])
            maximum = max(maximum, actual.distance_to(reference))
            for axis in range(3):
                var row = sample.axes[axis]
                var reference_axis = Vector3(row[0], row[1], row[2])
                maximum_axis = max(maximum_axis, pose.basis[axis].distance_to(reference_axis))
            if skin_review:
                await process_frame
                await RenderingServer.frame_post_draw
                var body = bodies[0]
                var baked = body.bake_mesh_from_current_skeleton_pose()
                if baked == null:
                    fail("Could not bake evaluated skin")
                    return
                var actual_points = []
                for surface in range(baked.get_surface_count()):
                    for vertex in baked.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
                        actual_points.append(body.global_transform * vertex)
                var reference_points = []
                for row in sample.positions[str(int(level.index))]:
                    reference_points.append(Vector3(row[0], row[1], row[2]))
                if actual_points.is_empty() or reference_points.is_empty():
                    fail("Missing skin points")
                    return
                for pair in [[actual_points, reference_points], [reference_points, actual_points]]:
                    for point in pair[0]:
                        var nearest = INF
                        for other in pair[1]:
                            nearest = min(nearest, point.distance_to(other))
                        maximum_skin = max(maximum_skin, nearest)
        results.append({"file": level.file, "samples": expected.samples.size(), "maximum_head_error": maximum, "maximum_axis_error": maximum_axis, "maximum_skin_error": maximum_skin if skin_review else null})
        asset.free()
        if maximum > expected.tolerance or maximum_axis > expected.tolerance or maximum_skin > expected.tolerance:
            fail("Bone playback mismatch: " + str(results))
            return
    var output = FileAccess.open(report_path, FileAccess.WRITE)
    output.store_string(JSON.stringify({"levels": results, "skin_review": skin_review, "scope": "Sampled heads/axes and optional baked vertex clouds; not visual acceptance"}, "  "))
    output.close()
    print("Skinned LOD Godot bone playback passed: ", results)
    quit(0)
