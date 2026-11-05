# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_asset
from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_deformable_mesh


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderHumanUVTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def test_generated_human_gets_editable_uv_map(self):
        proportions = generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE))
        mesh = generate_deformable_mesh(proportions)
        root = create_asset(mesh, name="UVHuman")
        obj = next(child for child in root.children if child.type == "MESH")

        self.assertEqual(len(obj.data.uv_layers), 1)
        layer = obj.data.uv_layers[0]
        self.assertEqual(layer.name, "UVMap")
        self.assertEqual(len(layer.data), len(obj.data.loops))
        self.assertTrue(all(0.0 <= item.uv[0] <= 1.0 and 0.0 <= item.uv[1] <= 1.0
                            for item in layer.data))


    def test_current_human_has_no_collapsed_uv_triangles_after_float32_storage(self):
        from object_core.objects import get_provider
        from scripts.anatomy_baseline import SAMPLES
        from scripts.review_human_lod_atlas import atlas_report, source_atlas_columns
        provider = get_provider('human')
        for sample in ({}, SAMPLES['human']):
            with self.subTest(sample=sample):
                values = {p.key: p.default for p in provider.parameters}
                values.update(sample)
                root = create_asset(provider.mesh(values), name='CurrentHumanUV')
                body = next(obj for obj in root.children if obj.type == 'MESH')
                result = atlas_report(body.data, source_atlas_columns(body.data))
                self.assertEqual(result['zero_uv_area_triangles'], 0)
                self.assertEqual(result['cross_cell_triangles'], 0)
                self.assertEqual(result['outside_atlas_triangles'], 0)


if __name__ == "__main__":
    unittest.main()
