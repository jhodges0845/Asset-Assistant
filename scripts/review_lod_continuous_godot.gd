# SPDX-License-Identifier: GPL-3.0-or-later
# Rendering-enabled Godot --fixed-fps 60 --path ENGINE_COPY --script /absolute/this_script.gd
# Observe autoplay without seeking or advancing either player's clock manually.
extends "review_lod_selection_godot.gd"

func review():
    var output_path = "res://godot-lod-continuous.json"
    if FileAccess.file_exists(output_path):
        fail("Choose a copy without an existing continuous-playback report")
        return
    var resource = load("res://lod-engine.tscn")
    if not resource is PackedScene:
        fail("Missing engine scene")
        return
    var viewport = SubViewport.new()
    viewport.size = Vector2i(128, 128)
    viewport.own_world_3d = true
    viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    root.add_child(viewport)
    var setup = resource.instantiate()
    viewport.add_child(setup)
    var metadata = setup.get_meta("lod_selection_review", {})
    if metadata.get("version") != 1 or metadata.get("diagnostic_materials", true) or metadata.get("clip", "") == "":
        fail("Expected an animated material-preserving engine scene")
        return
    var players = []
    for path in metadata.player_paths:
        var player = setup.get_node_or_null(path)
        if not player is AnimationPlayer or not player.is_playing() or player.current_animation != metadata.clip:
            fail("Configured clip is not playing")
            return
        players.append(player)
    if players.size() != 2:
        fail("Expected two autoplay players")
        return
    var duration = players[0].get_animation(metadata.clip).length
    if duration <= 0 or not is_equal_approx(duration, players[1].get_animation(metadata.clip).length):
        fail("Clip durations differ")
        return
    for index in range(2):
        for path in metadata.group_paths[index]:
            var mesh = setup.get_node_or_null(path)
            if not mesh is MeshInstance3D or mesh.material_override != null:
                fail("Missing mesh or unexpected material override")
                return
            var material = StandardMaterial3D.new()
            material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
            material.albedo_color = Color.RED if index == 0 else Color.GREEN
            material.cull_mode = BaseMaterial3D.CULL_DISABLED
            mesh.material_override = material
    var camera = Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.size = metadata.scale * 1.2
    camera.far = metadata.scale * 20.0
    viewport.add_child(camera)
    camera.current = true
    var previous = -1.0
    var wraps = 0
    var changed = 0
    var selected = [0, 0]
    var maximum_clock_error = 0.0
    var frames = ceili(duration * 60.0 * 3.5)
    for frame in range(frames):
        # Cross repeatedly, avoiding the exact boundary tie and its pixel ambiguity.
        var multiplier = 0.8 if (frame / 12) % 2 == 0 else 1.2
        camera.position = metadata.center + Vector3(0, 0, metadata.boundary * multiplier)
        camera.look_at(metadata.center)
        await process_frame
        await RenderingServer.frame_post_draw
        if not players[0].is_playing() or not players[1].is_playing():
            fail("Autoplay stopped during selection")
            return
        var time0 = players[0].current_animation_position
        var time1 = players[1].current_animation_position
        var error = absf(time0 - time1)
        maximum_clock_error = maxf(maximum_clock_error, error)
        if error > 0.000001:
            fail("LOD animation clocks diverged")
            return
        if previous >= 0:
            changed += int(not is_equal_approx(time0, previous))
            wraps += int(time0 < previous)
        previous = time0
        var image = viewport.get_texture().get_image()
        if image == null or image.is_empty():
            fail("Rendering unavailable")
            return
        var counts = [0, 0]
        for y in range(image.get_height()):
            for x in range(image.get_width()):
                var color = image.get_pixel(x, y)
                counts[0] += int(color.r > 0.5 and color.g < 0.2 and color.b < 0.2)
                counts[1] += int(color.g > 0.5 and color.r < 0.2 and color.b < 0.2)
        var expected = 0 if multiplier < 1 else 1
        if counts[expected] < 20 or counts[1 - expected] != 0:
            fail("Wrong rendered level during continuous playback")
            return
        selected[expected] += 1
    if wraps < 2 or changed < frames / 2 or selected.min() == 0:
        fail("Insufficient continuous loop/selection coverage; run with --fixed-fps 60")
        return
    var output = FileAccess.open(output_path, FileAccess.WRITE)
    output.store_string(JSON.stringify({"frames": frames, "loop_wraps": wraps,
        "selected_frames": selected, "maximum_clock_error_seconds": maximum_clock_error,
        "clip": metadata.clip, "scope": "Continuous autoplay clocks and rendered level selection; not visual transition quality"}, "  "))
    output.close()
    print("PASS: continuous autoplay and rendered selection: ", frames, " frames")
    quit(0)
