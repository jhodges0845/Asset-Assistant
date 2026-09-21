# SPDX-License-Identifier: GPL-3.0-or-later
"""Test the Asset Assistant release ZIP in a fresh headless Blender process."""

from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile

import bpy

root = Path(__file__).resolve().parents[1]
sys.path[:] = [entry for entry in sys.path
               if Path(entry or ".").resolve() not in (root, root / "scripts")]
assert "object_core" not in sys.modules
assert "humanoid_blender" not in sys.modules

with tempfile.TemporaryDirectory() as directory:
    with ZipFile(root / "dist" / "asset_assistant.zip") as archive:
        assert b"GNU GENERAL PUBLIC LICENSE" in archive.read("humanoid_blender/LICENSE")
        assert b"GPL-3.0-or-later" in archive.read("humanoid_blender/NOTICE")
        archive.extractall(directory)
    sys.path.insert(0, directory)
    import humanoid_blender
    from humanoid_blender import core
    Path(core._core.__file__).resolve().relative_to(Path(directory).resolve())
    assert core._core.__name__ == "humanoid_blender.object_core"
    assert humanoid_blender.bl_info["name"] == "Asset Assistant"
    humanoid_blender.register()
    try:
        scene = bpy.data.scenes.new("Asset Assistant Package Test")
        bpy.context.window.scene = scene
        scene.unit_settings.system = "METRIC"
        scene.humanoid_settings.body_type = "average"

        assert bpy.ops.humanoid.generate_blockout() == {"FINISHED"}
        assert bpy.context.view_layer.objects.active.type == "EMPTY"

        scene.humanoid_settings.workflow_tab = "RIGGING"
        assert bpy.ops.humanoid.add_basic_rig() == {"FINISHED"}
        rig = bpy.context.view_layer.objects.active
        assert rig.type == "ARMATURE"
        assert len(rig.data.bones) == 16

        character = rig.parent
        meshes = [obj for obj in character.children if obj.type == "MESH"]
        assert character["object_type"] == "human"
        assert len(meshes) == 1
        assert meshes[0]["body_part"] == "human"
        assert len(meshes[0].data.vertices) > 0
        bpy.context.view_layer.update()
        heights = [(obj.matrix_world @ vertex.co).z
                   for obj in meshes for vertex in obj.data.vertices]
        assert abs(max(heights) - min(heights) - 1.8) < 1e-5
        assert all(not obj.data.validate() for obj in meshes)

        scene.humanoid_settings.workflow_tab = "ANIMATION"
        assert bpy.ops.humanoid.generate_idle() == {"FINISHED"}
        assert rig.animation_data.action is not None
        assert bpy.ops.humanoid.preview_idle() == {"FINISHED"}
        assert scene.frame_current > scene.frame_start

        scene.humanoid_settings.asset_use = "ANIMATED"
        scene.humanoid_settings.workflow_tab = "VALIDATION"
        assert bpy.ops.humanoid.prepare_materials() == {"FINISHED"}
        assert bpy.ops.humanoid.validate_character() == {"FINISHED"}
        assert not any(row.status == "ERROR" for row in scene.humanoid_settings.validation_results)

        scene.humanoid_settings.object_type = "box"
        assert bpy.ops.humanoid.generate_blockout() == {"FINISHED"}
        box = scene.humanoid_settings.target
        assert box["object_type"] == "box"
        assert bpy.ops.humanoid.prepare_materials() == {"FINISHED"}
        assert bpy.ops.humanoid.validate_character() == {"FINISHED"}
        assert not any(row.status == "ERROR" for row in scene.humanoid_settings.validation_results)

        for target_key, extension in (("GODOT", ".glb"), ("UNITY", ".fbx"),
                                      ("UNREAL", ".fbx"), ("CURA", ".stl")):
            scene.humanoid_settings.output_target = target_key
            # Changing the export target intentionally invalidates the cached
            # validation snapshot. Refresh it explicitly before exercising the
            # packaged add-on's lightweight export poll.
            assert bpy.ops.humanoid.validate_character() == {"FINISHED"}
            assert not any(row.status == "ERROR" for row in scene.humanoid_settings.validation_results)
            assert bpy.ops.humanoid.export_asset.poll(), target_key
            export_path = Path(directory) / (target_key + extension)
            assert bpy.ops.humanoid.export_asset(filepath=str(export_path)) == {"FINISHED"}
            assert export_path.stat().st_size > 0

        print("PACKAGED_ADDON_OK: Asset Assistant isolated ZIP loaded, generated, rigged, animated, validated, and exported successfully")
    finally:
        humanoid_blender.unregister()
