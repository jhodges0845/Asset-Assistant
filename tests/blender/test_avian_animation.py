# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.animation import generated_action


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class AvianAnimationBlenderTests(unittest.TestCase):
    def setUp(self):
        import blender_adapter as addon
        self.addon = addon
        self.previous_scene = bpy.context.window.scene
        self.scene = bpy.data.scenes.new("AvianAnimationTest")
        bpy.context.window.scene = self.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ("objects", "meshes", "armatures", "collections", "actions")}
        addon.register()

        settings = self.scene.humanoid_settings
        settings.object_type = "avian"
        self.assertEqual(bpy.ops.humanoid.generate_blockout(), {"FINISHED"})
        self.root = settings.target
        self.assertEqual(bpy.ops.humanoid.add_basic_rig(), {"FINISHED"})
        self.settings = settings

    def tearDown(self):
        self.addon.unregister()
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)

    def test_idle_walk_and_flight_generate_as_separate_editable_actions(self):
        self.settings.animation_clip = "IDLE"
        self.assertTrue(bpy.ops.humanoid.select_animation_clip.poll())
        self.assertEqual(bpy.ops.humanoid.select_animation_clip(), {"FINISHED"})
        idle = generated_action(self.root, "Idle")
        self.assertIsNotNone(idle)

        self.settings.animation_clip = "WALK"
        self.settings.walk_duration = 1.2
        self.settings.walk_strength = 1.0
        self.assertTrue(bpy.ops.humanoid.select_animation_clip.poll())
        self.assertEqual(bpy.ops.humanoid.select_animation_clip(), {"FINISHED"})
        walk = generated_action(self.root, "Walk")
        self.assertIsNotNone(walk)
        self.assertIsNone(generated_action(self.root, "Flight"))

        self.settings.animation_clip = "FLIGHT"
        self.settings.walk_duration = 0.9
        self.settings.walk_strength = 1.0
        self.assertTrue(bpy.ops.humanoid.select_animation_clip.poll())
        self.assertEqual(bpy.ops.humanoid.select_animation_clip(), {"FINISHED"})
        flight = generated_action(self.root, "Flight")
        self.assertIsNotNone(flight)
        self.assertIsNot(idle, walk)
        self.assertIsNot(walk, flight)
        self.assertEqual(walk.get("asset_assistant_export_name"), "Walk")
        self.assertEqual(flight.get("asset_assistant_export_name"), "Flight")

        rig = next(obj for obj in self.root.children if obj.type == "ARMATURE")
        self.assertIs(rig.animation_data.action, flight)
        self.assertGreater(flight.frame_range[1], flight.frame_range[0])
        # Reuse already-created actions: no generator reset may mask stale crouch.
        for action in (walk, idle, walk, flight, idle):
            rig.animation_data.action = action
            self.scene.frame_set(3)
            bpy.context.view_layer.update()
            from mathutils import Euler
            from object_core.providers.avian_posture import COMPACT_FOLD_ROTATIONS
            expected = {}
            for name, axis, angle in COMPACT_FOLD_ROTATIONS:
                expected.setdefault(name, [0.,0.,0.])['xyz'.index(axis)] = angle
            for name, angles in expected.items():
                target = Euler(angles, 'XYZ').to_quaternion()
                actual = rig.pose.bones[name].rotation_quaternion
                difference = 1-abs(target.dot(actual))
                if action in (walk, idle):
                    self.assertLess(abs(difference),1e-6)
                else:
                    self.assertGreater(difference,.001)
            offset = rig.pose.bones['root'].location.length
            if action == walk:
                self.assertGreater(offset, .001)
            else:
                self.assertLess(offset, 1e-7)


    def test_run_remains_unavailable_to_avian(self):
        self.settings.animation_clip = "RUN"
        self.assertFalse(bpy.ops.humanoid.select_animation_clip.poll())

    def test_flight_option_is_not_available_to_human_provider(self):
        self.settings.animation_clip = "FLIGHT"
        self.assertTrue(bpy.ops.humanoid.select_animation_clip.poll())

        human_scene = bpy.data.scenes.new("HumanFlightCapabilityTest")
        try:
            bpy.context.window.scene = human_scene
            settings = human_scene.humanoid_settings
            settings.object_type = "human"
            self.assertEqual(bpy.ops.humanoid.generate_blockout(), {"FINISHED"})
            self.assertEqual(bpy.ops.humanoid.add_basic_rig(), {"FINISHED"})
            settings.animation_clip = "FLIGHT"
            self.assertFalse(bpy.ops.humanoid.select_animation_clip.poll())
        finally:
            bpy.context.window.scene = self.scene
            bpy.data.scenes.remove(human_scene)


if __name__ == "__main__":
    unittest.main()
