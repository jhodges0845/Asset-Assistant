# SPDX-License-Identifier: GPL-3.0-or-later
# Run: godot --headless --path OUTPUT_DIRECTORY --script review.gd
extends SceneTree

func _initialize():
    call_deferred("review")

func fail(message):
    push_error(message)
    quit(1)

func review():
    # Diagnostic defaults preserve resets and dense source motion. This high
    # sampling rate is for parity measurement, not a shipping-memory preset.
    var bake_fps = 800.0
    var remove_immutable = false
    var source_aligned = false
    var packed_scene = false
    var arguments = OS.get_cmdline_user_args()
    for argument in arguments:
        if argument.begins_with("--bake-fps="):
            bake_fps = float(argument.get_slice("=", 1))
        elif argument == "--packed-scene":
            packed_scene = true
            source_aligned = true
        elif argument == "--source-aligned":
            source_aligned = true
        elif argument == "--remove-immutable":
            remove_immutable = true
        else:
            fail("Unknown probe option: " + argument)
            return
    if not is_finite(bake_fps) or bake_fps <= 0 or bake_fps > 3200:
        fail("Bake FPS must be in (0, 3200]")
        return
    if FileAccess.file_exists("res://godot-report.json"):
        DirAccess.remove_absolute("res://godot-report.json")
    var expected = JSON.parse_string(FileAccess.get_file_as_string("res://expected.json"))
    if expected == null:
        fail("Missing pose oracle")
        return
    var importer = load("res://canine_import.gd")
    var asset
    if packed_scene:
        if remove_immutable:
            fail("Packed scene has retained reset tracks; remove-immutable is incompatible")
            return
        var saved = load("res://canine-source-grid.scn")
        if not saved is PackedScene:
            fail("Missing prepared canine scene")
            return
        asset = saved.instantiate()
    else:
        asset = importer.load_asset(expected, source_aligned, bake_fps, remove_immutable)
    if asset == null:
        fail("Canine import failed")
        return
    root.add_child(asset)
    var players = asset.find_children("*", "AnimationPlayer", true, false)
    var skeletons = asset.find_children("*", "Skeleton3D", true, false)
    if players.size() != 1 or skeletons.size() != 1:
        fail("Expected one animation player and skeleton")
        return
    var player = players[0]
    var skeleton = skeletons[0]
    var results = []
    var passed = true
    for label in ["Walk", "Idle", "Run", "Idle"]:
        if not player.has_animation(label):
            fail("Missing clip " + label + ": " + str(player.get_animation_list()))
            return
        var clip = expected.clips[label]
        var animation = player.get_animation(label)
        if abs(animation.length - clip.duration) > 0.00001:
            fail("Changed duration for " + label + ": " + str(animation.length) + " expected " + str(clip.duration))
            return
        var key_count = 0
        for track in range(animation.get_track_count()):
            key_count += animation.track_get_key_count(track)
        var imported_loop_mode = animation.loop_mode
        # Looping is an explicit destination setting, not a GLB guarantee.
        animation.loop_mode = Animation.LOOP_LINEAR
        player.play(label)
        player.advance(0)
        var maximum = 0.0
        var worst = {}
        for cycle in range(3):
            for sample in clip.samples:
                # Start at the source phase, then advance whole cycles through
                # AnimationPlayer to exercise destination loop evaluation.
                player.seek(float(sample.seconds), true)
                player.advance(float(clip.duration) * cycle)
                skeleton.force_update_all_bone_transforms()
                for bone_name in sample.bones:
                    var index = skeleton.find_bone(bone_name)
                    if index < 0:
                        fail("Missing bone " + bone_name)
                        return
                    var actual = skeleton.global_transform * skeleton.get_bone_global_pose(index).origin
                    var p = sample.bones[bone_name]
                    var reference = Vector3(p[0], p[1], p[2])
                    var distance = actual.distance_to(reference) * 100.0
                    if distance > maximum:
                        maximum = distance
                        worst = {"bone": bone_name, "seconds": sample.seconds, "cycle": cycle,
                            "actual": str(actual), "reference": str(reference)}
        results.append({"clip": label, "maximum_bone_head_error_cm": maximum,
            "effective_bake_fps": clip.import_bake_fps if source_aligned else bake_fps,
            "key_count": key_count, "worst": worst, "imported_loop_mode": imported_loop_mode, "cycles": 3, "samples_per_cycle": 34})
        if maximum > expected.tolerance_cm:
            passed = false
            push_error(label + " pose mismatch in cm: " + str(maximum) + " " + str(worst))
    var report = {"schema_version": 1, "godot_version": Engine.get_version_info(),
        "sample": expected.sample, "source_commit": expected.commit,
        "tolerance_cm": expected.tolerance_cm, "clips": results, "passed": passed,
        "packed_scene": packed_scene, "source_aligned": source_aligned, "bake_fps": bake_fps, "remove_immutable_tracks": remove_immutable,
        "scope": "Headless skeletal playback; loop mode explicitly enabled; not rendered skin or visual acceptance."}
    var output = FileAccess.open("res://godot-report.json", FileAccess.WRITE)
    output.store_string(JSON.stringify(report, "  ") + "\n")
    output.close()
    print("CANINE_GODOT_PLAYBACK_OK " if passed else "CANINE_GODOT_PLAYBACK_FAILED ", expected.sample)
    quit(0 if passed else 1)
