# SPDX-License-Identifier: GPL-3.0-or-later
# Fresh rendering-enabled process; only project.godot and review TSCN are needed.
extends "review_lod_selection_godot.gd"

func review():
    if not OS.get_cmdline_user_args().is_empty():
        fail("Reopen uses the clip stored in the review scene; no arguments expected")
        return
    var viewport = SubViewport.new()
    viewport.size = Vector2i(128, 128)
    viewport.own_world_3d = true
    viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    root.add_child(viewport)
    var camera = Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.near = 0.01
    viewport.add_child(camera)
    camera.current = true
    await verify_saved_scene("res://lod-selection-review.tscn",
        "res://godot-lod-selection-reopened.json", viewport, camera)
