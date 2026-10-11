# SPDX-License-Identifier: GPL-3.0-or-later
# Package only prepared resources and probes, excluding GLB/importer dependencies.
extends SceneTree

func _initialize():
    var destination = "res://canine-review.pck"
    if FileAccess.file_exists(destination):
        push_error("Refusing to overwrite an existing review pack")
        quit(1)
        return
    var files = ["project.godot", "canine-source-grid.scn", "expected.json",
        "surface-expected.json", "review.gd", "surface.gd"]
    for path in files:
        if not FileAccess.file_exists("res://" + path):
            push_error("Missing pack input: " + path)
            quit(1)
            return
    var packer = PCKPacker.new()
    var result = packer.pck_start(destination)
    for path in files:
        if result == OK:
            result = packer.add_file("res://" + path, "res://" + path)
    if result == OK:
        result = packer.flush()
    if result != OK:
        DirAccess.remove_absolute(destination)
        push_error("Review packaging failed: " + str(result))
        quit(1)
        return
    print("CANINE_REVIEW_PACK_OK")
    quit(0)
