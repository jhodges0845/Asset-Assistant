# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import patch

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

import blender_adapter.modification as modification
from blender_adapter.adapter import create_character
from object_core.modification import ModificationRequest, SemanticOperation, plan_modification
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderSemanticModificationPerformanceTests(unittest.TestCase):
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
        root = create_character(provider.mesh(values), name=provider.label, scene=bpy.context.scene)
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root

    def test_semantic_apply_reuses_generated_mesh_for_post_apply_validation(self):
        root = self._human()
        snapshot = modification.inspect_generated_asset(root)
        operation = SemanticOperation(
            "shape",
            "jaw",
            (("profile", "tapered"), ("amount", 0.5)),
        )
        plan = plan_modification(
            snapshot,
            ModificationRequest(semantic_operations=(operation,)),
        )

        with patch.object(modification, "_expected_mesh", wraps=modification._expected_mesh) as expected_mesh:
            result = modification.apply_semantic_modification(root, plan)

        self.assertTrue(result.owns_geometry)
        self.assertEqual(1, len(result.semantic_operations))
        applied = result.semantic_operations[0]
        self.assertEqual(operation.operation, applied.operation)
        self.assertEqual(operation.target, applied.target)
        self.assertEqual(dict(operation.arguments), dict(applied.arguments))
        self.assertEqual(1, expected_mesh.call_count)


if __name__ == "__main__":
    unittest.main()
