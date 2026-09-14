# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.body_refinement import refine_human_torso_cross_sections
from object_core.geometry.shoulder_refinement import refine_human_shoulders
from object_core.proportions.landmarks import generate_landmarks


class HumanShoulderRefinementTests(unittest.TestCase):
    def _fixture(self, height=180, body_type=BodyType.AVERAGE):
        proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
        base = generate_deformable_mesh(proportions)
        torso = refine_human_torso_cross_sections(base, proportions)
        refined = refine_human_shoulders(torso, proportions)
        return proportions, torso.parts[0], refined.parts[0]

    def test_refinement_changes_only_geometry_not_topology_or_uv_contract(self):
        _proportions, before, after = self._fixture()
        self.assertEqual(after.faces, before.faces)
        self.assertEqual(after.uvs, before.uvs)
        self.assertEqual(len(after.vertices), len(before.vertices))
        self.assertTrue(any(first != second for first, second in zip(before.vertices, after.vertices)))
        self.assertTrue(is_closed_manifold(after))

    def test_changes_are_local_to_shoulder_neighborhoods(self):
        proportions, before, after = self._fixture()
        landmarks = generate_landmarks(proportions)
        shoulders = (landmarks["shoulder.left"], landmarks["shoulder.right"])
        radius = max(
            proportions.upper_arm_thickness_cm * 1.65,
            proportions.shoulder_width_cm * 0.18,
        )
        changed = [
            (first, second)
            for first, second in zip(before.vertices, after.vertices)
            if first != second
        ]
        self.assertTrue(changed)
        for first, _second in changed:
            nearest = min(
                sum((first[index] - shoulder[index]) ** 2 for index in range(3)) ** 0.5
                for shoulder in shoulders
            )
            self.assertLess(nearest, radius + 1e-7)

    def test_outer_shoulder_corner_slopes_downward(self):
        proportions, before, after = self._fixture()
        landmarks = generate_landmarks(proportions)
        shoulder_z = landmarks["shoulder_center"][2]
        candidates = []
        for first, second in zip(before.vertices, after.vertices):
            if abs(first[2] - shoulder_z) > 1e-7:
                continue
            if abs(first[0]) < proportions.shoulder_width_cm * 0.35:
                continue
            if second[2] < first[2] - 1e-7:
                candidates.append((first, second))
        self.assertTrue(candidates)

    def test_neutral_result_remains_left_right_symmetric(self):
        _proportions, _before, after = self._fixture()
        rounded = {
            (round(x, 6), round(y, 6), round(z, 6))
            for x, y, z in after.vertices
        }
        for x, y, z in tuple(rounded):
            self.assertIn((round(-x, 6), y, z), rounded)

    def test_standing_height_is_preserved(self):
        _proportions, before, after = self._fixture()
        self.assertAlmostEqual(
            min(vertex[2] for vertex in after.vertices),
            min(vertex[2] for vertex in before.vertices),
        )
        self.assertAlmostEqual(
            max(vertex[2] for vertex in after.vertices),
            max(vertex[2] for vertex in before.vertices),
        )

    def test_refinement_is_deterministic_across_supported_heights_and_body_types(self):
        for height in (120, 180, 240):
            for body_type in (BodyType.SLIM, BodyType.AVERAGE, BodyType.HEAVY):
                with self.subTest(height=height, body_type=body_type):
                    proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
                    mesh = refine_human_torso_cross_sections(
                        generate_deformable_mesh(proportions), proportions
                    )
                    self.assertEqual(
                        refine_human_shoulders(mesh, proportions),
                        refine_human_shoulders(mesh, proportions),
                    )


if __name__ == "__main__":
    unittest.main()
