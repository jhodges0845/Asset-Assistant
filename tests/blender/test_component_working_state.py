# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.components import attach_rigid_component
from blender_adapter.working_asset_ui import save_editable_checkpoint, validate_working_state
from object_core.component_primitives import ring_mesh
from object_core.components import AttachmentMode, ComponentBehavior, ComponentKind, ComponentRecord
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class ComponentWorkingStateTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def _base(self):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        root = create_character(provider.mesh(values), name="Human", scene=bpy.context.scene)
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root

    def _ring(self, root):
        record = ComponentRecord(
            component_id="generated-ring-proof",
            kind=ComponentKind.ACCESSORY,
            provider_key="primitive.ring",
            attachment_target="asset_root",
            attachment_mode=AttachmentMode.RIGID,
            behavior=ComponentBehavior.RIGID,
            owns_geometry=True,
            owns_materials=False,
            owns_rig=False,
        )
        return attach_rigid_component(root, ring_mesh(), record, name="Ring Accessory")

    def test_generated_ring_is_valid_editable_working_state(self):
        root = self._base()
        component_root = self._ring(root)

        snapshots = validate_working_state(bpy.context.scene)

        self.assertEqual(1, len(snapshots))
        self.assertEqual(root.get("asset_assistant_asset_id"), snapshots[0].asset_id)
        self.assertEqual(root, component_root.parent)

    def test_tampered_component_blocks_checkpoint_before_file_write(self):
        root = self._base()
        component_root = self._ring(root)
        component_root["asset_assistant_component_record"] = "{}"
        calls = []

        with self.assertRaises(ValueError):
            save_editable_checkpoint(
                "/tmp/tampered-component.blend",
                lambda **kwargs: calls.append(kwargs) or {"FINISHED"},
                bpy.context.scene,
            )

        self.assertEqual([], calls)


if __name__ == "__main__":
    unittest.main()
