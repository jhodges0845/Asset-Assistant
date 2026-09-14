# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.facial_feature_topology import refine_human_facial_feature_loops
from object_core.proportions.landmarks import generate_landmarks


class HumanFacialFeatureTopologyTests(unittest.TestCase):
    def _fixture(self, height=180, body_type=BodyType.AVERAGE):
        proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
        before = generate_deformable_mesh(proportions).parts[0]
        after = refine_human_facial_feature_loops(
            generate_deformable_mesh(proportions), proportions
        ).parts[0]
        return proportions, before, after

    def test_refinement_adds_shared_head_section_loops(self):
        proportions, before, after = self._fixture()
        landmarks = generate_landmarks(proportions)
        chin_z = landmarks["chin"][2]
        crown_z = landmarks["crown"][2]
        self.assertGreater(len(after.vertices), len(before.vertices))
        self.assertGreater(len(after.faces), len(before.faces))
        added = after.vertices[len(before.vertices):]
        self.assertTrue(added)
        self.assertTrue(all(chin_z < vertex[2] < crown_z for vertex in added))

    def test_refinement_preserves_closed_manifold_and_uv_contract(self):
        _proportions, _before, after = self._fixture()
        self.assertTrue(is_closed_manifold(after))
        self.assertEqual(len(after.faces), len(after.uvs))
        for face, face_uvs in zip(after.faces, after.uvs):
            self.assertEqual(len(face), len(face_uvs))

    def test_refinement_preserves_standing_height_and_global_bounds(self):
        _proportions, before, after = self._fixture()
        for axis in range(3):
            self.assertAlmostEqual(
                min(vertex[axis] for vertex in before.vertices),
                min(vertex[axis] for vertex in after.vertices),
            )
            self.assertAlmostEqual(
                max(vertex[axis] for vertex in before.vertices),
                max(vertex[axis] for vertex in after.vertices),
            )

    def test_new_feature_points_are_left_right_symmetric(self):
        _proportions, before, after = self._fixture()
        rounded = {
            (round(x, 6), round(y, 6), round(z, 6))
            for x, y, z in after.vertices[len(before.vertices):]
        }
        for x, y, z in tuple(rounded):
            self.assertIn((round(-x, 6), y, z), rounded)

    def test_feature_loops_add_levels_near_mouth_nose_eye_and_brow(self):
        proportions, before, after = self._fixture()
        landmarks = generate_landmarks(proportions)
        chin_z = landmarks["chin"][2]
        height = landmarks["crown"][2] - chin_z
        added_levels = sorted({round((z - chin_z) / height, 2) for _x, _y, z in after.vertices[len(before.vertices):]})
        for target in (0.28, 0.43, 0.59, 0.70):
            self.assertLess(min(abs(level - target) for level in added_levels), 0.08)

    def test_refinement_is_deterministic_across_supported_extremes(self):
        for height in (120, 180, 240):
            for body_type in (BodyType.SLIM, BodyType.AVERAGE, BodyType.OVERWEIGHT):
                with self.subTest(height=height, body_type=body_type):
                    proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
                    mesh = generate_deformable_mesh(proportions)
                    self.assertEqual(
                        refine_human_facial_feature_loops(mesh, proportions),
                        refine_human_facial_feature_loops(mesh, proportions),
                    )


if __name__ == "__main__":
    unittest.main()
