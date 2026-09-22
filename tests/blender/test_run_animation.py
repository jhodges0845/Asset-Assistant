# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_run, generated_action
from blender_adapter.workflow import add_basic_rig
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, 'requires Blender; use scripts/test_blender.py')
class RunAnimationBlenderTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ('objects', 'meshes', 'armatures', 'collections', 'materials', 'images', 'actions')}
        self.scene = bpy.data.scenes.new('RunAnimationTest')
        bpy.context.window.scene = self.scene

    def tearDown(self):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)

    def _make(self, provider_key, name):
        provider = get_provider(provider_key)
        values = {field.key: field.default for field in provider.parameters}
        root = create_character(provider.mesh(values), name=name, scene=self.scene)
        root['object_type'] = provider.key
        for key, value in values.items():
            root[key] = value
        add_basic_rig(root, bpy.context)
        return root

    def test_human_run_creates_named_generated_action(self):
        root = self._make('human', 'RunHuman')
        action, end = add_run(root, self.scene)
        self.assertEqual(action.get('asset_assistant_clip'), 'Run')
        self.assertEqual(action.get('asset_assistant_export_name'), 'Run')
        self.assertIs(generated_action(root, 'Run'), action)
        self.assertGreater(end, self.scene.frame_start)

    def test_quadruped_run_creates_named_generated_action(self):
        root = self._make('quadruped', 'RunQuadruped')
        action, end = add_run(root, self.scene, 0.64, 1.0)
        self.assertEqual(action.get('asset_assistant_clip'), 'Run')
        self.assertEqual(action.get('asset_assistant_export_name'), 'Run')
        self.assertIs(generated_action(root, 'Run'), action)
        self.assertGreater(end, self.scene.frame_start)


if __name__ == '__main__':
    unittest.main()
