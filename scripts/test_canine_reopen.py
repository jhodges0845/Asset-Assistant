# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify generated canine hocks, weights and animation survive save/reopen."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_adapter
from blender_adapter.modification import inspect_generated_asset
from object_core.objects import get_provider

blender_adapter.register()
try:
    settings = bpy.context.scene.humanoid_settings
    settings.object_type = "quadruped"
    assert bpy.ops.humanoid.generate_blockout() == {"FINISHED"}
    root = settings.target
    asset_id = root["asset_assistant_asset_id"]
    assert bpy.ops.humanoid.add_basic_rig() == {"FINISHED"}
    assert bpy.ops.humanoid.generate_idle() == {"FINISHED"}
    rig = next(obj for obj in root.children if obj.type == "ARMATURE")
    hock = rig.pose.bones["hind_pastern.left"]
    hock.rotation_mode = "XYZ"
    hock.rotation_euler.x = .3
    action_name = rig.animation_data.action.name
    with TemporaryDirectory() as directory:
        path = str(Path(directory) / "canine.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        root = bpy.context.scene.humanoid_settings.target
        assert root["asset_assistant_asset_id"] == asset_id
        assert root["object_type"] == "quadruped"
        rig = next(obj for obj in root.children if obj.type == "ARMATURE")
        body = next(obj for obj in root.children if obj.type == "MESH")
        assert len(rig.data.bones) == 17
        assert rig.animation_data.action.name == action_name
        assert abs(rig.pose.bones["hind_pastern.left"].rotation_euler.x - .3) < 1e-6
        assert any(mod.type == "ARMATURE" and mod.object == rig for mod in body.modifiers)
        provider = get_provider("quadruped")
        values = {field.key: root[field.key] for field in provider.parameters}
        mesh = provider.mesh(values)
        assert tuple(tuple(face.vertices) for face in body.data.polygons) == mesh.parts[0].faces
        assert len(body.data.vertices) == 312
        for side in ("left", "right"):
            group = body.vertex_groups["hind_pastern." + side]
            assert any(item.group == group.index and item.weight > 0
                       for vertex in body.data.vertices for item in vertex.groups)
        assert inspect_generated_asset(root).owns_geometry
        print("CANINE_PLUGIN_REOPEN_OK")
finally:
    blender_adapter.unregister()
