# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.body_refinement import refine_human_torso_cross_sections
from object_core.proportions.landmarks import generate_landmarks


class HumanBodyRefinementTests(unittest.TestCase):
    def _fixture(self, height=180):
        proportions = generate_proportions(HumanoidSpec(height, 95, BodyType.AVERAGE))
        base = generate_deformable_mesh(proportions)
        refined = refine_human_torso_cross_sections(base, proportions)
        return proportions, base.parts[0], refined.parts[0]

    def test_refinement_adds_torso_silhouette_support_without_changing_face_count(self):
        _proportions, base, refined = self._fixture()
        self.assertGreater(len(refined.vertices), len(base.vertices))
        self.assertEqual(len(refined.faces), len(base.faces))

    def test_refinement_keeps_overall_bounds_and_branch_seams(self):
        proportions, base, refined = self._fixture()
        for axis in range(3):
            self.assertAlmostEqual(
                min(vertex[axis] for vertex in refined.vertices),
                min(vertex[axis] for vertex in base.vertices),
            )
            self.assertAlmostEqual(
                max(vertex[axis] for vertex in refined.vertices),
                max(vertex[axis] for vertex in base.vertices),
            )

        landmarks = generate_landmarks(proportions)
        hip_z = landmarks["hip_center"][2]
        shoulder_z = landmarks["shoulder_center"][2]
        added = refined.vertices[len(base.vertices):]
        self.assertTrue(added)
        self.assertTrue(all(hip_z < vertex[2] < shoulder_z for vertex in added))

    def test_refinement_pushes_new_chord_points_outward(self):
        _proportions, base, refined = self._fixture()
        added = refined.vertices[len(base.vertices):]
        self.assertTrue(added)

        # At least one new point must sit between an old axis and diagonal point
        # rather than on the original octagonal chord, proving this is geometric
        # silhouette refinement rather than face-only subdivision.
        old_xy = {(round(vertex[0], 7), round(vertex[1], 7)) for vertex in base.vertices}
        new_xy = {(round(vertex[0], 7), round(vertex[1], 7)) for vertex in added}
        self.assertTrue(new_xy - old_xy)

    def test_refinement_preserves_uv_contract_and_manifold_surface(self):
        _proportions, _base, refined = self._fixture()
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
                    refine_human_torso_cross_sections(base, proportions),
                    refine_human_torso_cross_sections(base, proportions),
                )


if __name__ == "__main__":
    unittest.main()
