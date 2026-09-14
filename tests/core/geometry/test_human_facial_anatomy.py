# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.facial_anatomy import refine_human_local_facial_anatomy
from object_core.geometry.facial_feature_topology import refine_human_facial_feature_loops
from object_core.geometry.facial_refinement import refine_human_facial_topology
from object_core.proportions.landmarks import generate_landmarks


class HumanFacialAnatomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proportions = generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE))
        mesh = generate_deformable_mesh(cls.proportions)
        mesh = refine_human_facial_feature_loops(mesh, cls.proportions)
        cls.before_mesh = refine_human_facial_topology(mesh, cls.proportions)
        cls.after_mesh = refine_human_local_facial_anatomy(cls.before_mesh, cls.proportions)
        cls.before = cls.before_mesh.parts[0]
        cls.after = cls.after_mesh.parts[0]

    def test_refinement_moves_face_without_changing_topology_or_uvs(self):
        self.assertEqual(self.before.faces, self.after.faces)
        self.assertEqual(self.before.uvs, self.after.uvs)
        self.assertEqual(len(self.before.vertices), len(self.after.vertices))
        self.assertNotEqual(self.before.vertices, self.after.vertices)
        self.assertTrue(is_closed_manifold(self.after))

    def test_changes_stay_inside_head_and_front_surface(self):
        landmarks = generate_landmarks(self.proportions)
        chin_z = landmarks["chin"][2]
        crown_z = landmarks["crown"][2]
        changed = [
            (first, second)
            for first, second in zip(self.before.vertices, self.after.vertices)
            if first != second
        ]
        self.assertTrue(changed)
        for first, _second in changed:
            self.assertGreater(first[1], 0.0)
            self.assertGreaterEqual(first[2], chin_z - 1e-7)
            self.assertLessEqual(first[2], crown_z + 1e-7)

    def test_local_anatomy_preserves_left_right_symmetry(self):
        rounded = {
            (round(x, 6), round(y, 6), round(z, 6))
            for x, y, z in self.after.vertices
        }
        for x, y, z in tuple(rounded):
            self.assertIn((round(-x, 6), y, z), rounded)

    def test_global_bounds_and_standing_height_are_preserved(self):
        for axis in range(3):
            self.assertAlmostEqual(
                min(vertex[axis] for vertex in self.before.vertices),
                min(vertex[axis] for vertex in self.after.vertices),
            )
            self.assertAlmostEqual(
                max(vertex[axis] for vertex in self.before.vertices),
                max(vertex[axis] for vertex in self.after.vertices),
            )

    def test_profile_has_nose_eye_brow_and_mouth_separation(self):
        landmarks = generate_landmarks(self.proportions)
        chin_z = landmarks["chin"][2]
        height = landmarks["crown"][2] - chin_z
        front = [vertex for vertex in self.after.vertices if vertex[1] > 0.0]

        def max_y_near(level, radius=0.035):
            candidates = [
                vertex[1]
                for vertex in front
                if abs((vertex[2] - chin_z) / height - level) <= radius
                and abs(vertex[0]) <= self.proportions.head_width_cm * 0.24
            ]
            self.assertTrue(candidates)
            return max(candidates)

        nose = max_y_near(0.43, 0.06)
        eye = max_y_near(0.61, 0.06)
        brow = max_y_near(0.70, 0.06)
        mouth = max_y_near(0.29, 0.055)
        self.assertGreater(nose, eye)
        self.assertGreater(brow, eye)
        self.assertGreater(nose, mouth)

    def test_refinement_is_deterministic_across_supported_extremes(self):
        for height, body_type in ((120, BodyType.SLIM), (240, BodyType.OVERWEIGHT)):
            with self.subTest(height=height, body_type=body_type):
                proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
                mesh = generate_deformable_mesh(proportions)
                mesh = refine_human_facial_feature_loops(mesh, proportions)
                mesh = refine_human_facial_topology(mesh, proportions)
                self.assertEqual(
                    refine_human_local_facial_anatomy(mesh, proportions),
                    refine_human_local_facial_anatomy(mesh, proportions),
                )


if __name__ == "__main__":
    unittest.main()
