# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core.animation import generate_run
from object_core.animation.walk import generate_walk
from object_core.objects import get_provider
from object_core.providers.quadruped_animation import generate_quadruped_run


class RunAnimationTests(unittest.TestCase):
    def test_human_run_is_closed_and_faster_than_default_walk(self):
        clip = generate_run()
        self.assertAlmostEqual(clip.duration, 0.72)
        self.assertTrue(clip.tracks)
        names = {track.bone for track in clip.tracks}
        self.assertIn('upper_leg.left', names)
        self.assertIn('upper_leg.right', names)
        self.assertIn('upper_arm.left', names)
        self.assertIn('upper_arm.right', names)
        for track in clip.tracks:
            self.assertEqual(track.keys[0][1], track.keys[-1][1])

    def test_human_run_has_deeper_joint_flexion_than_walk(self):
        run = {track.bone: track for track in generate_run().tracks}
        walk = {track.bone: track for track in generate_walk().tracks}
        for bone in ('lower_leg.left', 'lower_leg.right'):
            self.assertGreater(max(abs(angle) for _, angle in run[bone].keys),
                               max(abs(angle) for _, angle in walk[bone].keys))
        for bone in ('forearm.left', 'forearm.right'):
            self.assertIn(bone, run)
            self.assertGreater(min(abs(angle) for _, angle in run[bone].keys), 0.5)

    def test_human_run_uses_anatomically_correct_flexion_directions(self):
        run = {track.bone: track for track in generate_run().tracks}
        for bone in ('lower_leg.left', 'lower_leg.right'):
            angles = [angle for _, angle in run[bone].keys]
            self.assertTrue(all(angle < 0 for angle in angles),
                            bone + ' must flex backward at the knee')
        for bone in ('forearm.left', 'forearm.right'):
            angles = [angle for _, angle in run[bone].keys]
            self.assertTrue(all(angle > 0 for angle in angles),
                            bone + ' must flex forward toward the torso')

    def test_human_run_uses_phase_shift_not_mirrored_knee_bending(self):
        run = {track.bone: track for track in generate_run().tracks}
        left = [angle for _, angle in run['lower_leg.left'].keys]
        right = [angle for _, angle in run['lower_leg.right'].keys]
        self.assertNotEqual(left, right)
        self.assertGreater(abs(left[1]), abs(right[0]))
        self.assertGreater(abs(right[1]), abs(left[0]))

    def test_human_run_keeps_elbows_bent_and_phase_shifted(self):
        run = {track.bone: track for track in generate_run().tracks}
        left = [angle for _, angle in run['forearm.left'].keys]
        right = [angle for _, angle in run['forearm.right'].keys]
        self.assertTrue(all(angle > 0.5 for angle in left))
        self.assertTrue(all(angle > 0.5 for angle in right))
        self.assertNotEqual(left, right)

    def test_quadruped_run_is_closed_and_uses_all_four_limbs(self):
        clip = generate_quadruped_run()
        self.assertAlmostEqual(clip.duration, 0.64)
        names = {track.bone for track in clip.tracks}
        for bone in ('fore_upper.left', 'fore_upper.right', 'hind_upper.left', 'hind_upper.right'):
            self.assertIn(bone, names)
        for track in clip.tracks:
            self.assertAlmostEqual(track.keys[0][1], track.keys[-1][1])

    def test_run_tracks_exist_on_provider_skeletons(self):
        for provider_key, duration in (('human', 0.72), ('quadruped', 0.64)):
            provider = get_provider(provider_key)
            values = {field.key: field.default for field in provider.parameters}
            skeleton_names = {bone.name for bone in provider.skeleton(values).bones}
            run_names = {track.bone for track in provider.run(duration, 1.0).tracks}
            self.assertTrue(run_names.issubset(skeleton_names),
                            provider_key + ' run references bones missing from its skeleton: ' +
                            ', '.join(sorted(run_names - skeleton_names)))

    def test_human_and_quadruped_providers_advertise_run(self):
        human = get_provider('human')
        quadruped = get_provider('quadruped')
        self.assertTrue(human.supports_run)
        self.assertTrue(quadruped.supports_run)
        self.assertEqual(human.run(0.72, 1.0).duration, 0.72)
        self.assertEqual(quadruped.run(0.64, 1.0).duration, 0.64)

    def test_run_validation_rejects_bad_values(self):
        with self.assertRaises(ValueError):
            generate_run(0.2, 1.0)
        with self.assertRaises(ValueError):
            generate_quadruped_run(0.2, 1.0)
        with self.assertRaises(TypeError):
            generate_run(True, 1.0)


if __name__ == '__main__':
    unittest.main()
