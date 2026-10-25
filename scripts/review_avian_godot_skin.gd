# SPDX-License-Identifier: GPL-3.0-or-later
# Renderer-backed fixed-neutral-correspondence surface comparison.
extends SceneTree

func _initialize():
    call_deferred("review")

func fail(message):
    push_error(message)
    quit(1)

func point(row):
    return Vector3(row[0], row[1], row[2])

func review():
    var packed_scene = false
    var diagnostic_import = false
    var bake_fps = 800.0
    var explicit_bake_fps = false
    for argument in OS.get_cmdline_user_args():
        if argument == "--packed-scene":
            packed_scene = true
        elif argument.begins_with("--bake-fps="):
            bake_fps = float(argument.get_slice("=", 1))
            explicit_bake_fps = true
        elif argument == "--diagnostic-import":
            diagnostic_import = true
        else:
            fail("Unknown skin probe option: " + argument)
            return
    if not is_finite(bake_fps) or bake_fps <= 0 or bake_fps > 3200:
        fail("Bake FPS must be in (0, 3200]")
        return
    if explicit_bake_fps and not diagnostic_import:
        fail("--bake-fps requires --diagnostic-import")
        return
    if packed_scene and diagnostic_import:
        fail("Diagnostic import cannot change a packed scene")
        return
    var report_path = "res://godot-skin-packed-report.json" if packed_scene else "res://godot-skin-report.json"
    if FileAccess.file_exists(report_path):
        DirAccess.remove_absolute(report_path)
    var expected = JSON.parse_string(FileAccess.get_file_as_string("res://expected.json"))
    if expected == null or not expected.has("neutral_positions_m"):
        fail("Generate a character fixture with --posed-surface")
        return
    var asset
    if packed_scene:
        var saved = load("res://canine-source-grid.scn")
        if not saved is PackedScene:
            fail("Missing prepared scene")
            return
        asset = saved.instantiate()
    else:
        asset = load("res://canine_import.gd").load_asset(expected, not diagnostic_import, bake_fps)
    if asset == null:
        fail("Import failed")
        return
    root.add_child(asset)
    var bodies = asset.find_children("*", "MeshInstance3D", true, false)
    var players = asset.find_children("*", "AnimationPlayer", true, false)
    if bodies.size() != 1 or players.size() != 1:
        fail("Expected one body and player")
        return
    var body = bodies[0]
    var player = players[0]
    player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
    # Index the same tolerance-bounded nearest-vertex search for dense bodies.
    var cell_size = expected.tolerance_cm / 100.0
    if not is_finite(cell_size) or cell_size <= 0:
        fail("Invalid surface tolerance")
        return
    var cells = {}
    for index in range(expected.neutral_positions_m.size()):
        var position = point(expected.neutral_positions_m[index])
        var cell = Vector3i((position / cell_size).floor())
        if not cells.has(cell):
            cells[cell] = []
        cells[cell].append(index)
    var mappings = []
    var represented = {}
    var mapping_error = 0.0
    for surface in range(body.mesh.get_surface_count()):
        var indices = []
        for vertex in body.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
            var position = body.global_transform * vertex
            var closest = INF
            var selected = -1
            var cell = Vector3i((position / cell_size).floor())
            for x in range(-1, 2):
                for y in range(-1, 2):
                    for z in range(-1, 2):
                        for index in cells.get(cell + Vector3i(x, y, z), []):
                            var distance = position.distance_to(point(expected.neutral_positions_m[index])) * 100.0
                            if distance < closest or (distance == closest and index < selected):
                                closest = distance
                                selected = index
            if selected < 0 or not is_finite(closest) or closest > expected.tolerance_cm:
                fail("Cannot map imported rest vertex")
                return
            indices.append(selected)
            represented[selected] = true
            mapping_error = max(mapping_error, closest)
        mappings.append(indices)
    if represented.size() != expected.neutral_positions_m.size():
        fail("Neutral correspondence does not cover every source vertex")
        return
    var results = []
    var passed = true
    for label in expected.playback_sequence:
        if not player.has_animation(label):
            fail("Missing clip " + label)
            return
        var clip = expected.clips[label]
        player.get_animation(label).loop_mode = Animation.LOOP_LINEAR
        player.play(label)
        player.advance(0)
        var maximum = 0.0
        var worst = {}
        for cycle in range(3):
            for sample in clip.samples:
                if not sample.has("positions_m") or sample.positions_m.size() != expected.neutral_positions_m.size():
                    fail("Missing full-surface sample")
                    return
                player.seek(float(sample.seconds), true)
                player.advance(float(clip.duration) * cycle)
                await process_frame
                await RenderingServer.frame_post_draw
                var baked = body.bake_mesh_from_current_skeleton_pose()
                if baked == null or baked.get_surface_count() != mappings.size():
                    fail("Missing or changed baked surfaces")
                    return
                for surface in range(mappings.size()):
                    var vertices = baked.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
                    if vertices.size() != mappings[surface].size():
                        fail("Changed baked vertex count")
                        return
                    for index in range(vertices.size()):
                        var actual = body.global_transform * vertices[index]
                        var source = mappings[surface][index]
                        var reference = point(sample.positions_m[source])
                        if not actual.is_finite() or not reference.is_finite():
                            fail("Nonfinite surface point")
                            return
                        var error_cm = actual.distance_to(reference) * 100.0
                        if error_cm > maximum:
                            maximum = error_cm
                            worst = {"source_vertex": source, "seconds": sample.seconds, "cycle": cycle}
        var clip_passed = maximum <= expected.tolerance_cm
        passed = passed and clip_passed
        results.append({"clip": label, "passed": clip_passed, "maximum_error_cm": maximum,
            "worst": worst, "cycles": 3, "samples_per_cycle": clip.samples.size()})
    var report = {"passed": passed, "packed_scene": packed_scene, "diagnostic_import": diagnostic_import, "bake_fps": bake_fps if diagnostic_import else null, "godot_version": Engine.get_version_info(),
        "sample": expected.sample, "semantic_operations": expected.get("semantic_operations", []),
        "source_commit": expected.commit, "tolerance_cm": expected.tolerance_cm,
        "neutral_mapping_error_cm": mapping_error, "source_vertices_covered": represented.size(),
        "clips": results, "scope": "Fixed neutral vertex correspondence, sampled baked skin; excludes between-sample behavior, normals, UVs and artistic acceptance."}
    var output = FileAccess.open(report_path, FileAccess.WRITE)
    output.store_string(JSON.stringify(report, "  ") + "\n")
    output.close()
    print("AVIAN_SKIN_OK" if passed else "AVIAN_SKIN_FAILED")
    quit(0 if passed else 1)
