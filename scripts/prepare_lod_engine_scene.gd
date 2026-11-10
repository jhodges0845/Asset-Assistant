# SPDX-License-Identifier: GPL-3.0-or-later
# Godot --headless --path BUNDLE --script /absolute/this_script.gd -- DISTANCE [CLIP] [--loop] [--bounds-margin=VALUE]
# Saves a new two-level lod-engine.tscn; preserves imported surface materials.
extends "review_lod_selection_godot.gd"

func review():
    var arguments = OS.get_cmdline_user_args()
    var bounds_margin = -1.0
    for index in range(arguments.size() - 1, -1, -1):
        if arguments[index].begins_with("--bounds-margin="):
            var value = arguments[index].trim_prefix("--bounds-margin=")
            if bounds_margin >= 0 or not value.is_valid_float() or not is_finite(value.to_float()) or value.to_float() < 0:
                fail("Supply one finite nonnegative bounds margin")
                return
            bounds_margin = value.to_float()
            arguments.remove_at(index)
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
    if clip != "" and bounds_margin < 0:
        fail("Animated engine export requires explicit --bounds-margin=VALUE; validate it against the clip")
        return
    await build_scene(clip, "res://lod-engine.tscn", distance, false, loop_clip, maxf(bounds_margin, 0.0))
