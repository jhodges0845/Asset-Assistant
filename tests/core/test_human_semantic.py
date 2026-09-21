# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from object_core.modification import AssetSnapshot, ModificationRequest, SemanticOperation, plan_modification
from object_core.objects import get_provider


class HumanSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = get_provider("human")
        cls.values = {"height_cm": 180.0, "weight_kg": 70.0, "body_type": "average"}
        # ObjectMesh and its nested contracts are immutable. Reusing the neutral
        # Human here avoids regenerating the full refined topology for every
        # semantic test while preserving test isolation: semantic_mesh returns a
        # new mesh instead of mutating this shared fixture.
        cls.mesh = cls.provider.mesh(cls.values)

    def _operation(self, operation, target, **arguments):
        return SemanticOperation(operation, target, tuple(arguments.items()))

    def test_human_region_shape_and_scale_are_executable(self):
        capabilities = set(self.provider.semantic_apply_capabilities)
        self.assertIn(("face", "shape"), capabilities)
        self.assertIn(("jaw", "shape"), capabilities)
        self.assertIn(("cheeks", "scale"), capabilities)
        self.assertIn(("shoulders", "scale"), capabilities)
        self.assertNotIn(("hair", "add_component"), capabilities)

    def test_face_shape_preserves_topology_and_moves_vertices(self):
        mesh = self.mesh
        changed = self.provider.semantic_mesh(
            mesh,
            self.values,
            (self._operation("shape", "face", profile="narrow", amount=0.8),),
        )
        self.assertEqual(mesh.parts[0].faces, changed.parts[0].faces)
        self.assertEqual(mesh.parts[0].uvs, changed.parts[0].uvs)
        self.assertEqual(len(mesh.parts[0].vertices), len(changed.parts[0].vertices))
        self.assertNotEqual(mesh.parts[0].vertices, changed.parts[0].vertices)

    def test_jaw_and_cheek_profiles_preserve_topology(self):
        mesh = self.mesh
        changed = self.provider.semantic_mesh(
            mesh,
            self.values,
            (
                self._operation("shape", "jaw", profile="tapered", amount=0.65),
                self._operation("shape", "cheeks", profile="high", amount=0.45),
            ),
        )
        self.assertEqual(mesh.parts[0].faces, changed.parts[0].faces)
        self.assertEqual(mesh.parts[0].uvs, changed.parts[0].uvs)
        self.assertEqual(len(mesh.parts[0].vertices), len(changed.parts[0].vertices))
        self.assertNotEqual(mesh.parts[0].vertices, changed.parts[0].vertices)

    def test_left_arm_scale_does_not_move_rightmost_arm_vertex(self):
        mesh = self.mesh
        changed = self.provider.semantic_mesh(
            mesh,
            self.values,
            (self._operation("scale", "arm.left", factor=1.15),),
        )
        original = mesh.parts[0].vertices
        result = changed.parts[0].vertices
        rightmost = max(range(len(original)), key=lambda index: original[index][0])
        self.assertEqual(original[rightmost], result[rightmost])
        self.assertNotEqual(original, result)

    def test_profiles_can_compose_into_character_shape_recipe(self):
        mesh = self.mesh
        operations = (
            self._operation("shape", "torso", profile="athletic", amount=0.7),
            self._operation("shape", "shoulders", profile="broad", amount=0.5),
            self._operation("shape", "head", profile="oval", amount=0.5),
            self._operation("shape", "face", profile="defined", amount=0.6),
            self._operation("shape", "face", profile="narrow", amount=0.35),
            self._operation("shape", "jaw", profile="tapered", amount=0.5),
            self._operation("shape", "cheeks", profile="high", amount=0.35),
        )
        changed = self.provider.semantic_mesh(mesh, self.values, operations)
        self.assertEqual(mesh.parts[0].faces, changed.parts[0].faces)
        self.assertNotEqual(mesh.parts[0].vertices, changed.parts[0].vertices)

    def test_planner_accepts_human_geometry_semantics_but_blocks_components(self):
        snapshot = AssetSnapshot(
            asset_id="human-1",
            provider_key="human",
            provider_label="Human",
            parameters=tuple(self.values.items()),
            owns_geometry=True,
        )
        shape_plan = plan_modification(
            snapshot,
            ModificationRequest(semantic_operations=(self._operation("shape", "jaw", profile="tapered"),)),
        )
        self.assertTrue(shape_plan.safe_to_apply)
        self.assertEqual(("geometry",), shape_plan.rebuild_components)

        hair_plan = plan_modification(
            snapshot,
            ModificationRequest(semantic_operations=(self._operation("add_component", "hair", style="long"),)),
        )
        self.assertFalse(hair_plan.safe_to_apply)
        self.assertTrue(any("hair" in blocker for blocker in hair_plan.blockers))

    def test_unknown_profile_is_rejected_by_provider(self):
        mesh = self.mesh
        with self.assertRaisesRegex(ValueError, "Unsupported Human semantic profile"):
            self.provider.semantic_mesh(
                mesh,
                self.values,
                (self._operation("shape", "face", profile="not-a-profile"),),
            )


if __name__ == "__main__":
    unittest.main()
