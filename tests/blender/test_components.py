# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.components import (
    attach_rigid_component,
    component_records,
    inspect_component,
    remove_component,
    replace_rigid_component,
)
from object_core.components import AttachmentMode, ComponentKind, ComponentRecord
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderComponentPersistenceTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        for collection in tuple(bpy.data.collections):
            if collection.users == 0:
                bpy.data.collections.remove(collection)

    def _generated_human(self, *, rigged=False):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        if rigged:
            skeleton = provider.skeleton(values)
            skin_weights = provider.skin_weights(mesh, values)
            root = create_character(
                mesh,
                name="Human",
                scene=bpy.context.scene,
                skeleton=skeleton,
                skin_weights=skin_weights,
            )
        else:
            root = create_character(mesh, name="Human", scene=bpy.context.scene)
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root

    def _proof_mesh(self):
        provider = get_provider("box")
        values = {field.key: field.default for field in provider.parameters}
        return provider.mesh(values)

    def _record(self, *, component_id="proof-accessory-001", target="asset_root", provider_key="box-proof"):
        return ComponentRecord(
            component_id=component_id,
            kind=ComponentKind.ACCESSORY,
            provider_key=provider_key,
            attachment_target=target,
            attachment_mode=AttachmentMode.RIGID,
            owns_geometry=True,
            owns_materials=False,
            owns_rig=False,
        )

    def test_rigid_accessory_is_persisted_and_inspectable(self):
        root = self._generated_human()
        record = self._record()

        component_root = attach_rigid_component(root, self._proof_mesh(), record, name="Proof Accessory")

        self.assertEqual(root, component_root.parent)
        self.assertEqual(record, inspect_component(root, record.component_id))
        self.assertEqual((record,), component_records(root))
        self.assertTrue(any(child.type == "MESH" for child in component_root.children))

    def test_rigid_accessory_can_attach_to_generated_bone(self):
        root = self._generated_human(rigged=True)
        record = self._record(target="bone:hand.right")

        component_root = attach_rigid_component(root, self._proof_mesh(), record, name="Held Accessory")

        self.assertEqual("ARMATURE", component_root.parent.type)
        self.assertEqual("BONE", component_root.parent_type)
        self.assertEqual("hand.right", component_root.parent_bone)
        self.assertEqual(record, inspect_component(root, record.component_id))

    def test_missing_attachment_bone_is_rejected_without_registry_change(self):
        root = self._generated_human(rigged=True)
        record = self._record(target="bone:not-a-bone")

        with self.assertRaisesRegex(ValueError, "attachment bone does not exist"):
            attach_rigid_component(root, self._proof_mesh(), record, name="Bad Accessory")

        self.assertEqual((), component_records(root))

    def test_bone_attachment_tampering_is_detected(self):
        root = self._generated_human(rigged=True)
        record = self._record(target="bone:hand.right")
        component_root = attach_rigid_component(root, self._proof_mesh(), record, name="Held Accessory")
        component_root.parent_bone = "hand.left"

        with self.assertRaisesRegex(ValueError, "bone attachment no longer matches"):
            inspect_component(root, record.component_id)

    def test_duplicate_component_id_is_rejected_without_extra_children(self):
        root = self._generated_human()
        record = self._record()
        attach_rigid_component(root, self._proof_mesh(), record, name="Proof Accessory")
        child_count = len(root.children)

        with self.assertRaisesRegex(ValueError, "already attached"):
            attach_rigid_component(root, self._proof_mesh(), record, name="Duplicate")

        self.assertEqual(child_count, len(root.children))
        self.assertEqual((record,), component_records(root))

    def test_tampered_component_metadata_is_detected(self):
        root = self._generated_human()
        record = self._record()
        component_root = attach_rigid_component(root, self._proof_mesh(), record, name="Proof Accessory")
        component_root["asset_assistant_component_record"] = "{}"

        with self.assertRaisesRegex(ValueError, "metadata is invalid"):
            inspect_component(root, record.component_id)

    def test_remove_component_deletes_owned_tree_and_registry_entry(self):
        root = self._generated_human()
        record = self._record()
        component_root = attach_rigid_component(root, self._proof_mesh(), record, name="Proof Accessory")
        object_name = component_root.name

        removed = remove_component(root, record.component_id)

        self.assertEqual(record, removed)
        self.assertEqual((), component_records(root))
        self.assertIsNone(bpy.data.objects.get(object_name))
        with self.assertRaisesRegex(ValueError, "not registered"):
            inspect_component(root, record.component_id)

    def test_remove_bone_component_preserves_generated_armature(self):
        root = self._generated_human(rigged=True)
        armature = next(child for child in root.children if child.type == "ARMATURE")
        armature_name = armature.name
        record = self._record(target="bone:hand.right")
        attach_rigid_component(root, self._proof_mesh(), record, name="Held Accessory")

        remove_component(root, record.component_id)

        self.assertIsNotNone(bpy.data.objects.get(armature_name))
        self.assertEqual((), component_records(root))

    def test_replace_component_keeps_identity_and_can_change_attachment(self):
        root = self._generated_human(rigged=True)
        original = self._record(target="asset_root", provider_key="box-proof-v1")
        attach_rigid_component(root, self._proof_mesh(), original, name="Original Accessory")
        replacement = self._record(target="bone:hand.right", provider_key="box-proof-v2")

        previous, replacement_root = replace_rigid_component(
            root,
            self._proof_mesh(),
            replacement,
            name="Replacement Accessory",
        )

        self.assertEqual(original, previous)
        self.assertEqual(replacement, inspect_component(root, original.component_id))
        self.assertEqual((replacement,), component_records(root))
        self.assertEqual("BONE", replacement_root.parent_type)
        self.assertEqual("hand.right", replacement_root.parent_bone)

    def test_failed_replace_restores_previous_component(self):
        root = self._generated_human(rigged=True)
        original = self._record(target="asset_root", provider_key="box-proof-v1")
        original_root = attach_rigid_component(root, self._proof_mesh(), original, name="Original Accessory")
        bad_replacement = self._record(target="bone:not-a-bone", provider_key="box-proof-v2")

        with self.assertRaisesRegex(ValueError, "attachment bone does not exist"):
            replace_rigid_component(root, self._proof_mesh(), bad_replacement, name="Bad Replacement")

        self.assertEqual(original, inspect_component(root, original.component_id))
        self.assertEqual((original,), component_records(root))
        self.assertIsNotNone(bpy.data.objects.get(original_root.name))


if __name__ == "__main__":
    unittest.main()
