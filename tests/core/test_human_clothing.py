# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core.objects import get_provider
from object_core.providers.human_clothing import basic_shirt_mesh, basic_shirt_weights


class HumanClothingTests(unittest.TestCase):
    def setUp(self):
        provider = get_provider("human")
        self.values = {field.key: field.default for field in provider.parameters}
        self.skeleton = provider.skeleton(self.values)

    def test_basic_shirt_is_lightweight_open_garment(self):
        mesh = basic_shirt_mesh(self.skeleton)
        self.assertEqual(1, len(mesh.parts))
        self.assertEqual("Shirt", mesh.parts[0].name)
        self.assertEqual(8, len(mesh.parts[0].vertices))
        self.assertEqual(4, len(mesh.parts[0].faces))

    def test_basic_shirt_weights_cover_every_vertex_and_use_parent_rig(self):
        mesh = basic_shirt_mesh(self.skeleton)
        weights = basic_shirt_weights(mesh)
        self.assertEqual(len(mesh.parts[0].vertices), len(weights[0].vertices))
        names = {influence.bone_name for vertex in weights[0].vertices for influence in vertex}
        self.assertEqual({"torso", "neck"}, names)
        for vertex in weights[0].vertices:
            self.assertAlmostEqual(1.0, sum(item.weight for item in vertex))

    def test_invalid_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            basic_shirt_mesh(self.skeleton, ease_cm=-1)
        with self.assertRaises(ValueError):
            basic_shirt_mesh(self.skeleton, length_cm=0)


if __name__ == "__main__":
    unittest.main()
