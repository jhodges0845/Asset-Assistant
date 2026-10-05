# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from object_core.providers.quadruped_gait import contact_schedule
from object_core.objects import get_provider


class CanineContactGaitTests(unittest.TestCase):
    def test_walk_has_four_distinct_footfalls_and_continuous_support(self):
        schedule = contact_schedule(1.2, 1, 55)
        self.assertEqual({s.touchdown_phase for s in schedule.values()}, {0, .25, .5, .75})
        for i in range(128):
            self.assertGreaterEqual(sum(s.target(i/128).in_stance for s in schedule.values()), 2)

    def test_running_trot_has_diagonal_support_and_flight(self):
        schedule = contact_schedule(.64, 1, 55, True)
        counts = set()
        for i in range(128):
            states = {name: s.target(i/128).in_stance for name, s in schedule.items()}
            self.assertEqual(states['leg.front.left'], states['leg.hind.right'])
            self.assertEqual(states['leg.front.right'], states['leg.hind.left'])
            counts.add(sum(states.values()))
        self.assertEqual(counts, {0, 2})

    def test_sampling_is_looped_without_joint_branch_jumps(self):
        provider = get_provider('quadruped')
        for method in (provider.locomotion, provider.run):
            clip = method(1.2, 1)
            self.assertEqual(clip, method(1.2, 1))
            for track in clip.tracks:
                self.assertEqual(track.keys[0][1], track.keys[-1][1])
                self.assertEqual(track.keys[-1][0], clip.duration)
                self.assertLess(max(abs(a[1]-b[1]) for a,b in zip(track.keys, track.keys[1:])), .12)

    def test_reference_travel_scales_with_height_and_strength(self):
        base = contact_schedule(1, 1, 40)
        changed = contact_schedule(2, 2, 60)
        for name in base:
            self.assertAlmostEqual(changed[name].stride_cm, base[name].stride_cm * 3)
            self.assertAlmostEqual(changed[name].reference_speed_cm_s, base[name].reference_speed_cm_s * 1.5)

    def test_tall_short_body_supports_maximum_run_strength(self):
        provider = get_provider('quadruped')
        values = {p.key: p.default for p in provider.parameters}
        values.update(body_length_cm=25, shoulder_height_cm=100, body_width_cm=8)
        clip = provider.run(.64, 2, values=values)
        self.assertAlmostEqual(clip.translations[0].keys[0][1][2], -14)
        for track in clip.tracks:
            self.assertEqual(track.keys[0][1], track.keys[-1][1])
            if track.bone.startswith(('fore_', 'hind_')):
                self.assertLess(max(abs(a[1]-b[1]) for a,b in zip(track.keys, track.keys[1:])), .2)
