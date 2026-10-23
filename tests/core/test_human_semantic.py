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

    def test_limb_edits_follow_authored_side_after_large_movements(self):
        from object_core.providers.human import _human_anatomy
        regions = {r.name: set(r.vertex_indices) for r in _human_anatomy(**self.values).regions}
        for target in ("arm.left", "arm.right", "leg.left", "leg.right"):
            owned = regions[target]
            moved = self.provider.semantic_mesh(self.mesh, self.values, (
                self._operation("scale", target, offset_x=-200, offset_z=-200),))
            result = self.provider.semantic_mesh(moved, self.values, (
                self._operation("scale", target, offset_y=3),))
            for index, (original, changed, final) in enumerate(zip(
                    self.mesh.parts[0].vertices, moved.parts[0].vertices, result.parts[0].vertices)):
                if index in owned:
                    self.assertAlmostEqual(changed[0], original[0] - 200)
                    self.assertAlmostEqual(final[1], changed[1] + 3)
                else:
                    self.assertEqual(original, changed)
                    self.assertEqual(original, final)


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

    def test_glute_fullness_is_local_monotonic_and_topology_preserving(self):
        from math import dist
        from object_core.providers.human import _human_anatomy
        for height, weight in ((180, 95), (160, 55)):
            values = dict(height_cm=height, weight_kg=weight, body_type="average")
            mesh = self.provider.mesh(values)
            anatomy = _human_anatomy(**values)
            arms = {i for r in anatomy.regions if r.name.startswith("arm.") for i in r.vertex_indices}
            base = mesh.parts[0]
            previous = [0.] * len(base.vertices)
            for amount in (0., .6, 1.5):
                changed = self.provider.semantic_mesh(mesh, values, (
                    self._operation("shape", "glutes", profile="full", amount=amount),)).parts[0]
                self.assertEqual(base.faces, changed.faces)
                self.assertEqual(base.uvs, changed.uvs)
                displacement = []
                for i, (a, b) in enumerate(zip(base.vertices, changed.vertices)):
                    self.assertEqual((a[0], a[2]), (b[0], b[2]))
                    self.assertLessEqual(b[1], a[1])
                    if i in arms or a[1] >= 0 or not .47 * height < a[2] < .62 * height:
                        self.assertEqual(a, b)
                    displacement.append(a[1] - b[1])
                    self.assertGreaterEqual(displacement[-1] + 1e-12, previous[i])
                if amount:
                    self.assertGreater(max(displacement), amount * height * .005)
                else:
                    self.assertEqual(base.vertices, changed.vertices)
                previous = displacement
                for face in base.faces:
                    for a, b in zip(face, face[1:] + face[:1]):
                        length = dist(base.vertices[a], base.vertices[b])
                        if length > 1e-7:
                            ratio = dist(changed.vertices[a], changed.vertices[b]) / length
                            self.assertGreater(ratio, .5)
                            self.assertLess(ratio, 2.)

    def test_glutes_do_not_capture_repositioned_arms(self):
        from object_core.providers.human import _human_anatomy
        anatomy = _human_anatomy(**self.values)
        arms = {i for r in anatomy.regions if r.name.startswith("arm.") for i in r.vertex_indices}
        moved = self.provider.semantic_mesh(self.mesh, self.values, (
            self._operation("scale", "arm.left", offset_x=-20, offset_y=-10, offset_z=-10),
            self._operation("scale", "arm.right", offset_x=20, offset_y=-10, offset_z=-10)))
        changed = self.provider.semantic_mesh(moved, self.values, (
            self._operation("shape", "glutes", profile="full", amount=1.5),))
        self.assertTrue(any(a != b for a,b in zip(moved.parts[0].vertices, changed.parts[0].vertices)))
        for i in arms:
            self.assertEqual(moved.parts[0].vertices[i], changed.parts[0].vertices[i])

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
