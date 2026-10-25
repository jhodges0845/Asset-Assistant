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
        asset = load("res://canine_import.gd").load_asset(expected, source_aligned, bake_fps, remove_immutable)
    if asset == null:
        fail("Canine import failed")
        return
    root.add_child(asset)
    var geometry = {}
    if expected.has("neutral_positions_m"):
        geometry = compare_neutral_mesh(asset, expected.neutral_positions_m, expected.tolerance_cm)
    var players = asset.find_children("*", "AnimationPlayer", true, false)
    var skeletons = asset.find_children("*", "Skeleton3D", true, false)
    if players.size() != 1 or skeletons.size() != 1:
        fail("Expected one animation player and skeleton")
        return
    var player = players[0]
    var skeleton = skeletons[0]
    var results = []
    var passed = geometry.get("passed", true)
    for label in expected.get("playback_sequence", ["Walk", "Idle", "Run", "Idle"]):
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
        "neutral_geometry": geometry, "semantic_operations": expected.get("semantic_operations", []),
        "scope": "Optional rest vertex-cloud parity and headless skeletal playback; loop mode explicitly enabled; not rendered skin or visual acceptance."}
    var output = FileAccess.open("res://godot-report.json", FileAccess.WRITE)
    output.store_string(JSON.stringify(report, "  ") + "\n")
    output.close()
    print("CANINE_GODOT_PLAYBACK_OK " if passed else "CANINE_GODOT_PLAYBACK_FAILED ", expected.sample)
    quit(0 if passed else 1)


func compare_neutral_mesh(asset, reference_rows, tolerance_cm):
    var actual = []
    for instance in asset.find_children("*", "MeshInstance3D", true, false):
        if instance.mesh == null:
            continue
        for surface in range(instance.mesh.get_surface_count()):
            var arrays = instance.mesh.surface_get_arrays(surface)
            for point in arrays[Mesh.ARRAY_VERTEX]:
                actual.append(instance.global_transform * point)
    var reference = []
    for point in reference_rows:
        reference.append(Vector3(point[0], point[1], point[2]))
    if actual.is_empty() or reference.is_empty():
        return {"passed": false, "reason": "Missing rest vertices"}
    # Export may duplicate vertices at UV/normal seams. Compare both directions
    # without treating those duplicates as changed topology or vertex identity.
    var maximum = 0.0
    var cell_size = tolerance_cm / 100.0
    if not is_finite(cell_size) or cell_size <= 0:
        return {"passed": false, "reason": "Invalid tolerance"}
    for pair in [[actual, reference], [reference, actual]]:
        var cells = {}
        for other in pair[1]:
            if not other.is_finite():
                return {"passed": false, "reason": "Nonfinite rest vertex"}
            var cell = Vector3i((other / cell_size).floor())
            if not cells.has(cell):
                cells[cell] = []
            cells[cell].append(other)
        for point in pair[0]:
            if not point.is_finite():
                return {"passed": false, "reason": "Nonfinite rest vertex"}
            var nearest = INF
            var cell = Vector3i((point / cell_size).floor())
            for x in range(-1, 2):
                for y in range(-1, 2):
                    for z in range(-1, 2):
                        for other in cells.get(cell + Vector3i(x, y, z), []):
                            nearest = min(nearest, point.distance_to(other))
            # Keep exact failure distances when no tolerance-near match exists.
            if nearest > cell_size:
                for other in pair[1]:
                    nearest = min(nearest, point.distance_to(other))
            maximum = max(maximum, nearest * 100.0)
    return {"passed": maximum <= tolerance_cm, "maximum_nearest_vertex_error_cm": maximum,
        "imported_vertex_count": actual.size(), "source_vertex_count": reference.size(),
        "scope": "Bidirectional rest vertex-cloud distance; excludes topology, normals, UVs and posed skin."}
