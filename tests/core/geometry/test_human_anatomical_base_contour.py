# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.anatomical_base_contour import refine_human_anatomical_base_contour
from object_core.proportions.landmarks import generate_landmarks


class HumanAnatomicalBaseContourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proportions = generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE))
        cls.before_mesh = generate_deformable_mesh(cls.proportions)
        cls.after_mesh = refine_human_anatomical_base_contour(cls.before_mesh, cls.proportions)
        cls.before = cls.before_mesh.parts[0]
        cls.after = cls.after_mesh.parts[0]

    def test_changes_geometry_without_changing_topology_or_uvs(self):
        self.assertEqual(self.before.faces, self.after.faces)
        self.assertEqual(self.before.uvs, self.after.uvs)
        self.assertEqual(len(self.before.vertices), len(self.after.vertices))
        self.assertNotEqual(self.before.vertices, self.after.vertices)
        self.assertTrue(is_closed_manifold(self.after))

    def test_preserves_left_right_symmetry_and_standing_height(self):
        rounded = {(round(x, 6), round(y, 6), round(z, 6)) for x, y, z in self.after.vertices}
        for x, y, z in tuple(rounded):
            self.assertIn((round(-x, 6), y, z), rounded)
        self.assertAlmostEqual(
            min(vertex[2] for vertex in self.before.vertices),
            min(vertex[2] for vertex in self.after.vertices),
        )
        self.assertAlmostEqual(
            max(vertex[2] for vertex in self.before.vertices),
            max(vertex[2] for vertex in self.after.vertices),
        )

    def test_torso_establishes_waist_contour_without_expanding_bounds(self):
        landmarks = generate_landmarks(self.proportions)
        hip_z = landmarks["hip_center"][2]
        shoulder_z = landmarks["shoulder_center"][2]
        target_z = hip_z + (shoulder_z - hip_z) * 0.36
        tolerance = (shoulder_z - hip_z) * 0.08

        before = [
            abs(x) for x, _y, z in self.before.vertices
            if abs(z - target_z) <= tolerance and abs(x) <= self.proportions.waist_width_cm
        ]
        after = [
            abs(x) for x, _y, z in self.after.vertices
            if abs(z - target_z) <= tolerance and abs(x) <= self.proportions.waist_width_cm
        ]
        self.assertTrue(before and after)
        self.assertLessEqual(max(after), max(before))
        self.assertLess(max(after), max(before) + 1e-9)

    def test_leg_contour_narrows_near_knee_and_ankle(self):
        landmarks = generate_landmarks(self.proportions)
        hip_x = landmarks["hip.left"][0]
        knee_z = landmarks["knee.left"][2]
        ankle_z = landmarks["ankle.left"][2]
        tolerance = self.proportions.standing_height_cm * 0.012

        def local_half_width(part, z_target):
            xs = [
                abs(x - hip_x)
                for x, _y, z in part.vertices
                if x >= 0.0 and abs(z - z_target) <= tolerance
                and abs(x - hip_x) <= self.proportions.thigh_thickness_cm * 1.3
            ]
            self.assertTrue(xs)
            return max(xs)

        knee_before = local_half_width(self.before, knee_z)
        knee_after = local_half_width(self.after, knee_z)
        ankle_before = local_half_width(self.before, ankle_z + self.proportions.foot_height_cm)
        ankle_after = local_half_width(self.after, ankle_z + self.proportions.foot_height_cm)
        self.assertLessEqual(knee_after, knee_before)
        self.assertLessEqual(ankle_after, ankle_before)

    def test_refinement_is_deterministic_across_supported_extremes(self):
        for height, body_type in ((120, BodyType.SLIM), (240, BodyType.OVERWEIGHT)):
            with self.subTest(height=height, body_type=body_type):
                proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
                mesh = generate_deformable_mesh(proportions)
                self.assertEqual(
                    refine_human_anatomical_base_contour(mesh, proportions),
                    refine_human_anatomical_base_contour(mesh, proportions),
                )

    def test_requires_expected_inputs(self):
        with self.assertRaises(TypeError):
            refine_human_anatomical_base_contour(None, self.proportions)
        with self.assertRaises(TypeError):
            refine_human_anatomical_base_contour(self.before_mesh, None)


if __name__ == "__main__":
    unittest.main()
