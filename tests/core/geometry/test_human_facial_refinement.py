# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.facial_refinement import refine_human_facial_topology
from object_core.proportions.landmarks import generate_landmarks


class HumanFacialRefinementTests(unittest.TestCase):
    def _fixture(self, height=180):
        proportions = generate_proportions(HumanoidSpec(height, 95, BodyType.AVERAGE))
        base = generate_deformable_mesh(proportions)
        refined = refine_human_facial_topology(base, proportions)
        return proportions, base.parts[0], refined.parts[0]

    @staticmethod
    def _support_vertices(base, refined):
        return refined.vertices[len(base.vertices):]

    def _front_support_near(self, proportions, base, refined, level, tolerance=0.065):
        points = generate_landmarks(proportions)
        chin_z = points["chin"][2]
        crown_z = points["crown"][2]
        target_z = chin_z + (crown_z - chin_z) * level
        half_width = proportions.head_width_cm * 0.5
        candidates = [
            vertex for vertex in self._support_vertices(base, refined)
            if vertex[1] > 0.0
            and abs(vertex[0]) <= half_width * 0.62
            and abs(vertex[2] - target_z) <= proportions.head_height_cm * tolerance
        ]
        self.assertTrue(candidates, "expected front facial support vertices near requested level")
        return max(vertex[1] for vertex in candidates)

    def test_refinement_adds_local_head_resolution(self):
        _, base, refined = self._fixture()
        self.assertGreater(len(refined.vertices), len(base.vertices))
        self.assertGreater(len(refined.faces), len(base.faces))

    def test_neutral_support_anatomy_separates_nose_brow_and_eye_plane(self):
        proportions, base, refined = self._fixture()
        nose = self._front_support_near(proportions, base, refined, 0.45)
        eyes = self._front_support_near(proportions, base, refined, 0.59)
        brow = self._front_support_near(proportions, base, refined, 0.73)
        self.assertGreater(nose - eyes, proportions.head_depth_cm * 0.04)
        self.assertGreater(brow, eyes)

    def test_neutral_support_anatomy_separates_mouth_from_lower_jaw(self):
        proportions, base, refined = self._fixture()
        jaw = self._front_support_near(proportions, base, refined, 0.18)
        mouth = self._front_support_near(proportions, base, refined, 0.31)
        self.assertGreater(mouth, jaw)

    def test_support_anatomy_preserves_left_right_symmetry(self):
        _, base, refined = self._fixture()
        support = self._support_vertices(base, refined)
        for x, y, z in support:
            self.assertTrue(
                any(
                    abs(other[0] + x) < 1e-7
                    and abs(other[1] - y) < 1e-7
                    and abs(other[2] - z) < 1e-7
                    for other in support
                )
            )

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
