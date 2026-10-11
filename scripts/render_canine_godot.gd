# SPDX-License-Identifier: GPL-3.0-or-later
# Run with a rendering-capable display driver, not --headless.
extends SceneTree

func _initialize():
    call_deferred("render_review")

func render_review():
    var expected = JSON.parse_string(FileAccess.get_file_as_string("res://expected.json"))
    var importer = load("res://canine_import.gd")
    var asset = importer.load_asset(expected, true)
    if asset == null:
        push_error("Could not import canine review")
        quit(1)
        return
    var label = "Walk"
    for argument in OS.get_cmdline_user_args():
        if argument.begins_with("--clip="):
            label = argument.get_slice("=", 1)
        else:
            push_error("Unknown render option " + argument)
            quit(1)
            return
    if label not in ["Walk", "Run"]:
        push_error("Render clip must be Walk or Run")
        quit(1)
        return
    var world = Node3D.new()
    root.add_child(world)
    world.add_child(asset)
    var bounds = AABB()
    var first = true
    for body in asset.find_children("*", "MeshInstance3D", true, false):
        var box = body.global_transform * body.get_aabb()
        bounds = box if first else bounds.merge(box)
        first = false
    var stride = max(bounds.size.x, bounds.size.z) * 1.2
    var height = bounds.size.y
    var players = []
    for index in range(4):
        var animal = asset if index == 0 else asset.duplicate()
        if index != 0:
            world.add_child(animal)
        animal.position.x = (index - 1.5) * stride
        animal.rotation.y = [PI, 3 * PI / 4, PI / 2, 0.0][index]
        var player = animal.find_children("*", "AnimationPlayer", true, false)[0]
        player.get_animation(label).loop_mode = Animation.LOOP_LINEAR
        player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
        player.play(label)
        player.advance(0)
        players.append(player)
    var environment = WorldEnvironment.new()
    environment.environment = Environment.new()
    environment.environment.background_mode = Environment.BG_COLOR
    environment.environment.background_color = Color(0.12, 0.14, 0.17)
    environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.environment.ambient_light_color = Color(0.8, 0.85, 1.0)
    environment.environment.ambient_light_energy = 0.6
    world.add_child(environment)
    var light = DirectionalLight3D.new()
    light.rotation = Vector3(-0.8, -0.5, 0.0)
    light.light_energy = 1.4
    light.shadow_enabled = true
    world.add_child(light)
    var floor_mesh = MeshInstance3D.new()
    var plane = PlaneMesh.new()
    plane.size = Vector2(stride * 5, stride * 3)
    floor_mesh.mesh = plane
    var material = StandardMaterial3D.new()
    material.albedo_color = Color(0.22, 0.24, 0.27)
    floor_mesh.material_override = material
    world.add_child(floor_mesh)
    var camera = Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.size = max(stride * 4.3 / (1600.0 / 600.0), height * 1.5)
    camera.position = Vector3(0, height * 0.6 + 0.65, stride * 4)
    world.add_child(camera)
    camera.look_at(Vector3(0, height * 0.5, 0))
    camera.current = true
    root.size = Vector2i(1600, 600)
    root.content_scale_size = Vector2i(1600, 600)
    var captions = ["Front", "Three-quarter", "Side", "Back"]
    for index in range(4):
        var caption = Label.new()
        caption.text = captions[index]
        caption.position = Vector2(index * 400 + 130, 530)
        caption.add_theme_font_size_override("font_size", 20)
        root.add_child(caption)
    var directory = "res://render-" + label.to_lower()
    DirAccess.make_dir_recursive_absolute(directory)
    var frames = int(round(float(expected.clips[label].duration) * 25 * 3))
    for frame in range(frames):
        for player in players:
            player.seek(float(frame) / 25.0, true)
            player.advance(0)
        await process_frame
        await RenderingServer.frame_post_draw
        var result = root.get_texture().get_image().save_png(directory + "/frame-%03d.png" % frame)
        if result != OK:
            push_error("Frame capture failed: " + str(result))
            quit(1)
            return
    var report = {"sample": expected.sample, "clip": label, "frames": frames,
        "fps": 25, "cycles": 3, "views": ["front", "three-quarter", "side", "back"],
        "import": "source-aligned, constant tracks retained", "godot_version": Engine.get_version_info(), "renderer": RenderingServer.get_current_rendering_method()}
    var file = FileAccess.open(directory + "/render-report.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(report, "  ") + "\n")
    file.close()
    print("CANINE_GODOT_RENDER_OK ", directory)
    quit(0)
