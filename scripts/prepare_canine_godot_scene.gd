# SPDX-License-Identifier: GPL-3.0-or-later
# Review integration candidate: prepare once, load the PackedScene afterward.
extends SceneTree

func _initialize():
    call_deferred("prepare")

func prepare():
    var destination = "res://canine-source-grid.scn"
    if FileAccess.file_exists(destination):
        push_error("Refusing to overwrite an existing prepared scene")
        quit(1)
        return
    var expected = JSON.parse_string(FileAccess.get_file_as_string("res://expected.json"))
    if expected == null:
        push_error("Missing verified source-grid metadata")
        quit(1)
        return
    var importer = load("res://canine_import.gd")
    var started = Time.get_ticks_usec()
    var asset = importer.load_asset(expected, true)
    if asset == null:
        push_error("Source-grid import failed")
        quit(1)
        return
    # Imported descendants already belong to the imported root. Packing must
    # preserve their ownership, skin resources and animation track paths.
    var packed = PackedScene.new()
    var result = packed.pack(asset)
    if result == OK:
        result = ResourceSaver.save(packed, destination)
    asset.free()
    if result != OK:
        push_error("Unable to save prepared scene: " + str(result))
        quit(1)
        return
    print("CANINE_SCENE_PREPARED seconds=", (Time.get_ticks_usec() - started) / 1000000.0)
    quit(0)
