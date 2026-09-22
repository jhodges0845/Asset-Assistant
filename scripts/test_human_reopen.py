# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify the Human plugin mesh, rig and action survive a real save/reopen."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_adapter
from object_core.objects import get_provider

blender_adapter.register()
try:
    settings = bpy.context.scene.humanoid_settings
    settings.object_type = "human"
    assert bpy.ops.humanoid.generate_blockout() == {"FINISHED"}
    root = settings.target
    asset_id = root["asset_assistant_asset_id"]
    assert bpy.ops.humanoid.add_basic_rig() == {"FINISHED"}
    assert bpy.ops.humanoid.generate_idle() == {"FINISHED"}
    with TemporaryDirectory() as directory:
        path = str(Path(directory) / "human.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        root = bpy.context.scene.humanoid_settings.target
        assert root["asset_assistant_asset_id"] == asset_id
        assert root["object_type"] == "human"
        rig = next(obj for obj in root.children if obj.type == "ARMATURE")
        body = next(obj for obj in root.children if obj.type == "MESH")
        assert rig.animation_data.action is not None
        assert any(
            mod.type == "ARMATURE" and mod.object == rig for mod in body.modifiers
        )
        provider = get_provider("human")
        values = {field.key: root[field.key] for field in provider.parameters}
        expected = provider.mesh(values).parts[0]
        assert (
            tuple(tuple(face.vertices) for face in body.data.polygons) == expected.faces
        )
        assert len(body.data.vertices) == len(expected.vertices)
        assert len(body.vertex_groups) > 0
        print("HUMAN_PLUGIN_REOPEN_OK")
finally:
    blender_adapter.unregister()
