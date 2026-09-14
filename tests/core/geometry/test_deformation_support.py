# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh
from object_core.proportions.landmarks import generate_landmarks


class HumanDeformationSupportGeometryTests(unittest.TestCase):
    def _fixture(self):
        proportions = generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE))
        mesh = generate_deformable_mesh(proportions)
        points = generate_landmarks(proportions)
        return proportions, mesh.parts[0], points

    @staticmethod
    def _vertices_at_level(part, z):
        return [vertex for vertex in part.vertices if abs(vertex[2] - z) < 1e-6]

    def test_neck_has_multiple_intermediate_support_levels(self):
        proportions, part, points = self._fixture()
        shoulder_z = points["shoulder_center"][2]
        chin_z = points["chin"][2]
        half_width = proportions.neck_width_cm * 0.7
        levels = {
            round(vertex[2], 6)
            for vertex in part.vertices
            if shoulder_z < vertex[2] < chin_z and abs(vertex[0]) <= half_width
        }
        self.assertGreaterEqual(len(levels), 4)

    def test_each_shoulder_has_local_support_ring(self):
        proportions, part, points = self._fixture()
        minimum_radius = proportions.upper_arm_thickness_cm * 0.35
        maximum_radius = proportions.upper_arm_thickness_cm * 0.75
        for side in ("left", "right"):
            shoulder = points["shoulder." + side]
            nearby = []
            for vertex in part.vertices:
                distance = sum((vertex[i] - shoulder[i]) ** 2 for i in range(3)) ** 0.5
                if minimum_radius <= distance <= maximum_radius:
                    nearby.append(vertex)
            self.assertGreaterEqual(len(nearby), 8, side + " shoulder lacks a local support ring")

    def test_torso_has_pelvis_support_level_above_hip_opening(self):
        proportions, part, points = self._fixture()
        hip_z = points["hip_center"][2]
        support_z = hip_z + proportions.torso_length_cm * 0.10
        support = self._vertices_at_level(part, support_z)
        self.assertGreaterEqual(len(support), 8)

    def test_torso_has_shoulder_support_level_below_arm_opening(self):
        proportions, part, points = self._fixture()
        shoulder_z = points["shoulder_center"][2]
        support_z = shoulder_z - proportions.torso_length_cm * 0.08
        support = self._vertices_at_level(part, support_z)
        self.assertGreaterEqual(len(support), 8)

    def test_support_levels_survive_supported_height_extremes(self):
        for height in (120, 240):
            with self.subTest(height=height):
                proportions = generate_proportions(
                    HumanoidSpec(height, 95, BodyType.AVERAGE)
                )
                part = generate_deformable_mesh(proportions).parts[0]
                points = generate_landmarks(proportions)
                pelvis_z = points["hip_center"][2] + proportions.torso_length_cm * 0.10
                shoulder_z = points["shoulder_center"][2] - proportions.torso_length_cm * 0.08
                self.assertGreaterEqual(len(self._vertices_at_level(part, pelvis_z)), 8)
                self.assertGreaterEqual(len(self._vertices_at_level(part, shoulder_z)), 8)


if __name__ == "__main__":
    unittest.main()
