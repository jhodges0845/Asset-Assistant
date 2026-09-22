# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest import mock

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.components import component_records, inspect_component, remove_component
from blender_adapter.imported_components import adopt_rigid_component
from object_core.components import AttachmentMode, ComponentKind, ComponentRecord
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class ImportedComponentAdoptionTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def _generated_human(self, *, rigged=False):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        if rigged:
            root = create_character(
                mesh,
                name="Human",
                scene=bpy.context.scene,
                skeleton=provider.skeleton(values),
                skin_weights=provider.skin_weights(mesh, values),
            )
        else:
            root = create_character(mesh, name="Human", scene=bpy.context.scene)
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root

    def _external_mesh(self, name="Imported Hat"):
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

    def _record(
        self,
        *,
        target="asset_root",
        component_id="imported-hat-001",
        owns_materials=False,
    ):
        return ComponentRecord(
            component_id=component_id,
            kind=ComponentKind.ACCESSORY,
            provider_key="artist_authored",
            attachment_target=target,
            attachment_mode=AttachmentMode.RIGID,
            owns_geometry=True,
            owns_materials=owns_materials,
            owns_rig=False,
        )

    def test_external_mesh_can_be_adopted_without_copying_geometry(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        mesh_data = mesh_object.data
        world = mesh_object.matrix_world.copy()
        record = self._record()

        component_root = adopt_rigid_component(root, mesh_object, record)

        self.assertEqual(component_root, mesh_object.parent)
        self.assertEqual(mesh_data, mesh_object.data)
        self.assertEqual(world, mesh_object.matrix_world)
        self.assertEqual(record, inspect_component(root, record.component_id))
        self.assertEqual((record,), component_records(root))

    def test_adopted_mesh_enters_existing_remove_lifecycle(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        object_name = mesh_object.name
        record = self._record()
        adopt_rigid_component(root, mesh_object, record)

        remove_component(root, record.component_id)

        self.assertIsNone(bpy.data.objects.get(object_name))
        self.assertEqual((), component_records(root))

    def test_bone_adoption_preserves_mesh_world_transform(self):
        root = self._generated_human(rigged=True)
        mesh_object = self._external_mesh()
        world = mesh_object.matrix_world.copy()
        record = self._record(target="bone:hand.right")

        component_root = adopt_rigid_component(root, mesh_object, record)

        self.assertEqual("ARMATURE", component_root.parent.type)
        self.assertEqual("BONE", component_root.parent_type)
        self.assertEqual("hand.right", component_root.parent_bone)
        self.assertEqual(world, mesh_object.matrix_world)
        self.assertEqual(record, inspect_component(root, record.component_id))

    def test_asset_owned_mesh_cannot_be_adopted_as_external_component(self):
        root = self._generated_human()
        body_mesh = next(child for child in root.children if child.type == "MESH")

        with self.assertRaisesRegex(ValueError, "already part"):
            adopt_rigid_component(root, body_mesh, self._record())

        self.assertEqual((), component_records(root))

    def test_mesh_with_children_is_rejected_before_ownership_transfer(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        child = bpy.data.objects.new("External Child", None)
        bpy.context.scene.collection.objects.link(child)
        child.parent = mesh_object

        with self.assertRaisesRegex(ValueError, "no child objects"):
            adopt_rigid_component(root, mesh_object, self._record())

        self.assertIsNone(mesh_object.parent)
        self.assertEqual((), component_records(root))

    def test_armature_driven_mesh_is_not_mislabeled_as_rigid(self):
        root = self._generated_human(rigged=True)
        mesh_object = self._external_mesh()
        armature = next(child for child in root.children if child.type == "ARMATURE")
        modifier = mesh_object.modifiers.new(name="External Rig", type="ARMATURE")
        modifier.object = armature

        with self.assertRaisesRegex(ValueError, "skinned component adoption"):
            adopt_rigid_component(root, mesh_object, self._record())

        self.assertIsNone(mesh_object.parent)
        self.assertEqual((), component_records(root))

    def test_imported_adoption_does_not_claim_material_ownership(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()

        with self.assertRaisesRegex(ValueError, "does not claim material ownership"):
            adopt_rigid_component(root, mesh_object, self._record(owns_materials=True))

        self.assertIsNone(mesh_object.parent)
        self.assertEqual((), component_records(root))

    def test_failed_attachment_rolls_back_external_mesh_parent_and_registry(self):
        root = self._generated_human(rigged=True)
        mesh_object = self._external_mesh()
        world = mesh_object.matrix_world.copy()
        record = self._record(target="bone:not-a-bone")

        with self.assertRaisesRegex(ValueError, "attachment bone does not exist"):
            adopt_rigid_component(root, mesh_object, record)

        self.assertIsNone(mesh_object.parent)
        self.assertEqual(world, mesh_object.matrix_world)
        self.assertNotIn("asset_assistant_component_id", mesh_object)
        self.assertEqual((), component_records(root))

    def test_failed_post_adoption_inspection_restores_existing_object_metadata(self):
        root = self._generated_human()
        mesh_object = self._external_mesh()
        mesh_object["component_part_name"] = "artist-label"
        world = mesh_object.matrix_world.copy()

        with mock.patch(
            "blender_adapter.imported_components.inspect_component",
            side_effect=ValueError("inspection failed"),
        ):
            with self.assertRaisesRegex(ValueError, "inspection failed"):
                adopt_rigid_component(root, mesh_object, self._record())

        self.assertIsNone(mesh_object.parent)
        self.assertEqual(world, mesh_object.matrix_world)
        self.assertEqual("artist-label", mesh_object["component_part_name"])
        self.assertNotIn("asset_assistant_component_id", mesh_object)
        self.assertEqual((), component_records(root))


if __name__ == "__main__":
    unittest.main()
