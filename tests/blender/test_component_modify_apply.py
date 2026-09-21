# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.component_modify_apply import _host_plan, _remove_one
from blender_adapter.component_modify_exchange import enrich_snapshot
from blender_adapter.components import attach_rigid_component, component_records
from blender_adapter.modification import inspect_generated_asset
from blender_adapter.skinned_components import attach_skinned_component
from object_core.components import AttachmentMode, ComponentKind, ComponentRecord, RigBinding
from object_core.modification import ComponentOperation, ModificationRequest, plan_modification
from object_core.models import BoneWeight, SkinWeights
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderComponentModifyApplyTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        for collection in tuple(bpy.data.collections):
            if collection.users == 0:
                bpy.data.collections.remove(collection)

    def _human(self):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        root = create_character(
            mesh,
            name="Human",
            scene=bpy.context.scene,
            skeleton=provider.skeleton(values),
            skin_weights=provider.skin_weights(mesh, values),
        )
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root, provider, values

    def _proof_mesh(self):
        provider = get_provider("box")
        values = {field.key: field.default for field in provider.parameters}
        return provider.mesh(values)

    def _snapshot(self, root):
        return enrich_snapshot(root, inspect_generated_asset(root))

    def test_single_rigid_remove_is_executable_and_preserves_asset(self):
        root, _provider, _values = self._human()
        record = ComponentRecord(
            component_id="remove-rigid-001",
            kind=ComponentKind.ACCESSORY,
            provider_key="proof.accessory",
            attachment_target="bone:hand.right",
            attachment_mode=AttachmentMode.RIGID,
            owns_geometry=True,
        )
        attach_rigid_component(root, self._proof_mesh(), record, name="Held Proof")
        snapshot = self._snapshot(root)
        request = ModificationRequest(component_operations=(
            ComponentOperation("remove", record.component_id),
        ))

        plan = _host_plan(plan_modification, snapshot, request)
        self.assertTrue(plan.safe_to_apply)
        _remove_one(root, plan.requested_component_operations[0], snapshot)

        self.assertEqual((), component_records(root))
        self.assertEqual(1, len([child for child in root.children if child.type == "ARMATURE"]))

    def test_single_skinned_remove_is_executable_and_preserves_parent_rig(self):
        root, _provider, _values = self._human()
        mesh = self._proof_mesh()
        weights = tuple(
            SkinWeights(
                part.name,
                tuple(((BoneWeight("torso", 1.0),)) for _vertex in part.vertices),
            )
            for part in mesh.parts
        )
        record = ComponentRecord(
            component_id="remove-skinned-001",
            kind=ComponentKind.CLOTHING,
            provider_key="proof.clothing",
            attachment_target="body",
            attachment_mode=AttachmentMode.SKINNED,
            rig_binding=RigBinding.PARENT,
            owns_geometry=True,
        )
        armature = next(child for child in root.children if child.type == "ARMATURE")
        armature_name = armature.name
        attach_skinned_component(root, mesh, weights, record, name="Proof Clothing")
        snapshot = self._snapshot(root)
        request = ModificationRequest(component_operations=(
            ComponentOperation("remove", record.component_id),
        ))

        plan = _host_plan(plan_modification, snapshot, request)
        self.assertTrue(plan.safe_to_apply)
        _remove_one(root, plan.requested_component_operations[0], snapshot)

        self.assertEqual((), component_records(root))
        self.assertIsNotNone(bpy.data.objects.get(armature_name))

    def test_add_and_replace_remain_blocked_until_provider_execution_exists(self):
        root, _provider, _values = self._human()
        snapshot = self._snapshot(root)
        add_record = ComponentRecord(
            component_id="future-add-001",
            kind=ComponentKind.ACCESSORY,
            provider_key="future.accessory",
            attachment_target="asset_root",
            attachment_mode=AttachmentMode.RIGID,
            owns_geometry=True,
        )
        request = ModificationRequest(component_operations=(
            ComponentOperation("add", add_record.component_id, add_record),
        ))

        plan = _host_plan(plan_modification, snapshot, request)
        self.assertFalse(plan.safe_to_apply)
        self.assertTrue(any("executable component provider" in blocker for blocker in plan.blockers))

    def test_base_regeneration_is_blocked_while_component_is_attached(self):
        root, provider, values = self._human()
        record = ComponentRecord(
            component_id="guard-component-001",
            kind=ComponentKind.ACCESSORY,
            provider_key="proof.accessory",
            attachment_target="asset_root",
            attachment_mode=AttachmentMode.RIGID,
            owns_geometry=True,
        )
        attach_rigid_component(root, self._proof_mesh(), record)
        snapshot = self._snapshot(root)
        field = next(field for field in provider.parameters if not field.choices)
        current = values[field.key]
        candidate = min(field.maximum, current + max((field.maximum - field.minimum) * 0.05, 0.01))
        if candidate == current:
            candidate = max(field.minimum, current - max((field.maximum - field.minimum) * 0.05, 0.01))
        request = ModificationRequest(parameter_changes=((field.key, candidate),))

        plan = _host_plan(plan_modification, snapshot, request)
        self.assertFalse(plan.safe_to_apply)
        self.assertTrue(any("attached components" in blocker for blocker in plan.blockers))

    def test_multiple_removals_are_blocked_as_one_transaction(self):
        root, _provider, _values = self._human()
        records = []
        for index in range(2):
            record = ComponentRecord(
                component_id="multi-remove-00" + str(index),
                kind=ComponentKind.ACCESSORY,
                provider_key="proof.accessory",
                attachment_target="asset_root",
                attachment_mode=AttachmentMode.RIGID,
                owns_geometry=True,
            )
            attach_rigid_component(root, self._proof_mesh(), record, name="Proof " + str(index))
            records.append(record)
        snapshot = self._snapshot(root)
        request = ModificationRequest(component_operations=tuple(
            ComponentOperation("remove", record.component_id) for record in records
        ))

        plan = _host_plan(plan_modification, snapshot, request)
        self.assertFalse(plan.safe_to_apply)
        self.assertTrue(any("one component removal" in blocker for blocker in plan.blockers))


if __name__ == "__main__":
    unittest.main()
