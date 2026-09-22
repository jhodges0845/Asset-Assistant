# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_asset
from blender_adapter.materials import material_issues, prepare_materials
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class HumanGeneratedMaterialTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def _human(self):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        root = create_asset(provider.mesh(values), name="MaterialHuman")
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root, provider

    def test_prepare_uses_portable_human_surface_and_texture(self):
        root, provider = self._human()
        created = prepare_materials(root)
        mesh = next(obj for obj in root.children if obj.type == "MESH")
        expected = provider.materials({field.key: field.default for field in provider.parameters})[0]
        self.assertIsNotNone(created)
        self.assertEqual(len(mesh.material_slots), 1)
        material = mesh.material_slots[0].material
        self.assertEqual(material.name, expected.name)
        shader = material.node_tree.nodes.get("Principled BSDF")
        self.assertEqual(tuple(round(v, 6) for v in shader.inputs["Base Color"].default_value),
                         tuple(round(v, 6) for v in expected.base_color))
        self.assertAlmostEqual(shader.inputs["Metallic"].default_value, expected.metallic)
        self.assertAlmostEqual(shader.inputs["Roughness"].default_value, expected.roughness)
        self.assertTrue(shader.inputs["Base Color"].is_linked)
        texture_node = shader.inputs["Base Color"].links[0].from_node
        self.assertEqual(texture_node.type, "TEX_IMAGE")
        self.assertIsNotNone(texture_node.image)
        self.assertTrue(texture_node.image.packed_file or getattr(texture_node.image, "packed_files", ()))
        self.assertEqual(tuple(texture_node.image.size),
                         (expected.base_color_texture.width, expected.base_color_texture.height))
        actual_pixels = tuple(texture_node.image.pixels[:])
        expected_pixels = expected.base_color_texture.pixels
        self.assertEqual(len(actual_pixels), len(expected_pixels))
        for actual, expected_value in zip(actual_pixels, expected_pixels):
            self.assertAlmostEqual(actual, expected_value, delta=(1.0 / 255.0) + 1e-6)
        self.assertTrue(mesh.data.uv_layers.get("UVMap"))
        self.assertFalse(material_issues((mesh,)))

    def test_prepare_preserves_existing_artist_material(self):
        root, _provider = self._human()
        mesh = next(obj for obj in root.children if obj.type == "MESH")
        artist = bpy.data.materials.new("Artist Material")
        mesh.data.materials.append(artist)
        for face in mesh.data.polygons:
            face.material_index = 0
        self.assertIsNone(prepare_materials(root))
        self.assertIs(mesh.material_slots[0].material, artist)


if __name__ == "__main__":
    unittest.main()
