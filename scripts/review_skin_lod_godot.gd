# SPDX-License-Identifier: GPL-3.0-or-later
# Godot --headless --path BUNDLE --script /absolute/path/to/this/script
extends SceneTree

func _initialize():
    call_deferred("review")

func fail(message):
    push_error(message)
    quit(1)

func review():
    var report_path = "res://godot-skin-lod-report.json"
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
        var skeleton = skeletons[0]
        var bone = skeleton.find_bone(expected.bone)
        if bone < 0 or not player.has_animation("ProbeMotion"):
            fail("Missing bone or clip")
            return
        player.play("ProbeMotion")
        player.advance(0)
        var maximum = 0.0
        for sample in expected.samples:
            player.seek(sample.seconds, true)
            skeleton.force_update_all_bone_transforms()
            var pose = skeleton.global_transform * skeleton.get_bone_global_pose(bone)
            var actual = pose.origin
            var reference = Vector3(sample.head[0], sample.head[1], sample.head[2])
            maximum = max(maximum, actual.distance_to(reference))
        results.append({"file": level.file, "samples": expected.samples.size(), "maximum_head_error": maximum})
        asset.free()
        if maximum > expected.tolerance:
            fail("Bone playback mismatch: " + str(results))
            return
    var output = FileAccess.open(report_path, FileAccess.WRITE)
    output.store_string(JSON.stringify({"levels": results, "scope": "Bone heads only; not evaluated skin or visual acceptance"}, "  "))
    output.close()
    print("Skinned LOD Godot bone playback passed: ", results)
    quit(0)
