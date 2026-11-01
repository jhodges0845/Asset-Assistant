# SPDX-License-Identifier: GPL-3.0-or-later
# Godot --headless --path BUNDLE --script /absolute/path/to/this/script
extends SceneTree

func _initialize():
    call_deferred("review")

func fail(message):
    push_error(message)
    quit(1)

func review():
    var packed_diagnostic = "--balanced-pack-diagnostic" in OS.get_cmdline_user_args()
    var normalize_diagnostic = "--normalize-baked-diagnostic" in OS.get_cmdline_user_args()
    var skin_review = "--skin" in OS.get_cmdline_user_args()
    if packed_diagnostic and (not skin_review or normalize_diagnostic):
        fail("Balanced packing requires --skin and excludes normalized-bake mode")
        return
    if normalize_diagnostic and not skin_review:
        fail("Normalized-bake diagnostic requires --skin")
        return
    if normalize_diagnostic:
        print("DIAGNOSTIC ONLY: normalized baked positions do not establish export acceptance")
    if skin_review and DisplayServer.get_name() == "headless":
        fail("Skin review requires a rendering-enabled display; omit --headless")
        return
    var report_path = "res://godot-skin-lod-report.json"
    if skin_review:
        report_path = "res://godot-skin-lod-surface-report.json"
    if normalize_diagnostic:
        report_path = "res://godot-skin-normalized-diagnostic.json"
    if packed_diagnostic:
        report_path = "res://godot-balanced-pack-diagnostic.json"
        print("DIAGNOSTIC ONLY: balanced destination packing; source GLBs remain unchanged")
    if FileAccess.file_exists(report_path):
        DirAccess.remove_absolute(report_path)
    var expected = JSON.parse_string(FileAccess.get_file_as_string("res://expected.json"))
    var manifest = JSON.parse_string(FileAccess.get_file_as_string("res://lod-manifest.json"))
    if not expected is Dictionary or not manifest is Dictionary:
        fail("Missing fixture oracle or manifest")
        return
    var passed = true
    var results = []
    for level in manifest.levels:
        var document = GLTFDocument.new()
        var state = GLTFState.new()
        if document.append_from_file("res://" + level.file, state) != OK:
            fail("Could not import " + level.file)
            return
        var asset = document.generate_scene(state, 800, false, false)
        root.add_child(asset)
        var players = asset.find_children("*", "AnimationPlayer", true, false)
        var skeletons = asset.find_children("*", "Skeleton3D", true, false)
        if players.size() != 1 or skeletons.size() != 1:
            fail("Expected one player and skeleton")
            return
        var player = players[0]
        player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
        var skeleton = skeletons[0]
        var bone = skeleton.find_bone(expected.bone)
        if bone < 0 or not player.has_animation("ProbeMotion"):
            fail("Missing bone or clip")
            return
        player.play("ProbeMotion")
        player.advance(0)
        var failure_reason = ""
        var evaluated_samples = 0
        var maximum = 0.0
        var maximum_axis = 0.0
        var maximum_skin = 0.0
        var weight_sums = []
        var rest_vertices = []
        var correspondence = []
        var reference_count = 0
        var bodies = asset.find_children("*", "MeshInstance3D", true, false)
        if skin_review and bodies.size() != 1:
            fail("Expected one skinned mesh")
            return
        if packed_diagnostic:
            var replacement = ArrayMesh.new()
            var raw_mesh = state.get_meshes()[0].mesh
            for surface in range(raw_mesh.get_surface_count()):
                var arrays = raw_mesh.get_surface_arrays(surface)
                var weights = arrays[Mesh.ARRAY_WEIGHTS].duplicate()
                var vertices = arrays[Mesh.ARRAY_VERTEX].size()
                var stride = weights.size() / vertices
                for vertex in range(vertices):
                    var total = 0.0
                    for slot in range(stride):
                        total += weights[vertex * stride + slot]
                    if not is_finite(total) or total <= 0:
                        fail("Invalid diagnostic weight sum")
                        return
                    var integers = []
                    var remainders = []
                    var allocated = 0
                    for slot in range(stride):
                        var scaled = weights[vertex * stride + slot] / total * 65535.0
                        var quantized = int(floor(scaled))
                        integers.append(quantized)
                        remainders.append(scaled - quantized)
                        allocated += quantized
                    for unused in range(65535 - allocated):
                        var winner = remainders.find(remainders.max())
                        integers[winner] += 1
                        remainders[winner] = -1.0
                    for slot in range(stride):
                        var q = integers[slot]
                        weights[vertex * stride + slot] = min(1.0, (q + .125) / 65535.0) if q else 0.0
                arrays[Mesh.ARRAY_WEIGHTS] = weights
                replacement.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
            bodies[0].mesh = replacement
        if skin_review:
            var minimum_weight_sum = INF
            var maximum_weight_sum = -INF
            for surface in range(bodies[0].mesh.get_surface_count()):
                var arrays = bodies[0].mesh.surface_get_arrays(surface)
                rest_vertices.append_array(arrays[Mesh.ARRAY_VERTEX])
                var weights = arrays[Mesh.ARRAY_WEIGHTS]
                var vertex_count = arrays[Mesh.ARRAY_VERTEX].size()
                var stride = weights.size() / vertex_count
                for vertex in range(vertex_count):
                    var total = 0.0
                    for slot in range(stride):
                        total += weights[vertex * stride + slot]
                    weight_sums.append(total)
                    minimum_weight_sum = min(minimum_weight_sum, total)
                    maximum_weight_sum = max(maximum_weight_sum, total)
            print(level.file, " imported weight sums: ", minimum_weight_sum, " .. ", maximum_weight_sum)
        for sample in expected.samples:
            player.seek(sample.seconds, true)
            skeleton.force_update_all_bone_transforms()
            var pose = skeleton.global_transform * skeleton.get_bone_global_pose(bone)
            var actual = pose.origin
            var reference = Vector3(sample.head[0], sample.head[1], sample.head[2])
            maximum = max(maximum, actual.distance_to(reference))
            for axis in range(3):
                var row = sample.axes[axis]
                var reference_axis = Vector3(row[0], row[1], row[2])
                maximum_axis = max(maximum_axis, pose.basis[axis].distance_to(reference_axis))
            if skin_review:
                await process_frame
                await RenderingServer.frame_post_draw
                var body = bodies[0]
                var baked = body.bake_mesh_from_current_skeleton_pose()
                if baked == null:
                    fail("Could not bake evaluated skin")
                    return
                var actual_points = []
                var vertex_index = 0
                for surface in range(baked.get_surface_count()):
                    for vertex in baked.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
                        if normalize_diagnostic:
                            # Diagnostic only: not an import fix or acceptance mode.
                            var rest = rest_vertices[vertex_index]
                            vertex = rest + (vertex - rest) / weight_sums[vertex_index]
                        actual_points.append(body.global_transform * vertex)
                        vertex_index += 1
                var reference_points = []
                for row in sample.positions[str(int(level.index))]:
                    reference_points.append(Vector3(row[0], row[1], row[2]))
                if actual_points.is_empty() or reference_points.is_empty():
                    fail("Missing skin points")
                    return
                if correspondence.is_empty():
                    reference_count = reference_points.size()
                    var covered = {}
                    for point in actual_points:
                        var nearest = INF
                        var match_index = -1
                        for index in range(reference_points.size()):
                            var distance = point.distance_to(reference_points[index])
                            if distance < nearest:
                                nearest = distance
                                match_index = index
                        if nearest > expected.tolerance:
                            maximum_skin = nearest
                            failure_reason = "Initial skin correspondence exceeds tolerance"
                            break
                        correspondence.append(match_index)
                        covered[match_index] = true
                    if not failure_reason.is_empty():
                        break
                    if covered.size() != reference_count:
                        fail("Initial correspondence does not cover every source vertex")
                        return
                if actual_points.size() != correspondence.size() or reference_points.size() != reference_count:
                    fail("Skin vertex counts changed during playback")
                    return
                for index in range(actual_points.size()):
                    var distance = actual_points[index].distance_to(reference_points[correspondence[index]])
                    maximum_skin = max(maximum_skin, distance)
            evaluated_samples += 1
        var level_passed = failure_reason.is_empty() and maximum <= expected.tolerance and maximum_axis <= expected.tolerance and maximum_skin <= expected.tolerance
        if not level_passed and failure_reason.is_empty():
            failure_reason = "Playback error exceeds tolerance"
        passed = passed and level_passed
        results.append({"file": level.file, "passed": level_passed, "failure_reason": failure_reason, "evaluated_samples": evaluated_samples, "samples": expected.samples.size(), "maximum_head_error": maximum, "maximum_axis_error": maximum_axis, "maximum_skin_error": maximum_skin if skin_review else null, "source_vertices_covered": reference_count if skin_review else null})
        asset.free()
    var output = FileAccess.open(report_path, FileAccess.WRITE)
    output.store_string(JSON.stringify({"passed": passed, "levels": results, "skin_review": skin_review, "normalized_bake_diagnostic": normalize_diagnostic, "balanced_pack_diagnostic": packed_diagnostic, "scope": "Sampled heads/axes and optional fixed-correspondence baked skin; not visual acceptance"}, "  "))
    output.close()
    print("LOD playback result: ", "PASS" if passed else "FAIL", " ", results)
    quit(0 if passed else 1)
