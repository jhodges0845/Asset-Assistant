# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh, is_closed_manifold
from object_core.geometry.facial_feature_topology import refine_human_facial_feature_loops
from object_core.geometry.facial_local_topology import refine_human_local_feature_topology
from object_core.geometry.facial_refinement import refine_human_facial_topology
from object_core.proportions.landmarks import generate_landmarks


class HumanLocalFeatureTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proportions = generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE))
        mesh = generate_deformable_mesh(cls.proportions)
        mesh = refine_human_facial_feature_loops(mesh, cls.proportions)
        cls.before_mesh = refine_human_facial_topology(mesh, cls.proportions)
        cls.after_mesh = refine_human_local_feature_topology(cls.before_mesh, cls.proportions)
        cls.before = cls.before_mesh.parts[0]
        cls.after = cls.after_mesh.parts[0]

    def test_adds_local_resolution_without_splitting_existing_edges(self):
        self.assertGreater(len(self.after.vertices), len(self.before.vertices))
        self.assertGreater(len(self.after.faces), len(self.before.faces))
        self.assertEqual(self.after.vertices[: len(self.before.vertices)], self.before.vertices)

    def test_preserves_closed_surface_uv_contract_and_bounds(self):
        self.assertTrue(is_closed_manifold(self.after))
        self.assertEqual(len(self.after.faces), len(self.after.uvs))
        for face, face_uvs in zip(self.after.faces, self.after.uvs):
            self.assertEqual(len(face), len(face_uvs))
        for axis in range(3):
            self.assertAlmostEqual(
                min(vertex[axis] for vertex in self.before.vertices),
                min(vertex[axis] for vertex in self.after.vertices),
            )
            self.assertAlmostEqual(
                max(vertex[axis] for vertex in self.before.vertices),
                max(vertex[axis] for vertex in self.after.vertices),
            )

    def test_new_support_is_concentrated_near_eye_mouth_and_nose(self):
        landmarks = generate_landmarks(self.proportions)
        chin_z = landmarks["chin"][2]
        height = landmarks["crown"][2] - chin_z
        new_vertices = self.after.vertices[len(self.before.vertices):]
        self.assertTrue(new_vertices)
        levels = [(vertex[2] - chin_z) / height for vertex in new_vertices]
        for target in (0.29, 0.44, 0.61):
            self.assertTrue(any(abs(level - target) < 0.10 for level in levels))

    def test_local_topology_is_left_right_symmetric(self):
        rounded = {(round(x, 6), round(y, 6), round(z, 6)) for x, y, z in self.after.vertices}
        for x, y, z in tuple(rounded):
            self.assertIn((round(-x, 6), y, z), rounded)

    def test_refinement_is_deterministic_across_supported_extremes(self):
        for height, body_type in ((120, BodyType.SLIM), (240, BodyType.OVERWEIGHT)):
            with self.subTest(height=height, body_type=body_type):
                proportions = generate_proportions(HumanoidSpec(height, 95, body_type))
                mesh = generate_deformable_mesh(proportions)
                mesh = refine_human_facial_feature_loops(mesh, proportions)
                mesh = refine_human_facial_topology(mesh, proportions)
                first = refine_human_local_feature_topology(mesh, proportions)
                second = refine_human_local_feature_topology(mesh, proportions)
                self.assertEqual(first, second)

    def test_requires_expected_inputs(self):
        with self.assertRaises(TypeError):
            refine_human_local_feature_topology(None, self.proportions)
        with self.assertRaises(TypeError):
            refine_human_local_feature_topology(self.before_mesh, None)


if __name__ == "__main__":
    unittest.main()
