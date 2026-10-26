# SPDX-License-Identifier: GPL-3.0-or-later
# godot --headless --path BUNDLE --script /absolute/review_static_lod_godot.gd
# Tests direct GLTFDocument ingestion; does not configure runtime LOD switching.
extends SceneTree

func _initialize():
    call_deferred("review")

func fail(message):
    push_error(message)
    quit(1)

func review():
    var report_path = "res://godot-lod-report.json"
    if FileAccess.file_exists(report_path):
        DirAccess.remove_absolute(report_path)
    var manifest = JSON.parse_string(FileAccess.get_file_as_string("res://lod-manifest.json"))
    if not manifest is Dictionary or not manifest.has("levels"):
        fail("Missing bundle manifest")
        return
    if not manifest.levels is Array or manifest.levels.is_empty():
        fail("Bundle has no levels")
        return
    var results = []
    for level in manifest.levels:
        var document = GLTFDocument.new()
        var state = GLTFState.new()
        var error = document.append_from_file("res://" + level.file, state)
        if error != OK:
            fail("GLB load failed: " + level.file)
            return
        var scene = document.generate_scene(state)
        if scene == null:
            fail("GLB scene generation failed")
            return
        var pending = [scene]
        var meshes = 0
        var triangles = 0
        while not pending.is_empty():
            var node = pending.pop_back()
            pending.append_array(node.get_children())
            if node is MeshInstance3D:
                meshes += 1
                for surface in range(node.mesh.get_surface_count()):
                    if node.mesh.surface_get_primitive_type(surface) != Mesh.PRIMITIVE_TRIANGLES:
                        scene.free()
                        fail("Non-triangle surface")
                        return
                    var arrays = node.mesh.surface_get_arrays(surface)
                    var count = arrays[Mesh.ARRAY_INDEX].size()
                    if count == 0:
                        count = arrays[Mesh.ARRAY_VERTEX].size()
                    triangles += count / 3
        scene.free()
        if meshes != int(level.mesh_count) or triangles != int(level.triangles):
            fail("Imported counts differ from manifest: " + level.file)
            return
        results.append({"file": level.file, "meshes": meshes, "triangles": triangles})
    var output = FileAccess.open(report_path, FileAccess.WRITE)
    output.store_string(JSON.stringify({"levels": results, "engine_lod_configured": false}, "  "))
    output.close()
    print("Static LOD Godot import passed: ", results.size(), " levels")
    quit(0)
