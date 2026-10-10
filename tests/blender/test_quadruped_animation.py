# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from object_core.objects import get_provider
from humanoid_blender.adapter import create_character
from humanoid_blender.animation import add_idle, add_locomotion, generated_action


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class QuadrupedAnimationBlenderTests(unittest.TestCase):
    def setUp(self):
        self.scene = bpy.data.scenes.new("QuadrupedAnimationTest")
        self.previous_scene = bpy.context.window.scene
        bpy.context.window.scene = self.scene
        self.objects_before = set(bpy.data.objects)
        self.meshes_before = set(bpy.data.meshes)
        self.armatures_before = set(bpy.data.armatures)
        self.collections_before = set(bpy.data.collections)
        self.actions_before = set(bpy.data.actions)

    def tearDown(self):
        bpy.context.window.scene = self.previous_scene
        for action in set(bpy.data.actions) - self.actions_before:
            bpy.data.actions.remove(action)
        for obj in set(bpy.data.objects) - self.objects_before:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in set(bpy.data.meshes) - self.meshes_before:
            bpy.data.meshes.remove(mesh)
        for collection in set(bpy.data.collections) - self.collections_before:
            bpy.data.collections.remove(collection)
        for data in set(bpy.data.armatures) - self.armatures_before:
            bpy.data.armatures.remove(data)
        bpy.data.scenes.remove(self.scene)

    def _quadruped(self):
        provider = get_provider("quadruped")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        skeleton = provider.skeleton(values)
        weights = provider.skin_weights(mesh, values)
        root = create_character(mesh, scene=self.scene, skeleton=skeleton, skin_weights=weights)
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root

    def test_idle_and_walk_actions_generate_and_drive_connected_quadruped_surface(self):
        root = self._quadruped()
        rig = next(obj for obj in root.children if obj.type == "ARMATURE")
        mesh = next(obj for obj in root.children if obj.type == "MESH")

        idle, _ = add_idle(root, self.scene, 4.0, 1.0)
        self.assertIs(idle, generated_action(root, "Idle"))
        self.assertIs(rig.animation_data.action, idle)

        walk, _ = add_locomotion(root, self.scene, 1.2, 1.0)
        self.assertIs(walk, generated_action(root, "Walk"))
        self.assertIs(rig.animation_data.action, walk)

        graph = bpy.context.evaluated_depsgraph_get()
        self.scene.frame_set(self.scene.frame_start)
        bpy.context.view_layer.update()
        start = [v.co.copy() for v in mesh.evaluated_get(graph).data.vertices]
        self.scene.frame_set(self.scene.frame_start + max(1, round(self.scene.render.fps * 0.3)))
        bpy.context.view_layer.update()
        later = [v.co.copy() for v in mesh.evaluated_get(graph).data.vertices]
        self.assertTrue(any((a - b).length > 1e-5 for a, b in zip(start, later)))

        self.assertIn("fore_upper.left", rig.pose.bones)
        self.assertIn("hind_upper.right", rig.pose.bones)
        self.assertIn("tail.3", rig.pose.bones)


    def test_contact_crouch_respects_units_and_idle_switch_clears_translation(self):
        from blender_adapter.animation import activate_generated_action, action_curves
        from blender_adapter.animation_names_ui import _activate_action
        self.scene.unit_settings.scale_length = .01
        root = self._quadruped()
        rig = next(obj for obj in root.children if obj.type == 'ARMATURE')
        add_idle(root, self.scene, 4., 1.)
        walk, _ = add_locomotion(root, self.scene, 1.2, 1.)
        self.scene.frame_set(self.scene.frame_start)
        bpy.context.view_layer.update()
        delta = rig.pose.bones['root'].matrix.translation - rig.data.bones['root'].head_local
        self.assertAlmostEqual(delta.z, -55 * .07, places=4)
        curves = action_curves(walk, rig.animation_data.action_slot)
        self.assertEqual(sum(c.data_path.endswith('.location') for c in curves), 15)
        # At a nonzero sway phase the torso moves, but each limb retains its
        # rest X position even with its articulated contact rotations.
        self.scene.frame_set(self.scene.frame_start + 3)
        bpy.context.view_layer.update()
        self.assertGreater(abs(rig.pose.bones['root'].matrix.translation.x), .01)
        for name in ('fore_upper.left', 'fore_upper.right', 'hind_upper.left', 'hind_upper.right'):
            self.assertAlmostEqual(rig.pose.bones[name].matrix.translation.x,
                                   rig.data.bones[name].head_local.x, places=5)
        _activate_action(root, generated_action(root, 'Idle'), self.scene)
        bpy.context.view_layer.update()
        for name in ('root', 'fore_upper.left', 'fore_upper.right', 'hind_upper.left', 'hind_upper.right'):
            self.assertLess(rig.pose.bones[name].location.length, 1e-7)
        self.scene.frame_set(self.scene.frame_start)
        activate_generated_action(root, 'Walk')
        bpy.context.view_layer.update()
        delta = rig.pose.bones['root'].matrix.translation - rig.data.bones['root'].head_local
        self.assertAlmostEqual(delta.z, -55 * .07, places=4)


    def test_older_rig_rejects_forepaw_clip_without_replacing_existing_idle(self):
        root = self._quadruped()
        rig = next(obj for obj in root.children if obj.type == 'ARMATURE')
        idle, _ = add_idle(root, self.scene, 4., 1.)
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for side in ('left', 'right'):
            rig.data.edit_bones.remove(rig.data.edit_bones['fore_pastern.' + side])
        bpy.ops.object.mode_set(mode='OBJECT')
        actions = set(bpy.data.actions)
        frame = self.scene.frame_current
        with self.assertRaisesRegex(ValueError, 'missing bones'):
            add_locomotion(root, self.scene, 1.2, 1.)
        self.assertEqual(actions, set(bpy.data.actions))
        self.assertIs(rig.animation_data.action, idle)
        self.assertEqual(self.scene.frame_current, frame)
        self.assertIsNone(generated_action(root, 'Walk'))


if __name__ == "__main__":
    unittest.main()
