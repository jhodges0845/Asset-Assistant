# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import (add_idle, add_locomotion, action_curves,
                                       activate_generated_action, generated_action)
from blender_adapter.validation import inspect_character
from blender_adapter.workflow import add_basic_rig
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class HumanLocomotionTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ('objects', 'meshes', 'armatures', 'collections', 'materials', 'images', 'actions')}
        self.scene = bpy.data.scenes.new('HumanLocomotionTest')
        bpy.context.window.scene = self.scene
        provider = get_provider('human')
        values = {field.key: field.default for field in provider.parameters}
        self.root = create_character(provider.mesh(values), name='WalkHuman', scene=self.scene)
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

    def test_walk_creates_editable_cyclic_action_and_moves_opposing_legs(self):
        rig = add_basic_rig(self.root, bpy.context)
        self.scene.render.fps = 30
        action, end = add_locomotion(self.root, self.scene, 1.2, 1.0)
        self.assertTrue(action.name.endswith('.Walk'))
        self.assertEqual(action.get('asset_assistant_clip'), 'Walk')
        self.assertGreater(end, self.scene.frame_start)
        curves = action_curves(action, getattr(rig.animation_data, 'action_slot', None))
        self.assertTrue(curves)
        self.assertTrue(all(any(mod.type == 'CYCLES' for mod in curve.modifiers) for curve in curves))
        self.scene.frame_set(1)
        left_start = rig.pose.bones['upper_leg.left'].matrix.copy()
        right_start = rig.pose.bones['upper_leg.right'].matrix.copy()
        self.scene.frame_set(19)
        self.assertNotEqual(left_start, rig.pose.bones['upper_leg.left'].matrix)
        self.assertNotEqual(right_start, rig.pose.bones['upper_leg.right'].matrix)
        self.assertTrue(inspect_character(self.root).has_animation)

    def test_idle_and_walk_coexist_and_switch_without_overwriting(self):
        rig = add_basic_rig(self.root, bpy.context)
        idle, _ = add_idle(self.root, self.scene)
        # Reproduce the UI workflow: the user can be parked mid-Idle when they
        # choose Walk. The generated pose must not be mistaken for artist work.
        self.scene.frame_set(49)
        self.assertTrue(any(bone.matrix_basis != bone.matrix_basis.__class__.Identity(4)
                            for bone in rig.pose.bones))
        walk, _ = add_locomotion(self.root, self.scene)
        self.assertIs(rig.animation_data.action, walk)
        self.assertIs(generated_action(self.root, 'Idle'), idle)
        self.assertIs(generated_action(self.root, 'Walk'), walk)
        idle_curves = tuple((curve.data_path, curve.array_index, len(curve.keyframe_points))
                            for curve in action_curves(idle, idle.slots[0] if hasattr(idle, 'slots') else None))
        activate_generated_action(self.root, 'Idle')
        self.assertIs(rig.animation_data.action, idle)
        self.assertEqual(idle_curves, tuple((curve.data_path, curve.array_index, len(curve.keyframe_points))
                                           for curve in action_curves(idle, getattr(rig.animation_data, 'action_slot', None))))
        activate_generated_action(self.root, 'Walk')
        self.assertIs(rig.animation_data.action, walk)

    def test_generated_clip_is_not_overwritten(self):
        rig = add_basic_rig(self.root, bpy.context)
        action, _ = add_locomotion(self.root, self.scene)
        before = set(bpy.data.actions)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            add_locomotion(self.root, self.scene)
        self.assertIs(rig.animation_data.action, action)
        self.assertEqual(before, set(bpy.data.actions))

    def test_artist_animation_is_preserved(self):
        rig = add_basic_rig(self.root, bpy.context)
        artist = bpy.data.actions.new('ArtistAction')
        rig.animation_data_create().action = artist
        before = set(bpy.data.actions)
        with self.assertRaisesRegex(ValueError, 'Existing animation'):
            add_locomotion(self.root, self.scene)
        self.assertIs(rig.animation_data.action, artist)
        self.assertEqual(before, set(bpy.data.actions))


if __name__ == '__main__':
    unittest.main()
