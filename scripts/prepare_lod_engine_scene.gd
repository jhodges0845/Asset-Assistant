# SPDX-License-Identifier: GPL-3.0-or-later
# Godot --headless --path BUNDLE --script /absolute/this_script.gd -- DISTANCE [CLIP] [--loop]
# Saves a new two-level lod-engine.tscn; preserves imported surface materials.
extends "review_lod_selection_godot.gd"

func review():
    var arguments = OS.get_cmdline_user_args()
    var loop_clip = not arguments.is_empty() and arguments[-1] == "--loop"
    if loop_clip:
        arguments.remove_at(arguments.size() - 1)
    if arguments.size() < 1 or arguments.size() > 2 or not arguments[0].is_valid_float():
        fail("Expected positive switch distance and optional exact clip name")
        return
    var distance = arguments[0].to_float()
    if not is_finite(distance) or distance <= 0:
        fail("Switch distance must be finite and positive")
        return
    var clip = arguments[1] if arguments.size() == 2 else ""
    if loop_clip and clip == "":
        fail("Loop export requires an explicit clip")
        return
    await build_scene(clip, "res://lod-engine.tscn", distance, false, loop_clip)
