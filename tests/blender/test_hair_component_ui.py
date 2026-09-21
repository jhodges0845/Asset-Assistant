# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.hair_component_ui import _default_attachment, _supports_parent_skinned
from blender_adapter.skinned_components import attach_skinned_component, inspect_skinned_component
from object_core.component_primitives import hair_shell_mesh
from object_core.components import AttachmentMode, ComponentBehavior, ComponentKind, ComponentRecord, RigBinding
from object_core.objects import get_provider
from object_core.providers.human_hair import fit_parent_skinned_hair


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class HairComponentUiTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def _human(self, rigged):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        kwargs = {}
        if rigged:
            kwargs["skeleton"] = provider.skeleton(values)
            kwargs["skin_weights"] = provider.skin_weights(mesh, values)
        root = create_character(mesh, name="Human", scene=bpy.context.scene, **kwargs)
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root, provider, values

    def test_rigged_human_defaults_hair_to_head_bone_and_supports_bone_driven(self):
        root, _provider, _values = self._human(True)
        self.assertEqual("bone:head", _default_attachment(root))
        self.assertTrue(_supports_parent_skinned(root))

    def test_unrigged_asset_defaults_hair_to_asset_root(self):
        root, _provider, _values = self._human(False)
        self.assertEqual("asset_root", _default_attachment(root))
        self.assertFalse(_supports_parent_skinned(root))

    def test_parent_skinned_hair_uses_existing_human_rig_without_owning_it(self):
        root, provider, values = self._human(True)
        mesh, weights = fit_parent_skinned_hair(
            hair_shell_mesh(back_length_cm=24.0),
            provider.skeleton(values),
        )
        record = ComponentRecord(
            component_id="hair-bone-driven-proof",
            kind=ComponentKind.HAIR,
            provider_key="primitive.hair_shell",
            attachment_target="body",
            attachment_mode=AttachmentMode.SKINNED,
            rig_binding=RigBinding.PARENT,
            behavior=ComponentBehavior.PARENT_SKINNED,
            owns_geometry=True,
            owns_materials=False,
            owns_rig=False,
        )

        component_root = attach_skinned_component(root, mesh, weights, record, name="Bone Driven Hair")

        self.assertEqual(record, inspect_skinned_component(root, record.component_id))
        self.assertEqual(root, component_root.parent)
        hair_mesh = next(child for child in component_root.children if child.type == "MESH")
        modifier = next(item for item in hair_mesh.modifiers if item.type == "ARMATURE")
        parent_rig = next(child for child in root.children if child.type == "ARMATURE")
        self.assertEqual(parent_rig, modifier.object)
        self.assertIn("head", hair_mesh.vertex_groups)
        self.assertIn("neck", hair_mesh.vertex_groups)
        self.assertIn("torso", hair_mesh.vertex_groups)


if __name__ == "__main__":
    unittest.main()
