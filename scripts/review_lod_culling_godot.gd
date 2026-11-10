# SPDX-License-Identifier: GPL-3.0-or-later
# Rendering-enabled Godot --path ENGINE_COPY --script /absolute/this_script.gd
extends "review_lod_selection_godot.gd"

func review():
    var output_path = "res://godot-lod-culling.json"
    if FileAccess.file_exists(output_path):
        fail("Choose a new culling report path")
        return
    var resource = load("res://lod-engine.tscn")
    if not resource is PackedScene:
        fail("Missing engine scene")
        return
    var scene = resource.instantiate()
    root.add_child(scene)
    var metadata = scene.get_meta("lod_selection_review", {})
    if metadata.get("version") != 1 or metadata.get("clip", "") == "" or metadata.player_paths.size() != 2:
        fail("Expected an animated two-level engine scene")
        return
    var results = []
    var maximum = 0.0
    for level in range(2):
        var player = scene.get_node(metadata.player_paths[level])
        var skeleton = scene.get_node(metadata.skeleton_paths[level])
        player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
        var level_maximum = 0.0
        for sample in range(49):
            player.seek(player.get_animation(metadata.clip).length * sample / 48.0, true)
            skeleton.force_update_all_bone_transforms()
            await process_frame
            await RenderingServer.frame_post_draw
            for path in metadata.group_paths[level]:
                var mesh = scene.get_node(path)
                var baked = mesh.bake_mesh_from_current_skeleton_pose()
                if baked == null:
                    fail("Evaluated skin unavailable")
                    return
                var box = mesh.custom_aabb
                for surface in range(baked.get_surface_count()):
                    for point in baked.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
                        if not point.is_finite():
                            fail("Nonfinite evaluated vertex")
                            return
                        for axis in range(3):
                            level_maximum = maxf(level_maximum, maxf(box.position[axis] - point[axis], point[axis] - box.end[axis]))
        maximum = maxf(maximum, level_maximum)
        results.append({"level": level, "samples": 49, "maximum_local_axis_overflow": level_maximum})
    var output = FileAccess.open(output_path, FileAccess.WRITE)
    output.store_string(JSON.stringify({"clip": metadata.clip, "levels": results,
        "maximum_local_axis_overflow": maximum,
        "scope": "Sampled evaluated-vertex containment only; not a continuous conservative bound"}, "  "))
    output.close()
    print("Culling review maximum local axis overflow: ", maximum)
    quit(0)
