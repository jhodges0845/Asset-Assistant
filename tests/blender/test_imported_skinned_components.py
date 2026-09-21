# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest import mock

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.components import component_records
from blender_adapter.imported_components import adopt_skinned_component
from blender_adapter.skinned_components import inspect_skinned_component, remove_skinned_component
from object_core.components import AttachmentMode, ComponentKind, ComponentRecord, RigBinding
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class ImportedSkinnedComponentAdoptionTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def _generated_human(self):
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
        return root

    def _external_mesh(self, name="Imported Coat"):
        mesh = bpy.data.meshes.new(name + ".Mesh")
        mesh.from_pydata(
            ((-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (0.0, 0.5, 0.0)),
            (),
            ((0, 1, 2),),
        )
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = (2.0, 3.0, 4.0)
        return obj

    def _record(self, component_id="imported-coat-001"):
        return ComponentRecord(
            component_id=component_id,
            kind=ComponentKind.CLOTHING,
            provider_key="artist_authored",
            attachment_target="body",
            attachment_mode=AttachmentMode.SKINNED,
            owns_geometry=True,
            owns_materials=False,
            owns_rig=False,
            rig_binding=RigBinding.PARENT,
        )

    def _weight(self, root, mesh_object, *, add_modifier=True):
        armature = next(child for child in root.children if child.type == "ARMATURE")
        group = mesh_object.vertex_groups.new(name="torso")
        group.add(list(range(len(mesh_object.data.vertices))), 1.0, "REPLACE")
        modifier = None
        if add_modifier:
            modifier = mesh_object.modifiers.new(name="Imported Rig", type="ARMATURE")
            modifier.object = armature
            modifier.use_vertex_groups = True
            modifier.use_bone_envelopes = False
        return armature, modifier

    def test_existing_parent_rig_setup_is_preserved(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        mesh_data = mesh_object.data
        world = mesh_object.matrix_world.copy()
        armature, modifier = self._weight(root, mesh_object)
        record = self._record()

        component_root = adopt_skinned_component(root, mesh_object, record)

        self.assertEqual(root, component_root.parent)
        self.assertEqual(component_root, mesh_object.parent)
        self.assertEqual(mesh_data, mesh_object.data)
        self.assertEqual(world, mesh_object.matrix_world)
        self.assertEqual(armature, modifier.object)
        self.assertEqual(record, inspect_skinned_component(root, record.component_id))
        self.assertEqual((record,), component_records(root))

    def test_missing_modifier_is_added_after_weights_validate(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        armature, _ = self._weight(root, mesh_object, add_modifier=False)
        record = self._record()

        adopt_skinned_component(root, mesh_object, record)

        modifiers = [item for item in mesh_object.modifiers if item.type == "ARMATURE"]
        self.assertEqual(1, len(modifiers))
        self.assertEqual(armature, modifiers[0].object)
        self.assertTrue(modifiers[0].use_vertex_groups)
        self.assertFalse(modifiers[0].use_bone_envelopes)
        self.assertEqual(record, inspect_skinned_component(root, record.component_id))

    def test_existing_wrong_modifier_is_rejected_without_retargeting(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        self._weight(root, mesh_object, add_modifier=False)
        other_data = bpy.data.armatures.new("Other Rig Data")
        other_armature = bpy.data.objects.new("Other Rig", other_data)
        bpy.context.scene.collection.objects.link(other_armature)
        modifier = mesh_object.modifiers.new(name="Other Rig", type="ARMATURE")
        modifier.object = other_armature

        with self.assertRaisesRegex(ValueError, "must already target"):
            adopt_skinned_component(root, mesh_object, self._record())

        self.assertEqual(other_armature, modifier.object)
        self.assertIsNone(mesh_object.parent)
        self.assertEqual((), component_records(root))

    def test_unregistered_mesh_already_under_target_hierarchy_can_be_adopted(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        armature, _ = self._weight(root, mesh_object)
        world = mesh_object.matrix_world.copy()
        mesh_object.parent = armature
        mesh_object.matrix_world = world
        record = self._record()

        component_root = adopt_skinned_component(root, mesh_object, record)

        self.assertEqual(component_root, mesh_object.parent)
        self.assertEqual(world, mesh_object.matrix_world)
        self.assertEqual(record, inspect_skinned_component(root, record.component_id))

    def test_generated_body_mesh_is_rejected(self):
        root = self._generated_human()
        body_mesh = next(child for child in root.children if child.type == "MESH")

        with self.assertRaisesRegex(ValueError, "generated body geometry"):
            adopt_skinned_component(root, body_mesh, self._record())

        self.assertEqual((), component_records(root))

    def test_unknown_vertex_group_is_rejected(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        group = mesh_object.vertex_groups.new(name="not-a-parent-bone")
        group.add(list(range(len(mesh_object.data.vertices))), 1.0, "REPLACE")

        with self.assertRaisesRegex(ValueError, "map only to bones"):
            adopt_skinned_component(root, mesh_object, self._record())

        self.assertIsNone(mesh_object.parent)
        self.assertEqual((), component_records(root))

    def test_remove_preserves_parent_armature(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        armature, _ = self._weight(root, mesh_object)
        armature_name = armature.name
        object_name = mesh_object.name
        record = self._record()
        adopt_skinned_component(root, mesh_object, record)

        removed = remove_skinned_component(root, record.component_id)

        self.assertEqual(record, removed)
        self.assertIsNone(bpy.data.objects.get(object_name))
        self.assertIsNotNone(bpy.data.objects.get(armature_name))
        self.assertEqual((), component_records(root))

    def test_failed_post_inspection_rolls_back_and_removes_created_modifier(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        self._weight(root, mesh_object, add_modifier=False)
        world = mesh_object.matrix_world.copy()

        with mock.patch(
            "blender_adapter.imported_components.inspect_skinned_component",
            side_effect=ValueError("inspection failed"),
        ):
            with self.assertRaisesRegex(ValueError, "inspection failed"):
                adopt_skinned_component(root, mesh_object, self._record())

        self.assertIsNone(mesh_object.parent)
        self.assertEqual(world, mesh_object.matrix_world)
        self.assertFalse(any(item.type == "ARMATURE" for item in mesh_object.modifiers))
        self.assertNotIn("asset_assistant_component_id", mesh_object)
        self.assertEqual((), component_records(root))


if __name__ == "__main__":
    unittest.main()
