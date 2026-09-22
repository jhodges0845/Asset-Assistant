# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression coverage for Cura print-scale presets."""

from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None


@unittest.skipIf(bpy is None, 'requires Blender; use scripts/test_blender.py')
class CuraScaleTests(unittest.TestCase):
    def setUp(self):
        import blender_adapter
        self.addon = blender_adapter
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ('objects', 'meshes', 'armatures', 'collections', 'materials', 'images', 'actions')}
        self.scene = bpy.data.scenes.new('CuraScaleTest')
        bpy.context.window.scene = self.scene
        self.addon.register()

    def tearDown(self):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        self.addon.unregister()
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)

    @staticmethod
    def _stl_height(path):
        data = path.read_bytes()
        count, = struct.unpack_from('<I', data, 80)
        z_values = []
        for index in range(count):
            values = struct.unpack_from('<12fH', data, 84 + index * 50)
            z_values.extend((values[5], values[8], values[11]))
        return max(z_values) - min(z_values)

    def test_one_to_ten_exports_180_cm_human_at_about_180_mm(self):
        settings = self.scene.humanoid_settings
        settings.object_type = 'human'
        self.assertEqual(bpy.ops.humanoid.generate_blockout(), {'FINISHED'})
        root = settings.target

        source_z = [(obj.matrix_world @ vertex.co).z
                    for obj in root.children if obj.type == 'MESH'
                    for vertex in obj.data.vertices]
        self.assertAlmostEqual(max(source_z) - min(source_z), 1.8, places=4)

        settings.output_target = 'CURA'
        settings.cura_print_scale = '10'
        self.assertEqual(bpy.ops.humanoid.validate_character(), {'FINISHED'})
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())

        with TemporaryDirectory() as directory:
            path = Path(directory) / 'human-1-to-10.stl'
            self.assertEqual(bpy.ops.humanoid.export_asset(filepath=str(path)), {'FINISHED'})
            self.assertAlmostEqual(self._stl_height(path), 180.0, delta=3.0)

        source_z_after = [(obj.matrix_world @ vertex.co).z
                          for obj in root.children if obj.type == 'MESH'
                          for vertex in obj.data.vertices]
        self.assertAlmostEqual(max(source_z_after) - min(source_z_after), 1.8, places=4)


if __name__ == '__main__':
    unittest.main()
