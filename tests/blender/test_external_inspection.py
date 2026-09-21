# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.external_inspection import BLOCKED, REDUCED, SUPPORTED, inspect_external_object
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class ExternalAdoptionInspectionTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def _human(self, *, rigged=False):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        kwargs = {}
        if rigged:
            kwargs.update(
                skeleton=provider.skeleton(values),
                skin_weights=provider.skin_weights(mesh, values),
            )
        root = create_character(mesh, name="Human", scene=bpy.context.scene, **kwargs)
        root["object_type"] = provider.key
        return root

    def _mesh(self, name="External Mesh"):
        mesh = bpy.data.meshes.new(name + ".Mesh")
        mesh.from_pydata(((-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.0, 0.5, 0.0)), (), ((0, 1, 2),))
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        return obj

    def test_plain_external_mesh_is_supported_without_mutation(self):
        root = self._human()
        obj = self._mesh()
        parent_before = obj.parent

        result = inspect_external_object(root, obj)

        self.assertEqual(SUPPORTED, result.status)
        self.assertTrue(result.can_adopt)
        self.assertEqual("rigid", result.suggested_behavior)
        self.assertEqual(parent_before, obj.parent)
        self.assertNotIn("asset_assistant_component_id", obj)

    def test_child_hierarchy_reports_reduced_capability(self):
        root = self._human()
        obj = self._mesh()
        child = bpy.data.objects.new("External Child", None)
        bpy.context.scene.collection.objects.link(child)
        child.parent = obj

        result = inspect_external_object(root, obj)

        self.assertEqual(REDUCED, result.status)
        self.assertTrue(result.can_adopt)
        self.assertTrue(any("Child-object hierarchies" in reason for reason in result.reasons))

    def test_external_armature_reports_reduced_capability(self):
        root = self._human(rigged=True)
        obj = self._mesh()
        armature_data = bpy.data.armatures.new("External Rig.Data")
        external_armature = bpy.data.objects.new("External Rig", armature_data)
        bpy.context.scene.collection.objects.link(external_armature)
        modifier = obj.modifiers.new(name="External Rig", type="ARMATURE")
        modifier.object = external_armature

        result = inspect_external_object(root, obj)

        self.assertEqual(REDUCED, result.status)
        self.assertEqual("external_rig", result.suggested_behavior)
        self.assertTrue(result.detected_armature)

    def test_generated_body_geometry_is_blocked(self):
        root = self._human()
        body = next(child for child in root.children if child.type == "MESH")

        result = inspect_external_object(root, body)

        self.assertEqual(BLOCKED, result.status)
        self.assertFalse(result.can_adopt)

    def test_multiple_armatures_are_blocked(self):
        root = self._human(rigged=True)
        obj = self._mesh()
        for index in range(2):
            armature_data = bpy.data.armatures.new("Rig%d.Data" % index)
            armature = bpy.data.objects.new("Rig%d" % index, armature_data)
            bpy.context.scene.collection.objects.link(armature)
            modifier = obj.modifiers.new(name="Rig%d" % index, type="ARMATURE")
            modifier.object = armature

        result = inspect_external_object(root, obj)

        self.assertEqual(BLOCKED, result.status)
        self.assertFalse(result.can_adopt)


if __name__ == "__main__":
    unittest.main()
