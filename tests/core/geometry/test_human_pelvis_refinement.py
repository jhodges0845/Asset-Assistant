# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.body_refinement import refine_human_torso_cross_sections
from object_core.geometry.pelvis_refinement import refine_human_pelvis
from object_core.proportions.landmarks import generate_landmarks


class HumanPelvisRefinementTests(unittest.TestCase):
    def _fixture(self, height=180, body_type=BodyType.AVERAGE):
        proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
        base = generate_deformable_mesh(proportions)
        torso = refine_human_torso_cross_sections(base, proportions)
        refined = refine_human_pelvis(torso, proportions)
        return proportions, torso.parts[0], refined.parts[0]

    def test_refinement_changes_geometry_without_changing_topology_or_uvs(self):
        _proportions, before, after = self._fixture()
        self.assertEqual(after.faces, before.faces)
        self.assertEqual(after.uvs, before.uvs)
        self.assertEqual(len(after.vertices), len(before.vertices))
        self.assertTrue(any(first != second for first, second in zip(before.vertices, after.vertices)))
        self.assertTrue(is_closed_manifold(after))

    def test_changes_are_local_to_hip_neighborhoods(self):
        proportions, before, after = self._fixture()
        landmarks = generate_landmarks(proportions)
        hips = (landmarks["hip.left"], landmarks["hip.right"])
        radius = max(
            proportions.thigh_thickness_cm * 1.85,
            proportions.hip_width_cm * 0.24,
        )
        changed = [
            (first, second)
            for first, second in zip(before.vertices, after.vertices)
            if first != second
        ]
        self.assertTrue(changed)
        for first, _second in changed:
            nearest = min(
                sum((first[index] - hip[index]) ** 2 for index in range(3)) ** 0.5
                for hip in hips
            )
            self.assertLess(nearest, radius + 1e-7)

    def test_posterior_hip_gains_glute_volume(self):
        proportions, before, after = self._fixture()
        hip_z = generate_landmarks(proportions)["hip_center"][2]
        changed = [
            (first, second)
            for first, second in zip(before.vertices, after.vertices)
            if first[1] < -1e-7
            and abs(first[2] - hip_z) < proportions.thigh_thickness_cm
            and second[1] < first[1] - 1e-7
        ]
        self.assertTrue(changed)

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
            for body_type in (BodyType.SLIM, BodyType.AVERAGE, BodyType.OVERWEIGHT):
                with self.subTest(height=height, body_type=body_type):
                    proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
                    mesh = refine_human_torso_cross_sections(
                        generate_deformable_mesh(proportions), proportions
                    )
                    self.assertEqual(
                        refine_human_pelvis(mesh, proportions),
                        refine_human_pelvis(mesh, proportions),
                    )


if __name__ == "__main__":
    unittest.main()
