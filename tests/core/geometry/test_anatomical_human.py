# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_anatomical_human_mesh, is_closed_manifold
from object_core.proportions.landmarks import generate_landmarks


class AnatomicalHumanTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proportions = generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE))
        cls.mesh = generate_anatomical_human_mesh(cls.proportions)
        cls.part = cls.mesh.parts[0]
        cls.landmarks = generate_landmarks(cls.proportions)

    def test_generates_one_closed_symmetric_surface_with_uvs(self):
        self.assertEqual(len(self.mesh.parts), 1)
        self.assertTrue(is_closed_manifold(self.part))
        self.assertEqual(len(self.part.faces), len(self.part.uvs))
        for face, face_uvs in zip(self.part.faces, self.part.uvs):
            self.assertEqual(len(face), len(face_uvs))

        rounded = {(round(x, 6), round(y, 6), round(z, 6)) for x, y, z in self.part.vertices}
        for x, y, z in tuple(rounded):
            self.assertIn((round(-x, 6), y, z), rounded)

    def test_torso_sections_are_constructed_with_sixteen_point_loops(self):
        hip_z = self.landmarks["hip_center"][2]
        waist_z = hip_z + self.proportions.torso_length_cm * 0.35
        ring = [
            vertex for vertex in self.part.vertices
            if abs(vertex[2] - waist_z) <= 1e-7
        ]
        self.assertEqual(len(ring), 16)
        self.assertEqual(len({round(vertex[0], 6) for vertex in ring}), 9)

    def test_neck_and_head_keep_legacy_eight_point_layout(self):
        shoulder_z = self.landmarks["shoulder_center"][2]
        chin_z = self.landmarks["chin"][2]
        neck_z = shoulder_z + (chin_z - shoulder_z) * 0.18
        ring = [
            vertex for vertex in self.part.vertices
            if abs(vertex[2] - neck_z) <= 1e-7
        ]
        self.assertEqual(len(ring), 8)

    def test_standing_height_and_ground_are_preserved(self):
        zs = [vertex[2] for vertex in self.part.vertices]
        self.assertAlmostEqual(min(zs), 0.0)
        self.assertAlmostEqual(max(zs), self.proportions.standing_height_cm)

    def test_constructor_is_deterministic_across_supported_extremes(self):
        for height, body_type in ((120, BodyType.SLIM), (240, BodyType.OVERWEIGHT)):
            with self.subTest(height=height, body_type=body_type):
                proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
                self.assertEqual(
                    generate_anatomical_human_mesh(proportions),
                    generate_anatomical_human_mesh(proportions),
                )

    def test_requires_proportions(self):
        with self.assertRaises(TypeError):
            generate_anatomical_human_mesh(None)


if __name__ == "__main__":
    unittest.main()
