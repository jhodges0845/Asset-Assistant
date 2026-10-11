# SPDX-License-Identifier: GPL-3.0-or-later
# Review-only importer for generated canine clips on a verified uniform grid.
extends RefCounted

static func import_scene(fps, remove_immutable):
    var document = GLTFDocument.new()
    var state = GLTFState.new()
    if document.append_from_file("res://canine.glb", state) != OK:
        return null
    return document.generate_scene(state, fps, false, remove_immutable)

static func load_asset(expected, source_aligned = false, fps = 800.0, remove_immutable = false):
    var asset = import_scene(fps if not source_aligned else 30.0, remove_immutable)
    if asset == null or not source_aligned:
        return asset
    var players = asset.find_children("*", "AnimationPlayer", true, false)
    if players.size() != 1:
        asset.free()
        return null
    var library = players[0].get_animation_library("")
    for label in expected.clips:
        var rate = expected.clips[label].get("import_bake_fps", 0.0)
        if not is_finite(rate) or rate <= 0 or rate > 3200:
            push_error("Missing or invalid authored key grid for " + label)
            asset.free()
            return null
        var sampled = import_scene(rate, remove_immutable)
        if sampled == null:
            asset.free()
            return null
        var source_players = sampled.find_children("*", "AnimationPlayer", true, false)
        if source_players.size() != 1 or not source_players[0].has_animation(label):
            sampled.free()
            asset.free()
            return null
        var animation = source_players[0].get_animation(label)
        library.remove_animation(label)
        library.add_animation(label, animation)
        sampled.free()
    return asset
