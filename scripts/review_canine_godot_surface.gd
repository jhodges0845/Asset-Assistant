# SPDX-License-Identifier: GPL-3.0-or-later
# Run with a rendering-capable driver. Measures Godot's baked skinned mesh.
extends SceneTree

func _initialize():
    call_deferred("review")

func fail(message):
    push_error(message)
    quit(1)

func godot_point(point):
    return Vector3(point[0], point[2], -point[1]) / 100.0

func review():
    if FileAccess.file_exists("res://godot-surface-report.json"):
        DirAccess.remove_absolute("res://godot-surface-report.json")
    var oracle = JSON.parse_string(FileAccess.get_file_as_string("res://surface-expected.json"))
    var expected = JSON.parse_string(FileAccess.get_file_as_string("res://expected.json"))
    if oracle == null or expected == null:
        fail("Generate a fixture with --surface first")
        return
    var asset = load("res://canine_import.gd").load_asset(expected, true)
    if asset == null:
        fail("Surface import failed")
        return
    root.add_child(asset)
    var bodies = asset.find_children("*", "MeshInstance3D", true, false)
    var players = asset.find_children("*", "AnimationPlayer", true, false)
    if bodies.size() != 1 or players.size() != 1:
        fail("Surface probe requires one skinned mesh and animation player")
        return
    var body = bodies[0]
    var player = players[0]
    player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
    # Match fixed material points once in the neutral mesh. Never rematch
    # against moving positions, which could conceal sliding or identity loss.
    var pivots = {}
    var mapping_error = 0.0
    for name in oracle.neutral_pivots_cm:
        var target = godot_point(oracle.neutral_pivots_cm[name])
        var closest = INF
        var address = []
        for surface in range(body.mesh.get_surface_count()):
            var vertices = body.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
            for index in range(vertices.size()):
                var distance = (body.global_transform * vertices[index]).distance_to(target)
                if distance < closest:
                    closest = distance
                    address = [surface, index]
        if address.is_empty() or closest * 100 > oracle.tolerance_cm:
            fail("Cannot identify neutral toe: " + name + " error cm " + str(closest * 100))
            return
        pivots[name] = address
        mapping_error = max(mapping_error, closest * 100)
    var cycles = []
    var passed = true
    for cycle in oracle.cycles:
        var label = "Walk" if cycle.clip == "walk" else "Run"
        player.get_animation(label).loop_mode = Animation.LOOP_LINEAR
        player.play(label)
        player.advance(0)
        var frames = []
        var maximum_error = 0.0
        var minimum_height = INF
        var first_points = []
        var loop_error = 0.0
        for sample in cycle.frames:
            player.seek(float(sample.seconds), true)
            player.advance(0)
            await process_frame
            await RenderingServer.frame_post_draw
            var baked = body.bake_mesh_from_current_skeleton_pose()
            if baked == null or baked.get_surface_count() != body.mesh.get_surface_count():
                fail("Godot skin snapshot missing or changed surfaces")
                return
            var points = []
            var arrays = []
            var lowest = INF
            for surface in range(baked.get_surface_count()):
                var vertices = baked.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
                if vertices.size() != body.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX].size():
                    fail("Godot skin snapshot changed topology")
                    return
                arrays.append(vertices)
                for vertex in vertices:
                    var point = body.global_transform * vertex
                    if not point.is_finite():
                        fail("Non-finite skin position")
                        return
                    points.append(point)
                    lowest = min(lowest, point.y * 100)
            if first_points.is_empty():
                first_points = points
            if sample.phase == 1.0:
                for index in range(points.size()):
                    loop_error = max(loop_error, points[index].distance_to(first_points[index]) * 100)
            var positions = {}
            for name in pivots:
                var address = pivots[name]
                var actual = body.global_transform * arrays[address[0]][address[1]]
                maximum_error = max(maximum_error,
                    actual.distance_to(godot_point(sample.fixed_toe_positions_cm[name])) * 100)
                positions[name] = actual
            minimum_height = min(minimum_height, lowest)
            frames.append({"phase": sample.phase, "positions": positions})
        var contacts = {}
        for name in pivots:
            var schedule = cycle.contact_reference[name]
            var stance = []
            var low = INF
            var high = -INF
            for frame in frames.slice(0, frames.size() - 1):
                var local = fposmod(float(frame.phase) - float(schedule.touchdown_phase), 1.0)
                if local <= schedule.duty_factor:
                    var point = frame.positions[name]
                    var corrected = Vector2(point.x * 100, -point.z * 100 +
                        float(schedule.reference_speed_cm_s) * float(cycle.duration_seconds) * local)
                    stance.append([local, corrected])
                    low = min(low, point.y * 100)
                    high = max(high, point.y * 100)
            stance.sort_custom(func(a, b): return a[0] < b[0])
            if stance.size() < 2:
                fail("Insufficient stance samples for " + name)
                return
            var drift = 0.0
            for point in stance:
                drift = max(drift, point[1].distance_to(stance[0][1]))
            var limit = .002 if ".front." in name else .001
            passed = passed and drift < limit and low >= 0 and high <= .1
            contacts[name] = {"fixed_toe_drift_cm": drift, "minimum_stance_height_cm": low,
                "maximum_stance_height_cm": high, "stance_samples": stance.size(), "drift_limit_cm": limit}
        passed = passed and maximum_error < oracle.tolerance_cm and minimum_height >= -.001 and loop_error < .001
        cycles.append({"clip": label, "frames": frames.size(), "minimum_surface_height_cm": minimum_height,
            "maximum_toe_source_error_cm": maximum_error, "loop_error_cm": loop_error, "contacts": contacts})
    var report = {"schema_version": 1, "passed": passed, "sample": oracle.sample,
        "godot_version": Engine.get_version_info(), "renderer": RenderingServer.get_current_rendering_method(),
        "neutral_mapping_error_cm": mapping_error, "cycles": cycles,
        "scope": "Godot baked skin snapshots; four fixed toe vertices and whole-surface clearance at 127 intervals. Not continuous contact or visual acceptance."}
    var file = FileAccess.open("res://godot-surface-report.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(report, "  ") + "\n")
    file.close()
    print("CANINE_GODOT_SURFACE_OK " if passed else "CANINE_GODOT_SURFACE_FAILED ", oracle.sample)
    quit(0 if passed else 1)
