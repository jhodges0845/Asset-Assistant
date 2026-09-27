# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core.models import MaterialSpec, ObjectMesh, Skeleton
from object_core.objects import get_provider


class QuadrupedProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider("quadruped")
        self.defaults = {field.key: field.default for field in self.provider.parameters}

    def test_quadruped_provider_declares_deforming_rig_capabilities(self):
        self.assertEqual(self.provider.label, "Quadruped")
        self.assertTrue(self.provider.supports_rig)
        self.assertTrue(self.provider.supports_idle)
        self.assertTrue(self.provider.supports_locomotion)
        self.assertTrue(self.provider.supports_run)
        self.assertTrue(self.provider.uses_skin_weights)
        self.assertTrue(self.provider.supports_materials)

    def test_default_quadruped_generates_one_connected_deformable_surface(self):
        mesh = self.provider.mesh(self.defaults)
        self.assertIsInstance(mesh, ObjectMesh)
        self.assertEqual(mesh, self.provider.mesh(self.defaults))
        self.assertEqual(tuple(part.name for part in mesh.parts), ("quadruped",))
        self.assertEqual(mesh.vertex_count, 6274)
        self.assertEqual(mesh.face_count, 6272)
        part = mesh.parts[0]
        referenced = {index for face in part.faces for index in face}
        self.assertEqual(referenced, set(range(len(part.vertices))))
        self.assertEqual(len(part.uvs), len(part.faces))
        for face, face_uvs in zip(part.faces, part.uvs):
            self.assertEqual(len(face_uvs), len(face))
            self.assertTrue(all(0.0 <= coordinate <= 1.0
                                for uv in face_uvs for coordinate in uv))

    def test_dimensions_drive_independent_quadruped_axes(self):
        short = self.provider.mesh(dict(self.defaults, body_length_cm=40))
        long = self.provider.mesh(dict(self.defaults, body_length_cm=120))
        narrow = self.provider.mesh(dict(self.defaults, body_width_cm=10))
        wide = self.provider.mesh(dict(self.defaults, body_width_cm=50))
        low = self.provider.mesh(dict(self.defaults, shoulder_height_cm=20))
        tall = self.provider.mesh(dict(self.defaults, shoulder_height_cm=90))

        self.assertGreater(long.bounds_cm[1][1] - long.bounds_cm[0][1],
                           short.bounds_cm[1][1] - short.bounds_cm[0][1])
        self.assertGreater(wide.bounds_cm[1][0] - wide.bounds_cm[0][0],
                           narrow.bounds_cm[1][0] - narrow.bounds_cm[0][0])
        self.assertGreater(tall.bounds_cm[1][2], low.bounds_cm[1][2])

    def test_tail_length_changes_rear_extent(self):
        short_tail = self.provider.mesh(dict(self.defaults, tail_length_cm=5))
        long_tail = self.provider.mesh(dict(self.defaults, tail_length_cm=80))
        self.assertLess(long_tail.bounds_cm[0][1], short_tail.bounds_cm[0][1])

    def test_quadruped_skeleton_is_deterministic_and_parented(self):
        skeleton = self.provider.skeleton(self.defaults)
        self.assertIsInstance(skeleton, Skeleton)
        self.assertEqual(skeleton, self.provider.skeleton(self.defaults))
        names = [bone.name for bone in skeleton.bones]
        self.assertEqual(names[:4], ["root", "spine", "neck", "head"])
        for name in ("fore_upper.left", "fore_lower.left", "fore_upper.right", "fore_lower.right",
                     "hind_upper.left", "hind_lower.left", "hind_upper.right", "hind_lower.right",
                     "tail.1", "tail.2", "tail.3"):
            self.assertIn(name, names)
        by_name = {bone.name: bone for bone in skeleton.bones}
        self.assertEqual(by_name["fore_lower.left"].parent, "fore_upper.left")
        self.assertEqual(by_name["hind_upper.left"].parent, "spine")
        self.assertEqual(by_name["hind_lower.right"].parent, "hind_upper.right")
        self.assertEqual(by_name["tail.1"].parent, "spine")
        self.assertEqual(by_name["tail.3"].parent, "tail.2")

    def test_skin_weights_cover_connected_surface_and_stay_local(self):
        mesh = self.provider.mesh(self.defaults)
        skeleton = self.provider.skeleton(self.defaults)
        weights = self.provider.skin_weights(mesh, self.defaults)
        self.assertEqual(tuple(item.part_name for item in weights), ("quadruped",))
        rows = weights[0].vertices
        self.assertEqual(len(rows), len(mesh.parts[0].vertices))
        bone_names = {bone.name for bone in skeleton.bones}
        for vertex, influences in zip(mesh.parts[0].vertices, rows):
            self.assertAlmostEqual(sum(item.weight for item in influences), 1.0)
            self.assertTrue(all(item.bone_name in bone_names for item in influences))
            self.assertLessEqual(len(influences), 4)
            opposite = ".right" if vertex[0] <= 0 else ".left"
            self.assertFalse(any(item.bone_name.endswith(opposite) for item in influences))
        used = {item.bone_name for row in rows for item in row}
        self.assertTrue({"spine", "neck", "head", "tail.1", "tail.2", "tail.3"} <= used)
        self.assertTrue({"fore_upper.left", "fore_lower.right", "hind_upper.left", "hind_lower.right"} <= used)

    def test_deformation_junctions_share_weights_across_parent_child_bones(self):
        mesh = self.provider.mesh(self.defaults)
        rows = self.provider.skin_weights(mesh, self.defaults)[0].vertices
        influence_sets = [{item.bone_name for item in row} for row in rows]
        expected_blends = (
            {"spine", "fore_upper.left"},
            {"spine", "hind_upper.left"},
            {"spine", "neck"},
            {"spine", "tail.1"},
            {"tail.1", "tail.2"},
        )
        for pair in expected_blends:
            with self.subTest(pair=pair):
                self.assertTrue(any(pair <= names for names in influence_sets))

    def test_material_is_portable_textured_pbr_starting_point(self):
        materials = self.provider.materials(self.defaults)
        self.assertEqual(len(materials), 1)
        material = materials[0]
        self.assertIsInstance(material, MaterialSpec)
        self.assertEqual(material.name, "Quadruped Base Coat")
        self.assertEqual(material.part_names, ("quadruped",))
        self.assertEqual(material.metallic, 0.0)
        self.assertGreater(material.roughness, 0.7)
        self.assertIsNotNone(material.base_color_texture)
        self.assertEqual(material.base_color_texture.name, "Quadruped Coat Texture")
        self.assertEqual((material.base_color_texture.width, material.base_color_texture.height), (2, 2))
        self.assertEqual(len(material.base_color_texture.pixels), 16)

    def test_legacy_provider_key_resolves_to_quadruped(self):
        self.assertIs(get_provider("dog"), self.provider)

    def test_invalid_parameters_are_rejected(self):
        for field in self.provider.parameters:
            for value in (True, "bad", float("nan"), field.minimum - 1, field.maximum + 1):
                values = dict(self.defaults)
                values[field.key] = value
                with self.subTest(parameter=field.key, value=value):
                    with self.assertRaises((TypeError, ValueError)):
                        self.provider.mesh(values)
                    with self.assertRaises((TypeError, ValueError)):
                        self.provider.skeleton(values)


if __name__ == "__main__":
    unittest.main()
