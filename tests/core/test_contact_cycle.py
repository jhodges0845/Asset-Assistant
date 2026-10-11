# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from dataclasses import replace

from object_core.animation.contact import ContactCycle


class ContactCycleTests(unittest.TestCase):
    def setUp(self):
        self.cycle = ContactCycle(1.2, 30.0, .6, 5.0)

    def test_reference_root_travel_cancels_stance_motion(self):
        for duration in (.3, 1.2, 4):
            for stride in (0, 10, 90):
                cycle = replace(self.cycle, duration=duration, stride_cm=stride)
                positions = []
                for phase in (0, .1, .25, .59):
                    target = cycle.target(phase)
                    self.assertTrue(target.in_stance)
                    self.assertEqual(target.lift_cm, 0)
                    positions.append(target.forward_cm + cycle.reference_speed_cm_s * phase * duration)
                for position in positions:
                    self.assertAlmostEqual(position, positions[0])

    def test_lift_is_nonnegative_and_reaches_declared_apex(self):
        for duty in (.2, .6, .9):
            cycle = replace(self.cycle, duty_factor=duty)
            self.assertAlmostEqual(cycle.target((1 + duty) / 2).lift_cm, 5)
            for i in range(1001):
                self.assertGreaterEqual(cycle.target(i / 1000).lift_cm, 0)
                self.assertLessEqual(cycle.target(i / 1000).lift_cm, 5 + 1e-12)
            self.assertFalse(cycle.target(duty).in_stance)
            self.assertEqual(cycle.target(duty).lift_cm, 0)

    def test_position_and_velocity_are_continuous_at_contacts(self):
        eps = 1e-7
        for duty in (.2, .6, .9):
            cycle = replace(self.cycle, duty_factor=duty)
            for phase in (0, duty, 1):
                left, center, right = (cycle.target(phase + delta) for delta in (-eps, 0, eps))
                for field in ('forward_cm', 'lift_cm'):
                    a, b, c = (getattr(target, field) for target in (left, center, right))
                    self.assertAlmostEqual(a, b, delta=4e-6)
                    self.assertAlmostEqual(b, c, delta=4e-6)
                    expected = -cycle.stride_cm if field == 'forward_cm' else 0
                    self.assertAlmostEqual((b-a) / eps, expected, delta=.002)
                    self.assertAlmostEqual((c-b) / eps, expected, delta=.002)

    def test_phase_offsets_and_multiple_cycles(self):
        shifted = replace(self.cycle, touchdown_phase=.5)
        for phase in (0, .125, .25, .75):
            expected = self.cycle.target(phase)
            for turn in (-3, 0, 7):
                actual = shifted.target(phase + .5 + turn)
                self.assertEqual(actual.in_stance, expected.in_stance)
                self.assertAlmostEqual(actual.forward_cm, expected.forward_cm)
                self.assertAlmostEqual(actual.lift_cm, expected.lift_cm)
        self.assertEqual(self.cycle.target(0), self.cycle.target(1))

    def test_duration_only_changes_reference_speed(self):
        slow = replace(self.cycle, duration=2.4)
        self.assertEqual(slow.reference_speed_cm_s * 2, self.cycle.reference_speed_cm_s)
        self.assertEqual(slow.target(.8), self.cycle.target(.8))
        zero = replace(self.cycle, stride_cm=0, swing_height_cm=0)
        for phase in (0, .5, .8, 1):
            self.assertEqual(zero.target(phase).forward_cm, 0)
            self.assertEqual(zero.target(phase).lift_cm, 0)

    def test_invalid_inputs_fail_before_evaluation(self):
        for field in ('duration', 'stride_cm', 'duty_factor', 'swing_height_cm', 'touchdown_phase'):
            for value in (True, '1', None, float('nan'), float('inf')):
                with self.subTest(field=field, value=value), self.assertRaises((TypeError, ValueError)):
                    replace(self.cycle, **{field: value})
        for field, values in (('duration', (0, -1)), ('stride_cm', (-1,)),
                              ('swing_height_cm', (-1,)), ('duty_factor', (0, 1, -1)),
                              ('touchdown_phase', (-.1, 1))):
            for value in values:
                with self.assertRaises(ValueError):
                    replace(self.cycle, **{field: value})
        for phase in (True, None, '0', float('nan'), float('inf')):
            with self.assertRaises((TypeError, ValueError)):
                self.cycle.target(phase)
