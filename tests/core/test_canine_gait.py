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
            self.assertEqual(len(clip.translations), 5)
            for track in clip.translations[1:]:
                self.assertEqual(track.keys, tuple((t, (-v[0], 0., 0.)) for t, v in keys))
            if not running:
                self.assertGreater(max(v[0] for _, v in keys), .05)
                self.assertLess(min(v[0] for _, v in keys), -.05)
            heights = [offset[2] for _, offset in keys]
            self.assertGreater(max(heights)-min(heights), .3)
            for _, offset in keys:
                self.assertEqual(offset[1], 0.)
                self.assertLessEqual(abs(offset[0]), .24 + 1e-10)
                if running:
                    self.assertEqual(offset[0], 0.)
                self.assertGreaterEqual(offset[2], -55*(.084 if running else .076)-1e-10)
                self.assertLessEqual(offset[2], -55*.07+1e-10)
            for track in clip.tracks:
                if track.bone.startswith(('fore_', 'hind_')):
                    self.assertEqual([t for t,_ in keys], [t for t,_ in track.keys])
            if running:
                # The body is lower mid-stance than midway through flight.
                self.assertLess(heights[26], heights[58])

    def test_lateral_support_is_symmetric_scaled_and_idle_resets_offsets(self):
        from object_core.providers.quadruped_gait import _body_sway
        schedules = contact_schedule(1.2, 1, 55)
        for i in range(128):
            phase = i / 128
            sway = _body_sway(schedules, 24, 55, 1, phase)
            self.assertAlmostEqual(sway, -_body_sway(schedules, 24, 55, 1, phase + .5))
            self.assertAlmostEqual(2 * sway, _body_sway(schedules, 24, 55, 2, phase))
            self.assertLessEqual(abs(_body_sway(schedules, 55, 15, 2, phase)), .3 + 1e-10)
        idle = get_provider('quadruped').idle(4., 1.)
        self.assertEqual(len(idle.translations), 5)
        self.assertTrue(all(offset == (0., 0., 0.) for track in idle.translations
                            for _, offset in track.keys))

    def test_all_paws_roll_only_late_in_stance_and_curl_in_swing(self):
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
                self.assertLess(min(pitches), -.055)
                for i, pitch in enumerate(pitches):
                    schedule = schedules[chain.name]
                    local = (i / 128 - schedule.touchdown_phase) % 1.
                    if local <= .75 * schedule.duty_factor:
                        self.assertAlmostEqual(pitch, 0., places=10)
                    self.assertGreaterEqual(pitch, -.06 - 1e-10)
                    self.assertLessEqual(pitch, .12 + 1e-10)
            self.assertEqual(checked, 4)

    def test_toeoff_pitch_is_periodic_and_smooth_at_contact_boundaries(self):
        from object_core.providers.quadruped_gait import _paw_pitch
        for running in (False, True):
            schedule = contact_schedule(1, 1, 55, running)['leg.front.left']
            for local in (0., .75*schedule.duty_factor, schedule.duty_factor,
                          schedule.duty_factor + .3*(1-schedule.duty_factor), 1.):
                phase = schedule.touchdown_phase + local
                eps = 1e-6
                center = _paw_pitch(schedule, phase, 1.)
                self.assertAlmostEqual(center, _paw_pitch(schedule, phase+1, 1.), places=10)
                left = (center-_paw_pitch(schedule, phase-eps, 1.))/eps
                right = (_paw_pitch(schedule, phase+eps, 1.)-center)/eps
                self.assertAlmostEqual(left, right, delta=.001)

    def test_roll_pivots_are_selected_from_grounded_sole_points(self):
        from object_core.providers.quadruped import _construction
        from object_core.providers.quadruped_gait import _LimbSurface
        provider = get_provider('quadruped')
        defaults = {p.key: p.default for p in provider.parameters}
        for values in (defaults, dict(defaults, body_length_cm=95, shoulder_height_cm=40,
                                     body_width_cm=28, head_length_cm=30, tail_length_cm=50),
                       dict(defaults, body_length_cm=25, shoulder_height_cm=15, body_width_cm=55,
                            head_length_cm=8, tail_length_cm=5)):
            mesh, anatomy = _construction(provider.dimensions(values))
            weights = provider.skin_weights(mesh, values)[0]
            bones = {b.name: b for b in provider.skeleton(values).bones}
            regions = {r.name: r for r in anatomy.regions}
            checked = 0
            for chain in anatomy.chains:
                if not chain.name.startswith('leg.'):
                    continue
                surface = _LimbSurface(mesh, weights, regions[chain.name],
                                       tuple(bones[n] for n in chain.bones), 0.)
                self.assertGreaterEqual(surface.toe_z, 0.)
                self.assertLessEqual(surface.toe_z, .02)
                self.assertGreater(surface.toe_y, surface.neutral_y)
                checked += 1
            self.assertEqual(checked, 4)
