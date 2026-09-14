# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.cranium_refinement import refine_human_cranium_cross_sections
from object_core.geometry.facial_refinement import refine_human_facial_topology
from object_core.proportions.landmarks import generate_landmarks


class HumanCraniumRefinementTests(unittest.TestCase):
    def _fixture(self, height=180):
        proportions = generate_proportions(HumanoidSpec(height, 95, BodyType.AVERAGE))
        base = generate_deformable_mesh(proportions)
        facial = refine_human_facial_topology(base, proportions)
        refined = refine_human_cranium_cross_sections(facial, proportions)
        return proportions, facial.parts[0], refined.parts[0]

    def test_refinement_adds_head_circumference_support(self):
        proportions, before, after = self._fixture()
        self.assertGreater(len(after.vertices), len(before.vertices))
        landmarks = generate_landmarks(proportions)
        chin_z = landmarks["chin"][2]
        crown_z = landmarks["crown"][2]
        added = after.vertices[len(before.vertices):]
        self.assertTrue(added)
        self.assertTrue(all(chin_z < vertex[2] < crown_z for vertex in added))

    def test_refinement_preserves_overall_bounds(self):
        _proportions, before, after = self._fixture()
        for axis in range(3):
            self.assertAlmostEqual(min(v[axis] for v in after.vertices), min(v[axis] for v in before.vertices))
            self.assertAlmostEqual(max(v[axis] for v in after.vertices), max(v[axis] for v in before.vertices))

    def test_refinement_preserves_uvs_and_manifold_surface(self):
        _proportions, _before, after = self._fixture()
        self.assertEqual(len(after.uvs), len(after.faces))
        for face, face_uvs in zip(after.faces, after.uvs):
            self.assertEqual(len(face), len(face_uvs))
        self.assertTrue(is_closed_manifold(after))

    def test_refinement_is_deterministic_across_supported_heights(self):
        for height in (120, 180, 240):
            with self.subTest(height=height):
                proportions = generate_proportions(HumanoidSpec(height, 95, BodyType.AVERAGE))
                base = generate_deformable_mesh(proportions)
                facial = refine_human_facial_topology(base, proportions)
                self.assertEqual(
                    refine_human_cranium_cross_sections(facial, proportions),
                    refine_human_cranium_cross_sections(facial, proportions),
                )

    def test_refinement_requires_expected_inputs(self):
        proportions = generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE))
        with self.assertRaises(TypeError):
            refine_human_cranium_cross_sections(object(), proportions)
        with self.assertRaises(TypeError):
            refine_human_cranium_cross_sections(generate_deformable_mesh(proportions), object())


if __name__ == "__main__":
    unittest.main()
