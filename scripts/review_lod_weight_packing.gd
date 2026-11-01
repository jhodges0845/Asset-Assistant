# SPDX-License-Identifier: GPL-3.0-or-later
# Direct import diagnostic: compare ImporterMesh floats with packed ArrayMesh.
extends SceneTree

func _initialize():
    if FileAccess.file_exists("res://weight-packing-diagnostic.json"):
        DirAccess.remove_absolute("res://weight-packing-diagnostic.json")
    var manifest = JSON.parse_string(FileAccess.get_file_as_string("res://lod-manifest.json"))
    if not manifest is Dictionary or not manifest.get("levels") is Array or manifest.levels.is_empty():
        push_error("Missing fixture levels")
        quit(1)
        return
    var results = []
    for level in manifest.levels:
        var document = GLTFDocument.new()
        var state = GLTFState.new()
        if document.append_from_file("res://" + level.file, state) != OK:
            push_error("Import failed")
            quit(1)
            return
        var meshes = state.get_meshes()
        if meshes.size() != 1:
            push_error("Expected one fixture mesh")
            quit(1)
            return
        var source = meshes[0].mesh
        var packed = source.get_mesh()
        var largest = 0.0
        var minimum_sum = 1.0
        var source_sum_error = 0.0
        var truncation_error = 0.0
        var count = 0
        for surface in range(source.get_surface_count()):
            var original = source.get_surface_arrays(surface)
            var imported = packed.surface_get_arrays(surface)
            if original[Mesh.ARRAY_VERTEX] != imported[Mesh.ARRAY_VERTEX] or original[Mesh.ARRAY_BONES] != imported[Mesh.ARRAY_BONES]:
                push_error("Vertex or bone ordering changed; cannot compare by index")
                quit(1)
                return
            var raw = original[Mesh.ARRAY_WEIGHTS]
            var converted = imported[Mesh.ARRAY_WEIGHTS]
            var vertices = original[Mesh.ARRAY_VERTEX].size()
            var stride = raw.size() / vertices
            for vertex in range(vertices):
                var raw_sum = 0.0
                var converted_sum = 0.0
                for slot in range(stride):
                    var index = vertex * stride + slot
                    largest = max(largest, abs(raw[index] - converted[index]))
                    truncation_error = max(truncation_error, abs(floor(raw[index] * 65535.0) / 65535.0 - converted[index]))
                    raw_sum += raw[index]
                    converted_sum += converted[index]
                source_sum_error = max(source_sum_error, abs(raw_sum - 1.0))
                minimum_sum = min(minimum_sum, converted_sum)
            count += vertices
        results.append({"file": level.file, "vertices": count, "maximum_weight_change": largest,
            "maximum_raw_sum_error": source_sum_error, "minimum_packed_sum": minimum_sum,
            "maximum_u16_truncation_prediction_error": truncation_error})
    var output = FileAccess.open("res://weight-packing-diagnostic.json", FileAccess.WRITE)
    output.store_string(JSON.stringify({"godot": Engine.get_version_info(), "levels": results}, "  "))
    output.close()
    print(results)
    quit(0)
