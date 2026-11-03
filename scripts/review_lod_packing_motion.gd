# SPDX-License-Identifier: GPL-3.0-or-later
# Rendering-enabled diagnostic; does not replace acceptance checks.
extends SceneTree
const Correspondence = preload("review_skin_lod_godot.gd")

func _initialize():
    call_deferred("review")

func review():
    if DisplayServer.get_name() == "headless":
        push_error("Rendering-enabled display required")
        quit(1)
        return
    if FileAccess.file_exists("res://packing-motion-diagnostic.json"):
        DirAccess.remove_absolute("res://packing-motion-diagnostic.json")
    var expected = JSON.parse_string(FileAccess.get_file_as_string("res://expected.json"))
    var manifest = JSON.parse_string(FileAccess.get_file_as_string("res://lod-manifest.json"))
    if not expected is Dictionary or not manifest is Dictionary or manifest.get("levels", []).is_empty():
        push_error("Missing fixture data")
        quit(1)
        return
    var tolerance = float(expected.get("tolerance", 0))
    if not is_finite(tolerance) or tolerance <= 0:
        push_error("Motion correspondence requires a finite positive tolerance")
        quit(1)
        return
    var precision_explained = true
    var strict_passed = true
    var results = []
    for level in manifest.levels:
        var document = GLTFDocument.new()
        var state = GLTFState.new()
        if document.append_from_file("res://" + level.file, state) != OK:
            quit(1)
            return
        var asset = document.generate_scene(state, 800, false, false)
        root.add_child(asset)
        var body = asset.find_children("*", "MeshInstance3D", true, false)[0]
        var player = asset.find_children("*", "AnimationPlayer", true, false)[0]
        var skeleton = asset.find_children("*", "Skeleton3D", true, false)[0]
        player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
        player.play(expected.get("clip", "ProbeMotion"))
        player.advance(0)
        var max_observed = 0.0
        var max_unexplained = 0.0
        var max_packing = 0.0
        var max_bound = 0.0
        var max_bake_residual = 0.0
        var max_raw_reference = 0.0
        var mapping = []
        var cells = {}
        for sample in expected.samples:
            player.seek(sample.seconds, true)
            skeleton.force_update_all_bone_transforms()
            await process_frame
            await RenderingServer.frame_post_draw
            var rid = body.get_skin_reference().get_skeleton()
            var baked = body.bake_mesh_from_current_skeleton_pose()
            var ordinal = 0
            var reference_points = []
            for row in sample.positions[str(int(level.index))]:
                reference_points.append(Vector3(row[0], row[1], row[2]))
            if mapping.is_empty():
                cells = Correspondence.correspondence_grid(reference_points, expected.tolerance)
            for surface in range(body.mesh.get_surface_count()):
                var raw = state.get_meshes()[0].mesh.get_surface_arrays(surface)
                var packed = body.mesh.surface_get_arrays(surface)
                var vertices = packed[Mesh.ARRAY_VERTEX]
                if raw[Mesh.ARRAY_VERTEX] != vertices or raw[Mesh.ARRAY_BONES] != packed[Mesh.ARRAY_BONES]:
                    push_error("Cannot compare reordered vertices/bones")
                    quit(1)
                    return
                var actual = baked.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
                var stride = packed[Mesh.ARRAY_WEIGHTS].size() / vertices.size()
                for vertex in range(vertices.size()):
                    var base = vertices[vertex]
                    var full = base
                    var quantized = base
                    var bound = 0.0
                    for slot in range(stride):
                        var index = vertex * stride + slot
                        var bone = packed[Mesh.ARRAY_BONES][index]
                        var transform = RenderingServer.skeleton_bone_get_transform(rid, bone)
                        var delta = transform * base - base
                        var a = raw[Mesh.ARRAY_WEIGHTS][index]
                        var b = packed[Mesh.ARRAY_WEIGHTS][index]
                        full += a * delta
                        quantized += b * delta
                        bound += abs(a - b) * (body.global_transform.basis * delta).length()
                    max_bound = max(max_bound, bound)
                    max_packing = max(max_packing, (body.global_transform.basis * (full - quantized)).length())
                    max_bake_residual = max(max_bake_residual, (body.global_transform.basis * (actual[vertex] - quantized)).length())
                    var world = body.global_transform * full
                    if ordinal >= mapping.size():
                        var match = Correspondence.nearest_correspondence(world, reference_points, cells, expected.tolerance)
                        var nearest = match.distance
                        var match_index = match.index
                        if nearest > expected.tolerance:
                            push_error("Initial original-weight correspondence exceeds tolerance (%s vertex %d: %.12g)" % [level.file, ordinal, nearest])
                            quit(1)
                            return
                        mapping.append(match_index)
                    var target = reference_points[mapping[ordinal]]
                    var observed = body.global_transform * actual[vertex] - target
                    var predicted = body.global_transform.basis * (quantized - full)
                    if not observed.is_finite() or not predicted.is_finite():
                        push_error("Nonfinite motion diagnostic")
                        quit(1)
                        return
                    max_observed = max(max_observed, observed.length())
                    max_unexplained = max(max_unexplained, (observed - predicted).length())
                    max_raw_reference = max(max_raw_reference, world.distance_to(target))
                    ordinal += 1
        var strict_level = max_observed <= expected.tolerance
        var explained_level = max_unexplained <= expected.tolerance and max_bake_residual <= expected.tolerance and max_packing <= max_bound + 1e-6
        strict_passed = strict_passed and strict_level
        precision_explained = precision_explained and explained_level
        results.append({"file": level.file, "strict_passed": strict_level, "precision_explained": explained_level,
            "observed_error": max_observed, "unexplained_error": max_unexplained, "packing_error": max_packing, "packing_bound": max_bound,
            "bake_model_residual": max_bake_residual, "raw_weight_reference_error": max_raw_reference})
        asset.free()
    var output = FileAccess.open("res://packing-motion-diagnostic.json", FileAccess.WRITE)
    output.store_string(JSON.stringify({"schema_version": 2, "diagnostic_only": true, "strict_passed": strict_passed, "precision_explained": precision_explained, "tolerance": expected.tolerance, "levels": results}, "  "))
    output.close()
    print(results)
    quit(0 if precision_explained else 1)
