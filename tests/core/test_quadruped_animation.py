# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core.objects import get_provider


class QuadrupedAnimationTests(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider("quadruped")

    def test_quadruped_declares_idle_locomotion_and_run_support(self):
        self.assertTrue(self.provider.supports_idle)
        self.assertTrue(self.provider.supports_locomotion)
        self.assertTrue(self.provider.supports_run)

    def test_idle_is_closed_and_targets_quadruped_upper_body_and_tail(self):
        clip = self.provider.idle(4.0, 1.0)
        self.assertEqual(clip.duration, 4.0)
        self.assertEqual(clip.translations[0].bone, 'root')
        self.assertTrue(all(offset == (0., 0., 0.) for _, offset in clip.translations[0].keys))
        names = {track.bone for track in clip.tracks}
        self.assertEqual(names, {"spine", "neck", "head", "tail.1", "tail.2", "tail.3"})
        for track in clip.tracks:
            self.assertAlmostEqual(track.keys[0][0], 0.0)
            self.assertAlmostEqual(track.keys[-1][0], clip.duration)
            self.assertAlmostEqual(track.keys[0][1], track.keys[-1][1])

    def test_walk_solves_all_limb_joints_and_closes_with_body_crouch(self):
        clip = self.provider.locomotion(1.2, 1.0)
        tracks = {track.bone: track for track in clip.tracks}
        for family in ('fore_upper', 'fore_lower', 'hind_upper', 'hind_lower', 'hind_pastern'):
            for side in ('left', 'right'):
                self.assertIn(family + '.' + side, tracks)
        for track in tracks.values():
            self.assertEqual(track.keys[0][1], track.keys[-1][1])
        self.assertEqual(clip.translations[0].bone, 'root')
        self.assertLess(clip.translations[0].keys[0][1][2], 0)
        for side in ('left', 'right'):
            rows = [tracks[name + '.' + side].keys for name in ('hind_upper', 'hind_lower', 'hind_pastern')]
            for sample in zip(*rows):
                self.assertAlmostEqual(sum(angle for _, angle in sample), 0)

    def test_animation_validation_matches_shared_provider_ranges(self):
        for method in (self.provider.idle, self.provider.locomotion, self.provider.run):
            for duration, strength in ((True, 1.0), (1.2, True), (float("nan"), 1.0), (1.2, 0.0)):
                with self.assertRaises((TypeError, ValueError)):
                    method(duration, strength)


if __name__ == "__main__":
    unittest.main()
