# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.body_refinement import refine_human_torso_cross_sections
from object_core.geometry.limb_refinement import refine_human_limb_cross_sections


class HumanLimbRefinementTests(unittest.TestCase):
    def _fixture(self, height=180):
        proportions = generate_proportions(HumanoidSpec(height, 95, BodyType.AVERAGE))
        base = generate_deformable_mesh(proportions)
        torso = refine_human_torso_cross_sections(base, proportions)
        refined = refine_human_limb_cross_sections(torso, proportions)
        return proportions, torso.parts[0], refined.parts[0]

    def test_refinement_adds_limb_resolution(self):
        _proportions, before, after = self._fixture()
        self.assertGreater(len(after.vertices), len(before.vertices))
        self.assertEqual(len(after.faces), len(before.faces))

    def test_refinement_preserves_bounds_uvs_and_manifold_surface(self):
        _proportions, before, after = self._fixture()
        for axis in range(3):
            self.assertAlmostEqual(min(v[axis] for v in after.vertices), min(v[axis] for v in before.vertices))
            self.assertAlmostEqual(max(v[axis] for v in after.vertices), max(v[axis] for v in before.vertices))
        self.assertEqual(len(after.uvs), len(after.faces))
        for face, face_uvs in zip(after.faces, after.uvs):
            self.assertEqual(len(face), len(face_uvs))
        self.assertTrue(is_closed_manifold(after))

    def test_refinement_is_deterministic_across_supported_heights(self):
        for height in (120, 180, 240):
            with self.subTest(height=height):
                proportions = generate_proportions(HumanoidSpec(height, 95, BodyType.AVERAGE))
                base = generate_deformable_mesh(proportions)
                torso = refine_human_torso_cross_sections(base, proportions)
                self.assertEqual(
                    refine_human_limb_cross_sections(torso, proportions),
                    refine_human_limb_cross_sections(torso, proportions),
                )

    def test_refinement_requires_expected_inputs(self):
        proportions = generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE))
        base = generate_deformable_mesh(proportions)
        with self.assertRaisesRegex(TypeError, "HumanoidProportions"):
            refine_human_limb_cross_sections(base, HumanoidSpec(180, 95, BodyType.AVERAGE))


if __name__ == "__main__":
    unittest.main()
