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

    def test_refinement_keeps_standing_height_and_branch_seam_planes(self):
        proportions, base, refined = self._fixture()
        self.assertAlmostEqual(
            min(vertex[2] for vertex in refined.vertices),
            min(vertex[2] for vertex in base.vertices),
        )
        self.assertAlmostEqual(
            max(vertex[2] for vertex in refined.vertices),
            max(vertex[2] for vertex in base.vertices),
        )

        landmarks = generate_landmarks(proportions)
        hip_z = landmarks["hip_center"][2]
        shoulder_z = landmarks["shoulder_center"][2]
        for seam_z in (hip_z, shoulder_z):
            base_ring = sorted(
                vertex for vertex in base.vertices if abs(vertex[2] - seam_z) < 1e-7
            )
            refined_ring = sorted(
                vertex for vertex in refined.vertices[:len(base.vertices)] if abs(vertex[2] - seam_z) < 1e-7
            )
            self.assertEqual(refined_ring, base_ring)

    def test_refinement_pushes_new_chord_points_outward(self):
        _proportions, base, refined = self._fixture()
        added = refined.vertices[len(base.vertices):]
        self.assertTrue(added)
        old_xy = {(round(vertex[0], 7), round(vertex[1], 7)) for vertex in base.vertices}
        new_xy = {(round(vertex[0], 7), round(vertex[1], 7)) for vertex in added}
        self.assertTrue(new_xy - old_xy)

    def test_anatomy_shapes_existing_interior_torso_vertices(self):
        proportions, base, refined = self._fixture()
        landmarks = generate_landmarks(proportions)
        hip_z = landmarks["hip_center"][2]
        shoulder_z = landmarks["shoulder_center"][2]
        changed = []
        for before, after in zip(base.vertices, refined.vertices[:len(base.vertices)]):
            if hip_z < before[2] < shoulder_z and before != after:
                changed.append((before, after))
        self.assertTrue(changed)
        self.assertTrue(any(abs(after[0] - before[0]) > 1e-7 for before, after in changed))
        self.assertTrue(any(abs(after[1] - before[1]) > 1e-7 for before, after in changed))

    def test_front_and_back_receive_distinct_profile_contour(self):
        proportions, base, refined = self._fixture()
        landmarks = generate_landmarks(proportions)
        hip_z = landmarks["hip_center"][2]
        shoulder_z = landmarks["shoulder_center"][2]
        front_deltas = []
        back_deltas = []
        for before, after in zip(base.vertices, refined.vertices[:len(base.vertices)]):
            if not (hip_z < before[2] < shoulder_z):
                continue
            delta = abs(after[1]) - abs(before[1])
            if before[1] > 1e-7:
                front_deltas.append(delta)
            elif before[1] < -1e-7:
                back_deltas.append(delta)
        self.assertTrue(front_deltas)
        self.assertTrue(back_deltas)
        self.assertNotAlmostEqual(max(front_deltas), max(back_deltas))

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
