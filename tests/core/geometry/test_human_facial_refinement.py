# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.facial_refinement import refine_human_facial_topology


class HumanFacialRefinementTests(unittest.TestCase):
    def _fixture(self, height=180):
        proportions = generate_proportions(HumanoidSpec(height, 95, BodyType.AVERAGE))
        base = generate_deformable_mesh(proportions)
        refined = refine_human_facial_topology(base, proportions)
        return proportions, base.parts[0], refined.parts[0]

    def test_refinement_adds_local_head_resolution(self):
        _, base, refined = self._fixture()
        self.assertGreater(len(refined.vertices), len(base.vertices))
        self.assertGreater(len(refined.faces), len(base.faces))

    def test_refinement_preserves_bounds_and_symmetry(self):
        proportions, base, refined = self._fixture()
        for axis in range(3):
            self.assertAlmostEqual(min(v[axis] for v in refined.vertices), min(v[axis] for v in base.vertices))
            self.assertAlmostEqual(max(v[axis] for v in refined.vertices), max(v[axis] for v in base.vertices))
        self.assertAlmostEqual(max(v[2] for v in refined.vertices), proportions.standing_height_cm)
        self.assertAlmostEqual(min(v[0] for v in refined.vertices), -max(v[0] for v in refined.vertices))

    def test_refinement_preserves_uv_contract_and_manifold_surface(self):
        _, _base, refined = self._fixture()
        self.assertEqual(len(refined.uvs), len(refined.faces))
        for face, face_uvs in zip(refined.faces, refined.uvs):
            self.assertEqual(len(face), len(face_uvs))
        self.assertTrue(is_closed_manifold(refined))

    def test_refinement_is_deterministic_across_supported_heights(self):
        for height in (120, 180, 240):
            with self.subTest(height=height):
                proportions = generate_proportions(HumanoidSpec(height, 95, BodyType.AVERAGE))
                base = generate_deformable_mesh(proportions)
                self.assertEqual(
                    refine_human_facial_topology(base, proportions),
                    refine_human_facial_topology(base, proportions),
                )


if __name__ == "__main__":
    unittest.main()
