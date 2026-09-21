# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression coverage for printing the completed deforming Human through Cura."""
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_asset
from blender_adapter.printing import print_geometry
from blender_adapter.targets import get_adapter
from blender_adapter.workflow import add_basic_rig
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, 'requires Blender; use scripts/test_blender.py')
class HumanCuraTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ('objects', 'meshes', 'armatures', 'collections', 'materials', 'images', 'actions')}
        self.scene = bpy.data.scenes.new('HumanCuraTest')
        bpy.context.window.scene = self.scene
        provider = get_provider('human')
        values = {field.key: field.default for field in provider.parameters}
        self.root = create_asset(provider.mesh(values), name='PrintableHuman', scene=self.scene)
        self.root['object_type'] = provider.key
        for key, value in values.items():
            self.root[key] = value

    def tearDown(self):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)

    def test_default_human_is_one_closed_print_solid(self):
        snapshot, components, _ = print_geometry([self.root] + list(self.root.children), bpy.context)
        self.assertEqual(components, 1)
        self.assertEqual(snapshot.invalid_meshes, (),
                         'default Human print geometry should be closed and non-self-intersecting')

    def test_rigged_human_can_export_current_pose_to_stl(self):
        add_basic_rig(self.root, bpy.context)
        adapter = get_adapter('CURA')
        issues = adapter.prepare(self.root, bpy.context)
        self.assertFalse(any(issue.status in ('WARN', 'ERROR') for issue in issues), issues)
        with TemporaryDirectory() as directory:
            result = adapter.export(self.root, bpy.context, Path(directory) / 'human.stl')
            self.assertTrue(result.success, result.issues)
            self.assertTrue(Path(result.filepath).is_file())


if __name__ == '__main__':
    unittest.main()
