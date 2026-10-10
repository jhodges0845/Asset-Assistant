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
        self.assertTrue(all(-16.8 <= offset[2] <= -14 for _, offset in clip.translations[0].keys))
        for track in clip.tracks:
            self.assertEqual(track.keys[0][1], track.keys[-1][1])
            if track.bone.startswith(('fore_', 'hind_')):
                self.assertLess(max(abs(a[1]-b[1]) for a,b in zip(track.keys, track.keys[1:])), .2)


    def test_body_response_is_bounded_looped_and_compensated_at_joint_keys(self):
        provider = get_provider('quadruped')
        for running, method in ((False, provider.locomotion), (True, provider.run)):
            clip = method(1.2, 1)
            keys = clip.translations[0].keys
            self.assertEqual(len(keys), 129)
            self.assertEqual(keys[0][1], keys[-1][1])
            heights = [offset[2] for _, offset in keys]
            self.assertGreater(max(heights)-min(heights), .3)
            for _, offset in keys:
                self.assertEqual(offset[:2], (0., 0.))
                self.assertGreaterEqual(offset[2], -55*(.084 if running else .076)-1e-10)
                self.assertLessEqual(offset[2], -55*.07+1e-10)
            for track in clip.tracks:
                if track.bone.startswith(('fore_', 'hind_')):
                    self.assertEqual([t for t,_ in keys], [t for t,_ in track.keys])
            if running:
                # The body is lower mid-stance than midway through flight.
                self.assertLess(heights[26], heights[58])

    def test_all_paw_pitch_returns_to_level_during_stance(self):
        provider = get_provider('quadruped')
        from object_core.providers.quadruped import _construction
        values = {p.key: p.default for p in provider.parameters}
        _, anatomy = _construction(provider.dimensions(values))
        for running, method in ((False, provider.locomotion), (True, provider.run)):
            clip = method(1.2, 1)
            tracks = {track.bone: track for track in clip.tracks}
            schedules = contact_schedule(1.2, 1, 55, running)
            checked = 0
            for chain in anatomy.chains:
                if chain.name not in schedules or len(chain.bones) != 3:
                    continue
                checked += 1
                pitches = [sum(tracks[name].keys[i][1] for name in chain.bones)
                           for i in range(129)]
                self.assertGreater(max(pitches), .11)
                for i, pitch in enumerate(pitches):
                    if schedules[chain.name].target(i / 128).in_stance:
                        self.assertAlmostEqual(pitch, 0., places=10)
                    self.assertGreaterEqual(pitch, -1e-10)
                    self.assertLessEqual(pitch, .12 + 1e-10)
            self.assertEqual(checked, 4)
