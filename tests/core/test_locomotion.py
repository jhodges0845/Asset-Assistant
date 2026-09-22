# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from types import SimpleNamespace

from object_core.animation import generate_walk
from object_core.objects import get_provider, validate_provider


class LocomotionTests(unittest.TestCase):
    def test_walk_is_closed_deterministic_and_moves_opposing_limbs(self):
        clip = generate_walk(1.2, 1.0)
        stronger = generate_walk(1.2, 2.0)
        self.assertEqual(clip, generate_walk(1.2, 1.0))
        self.assertEqual(clip.duration, 1.2)
        by_bone = {track.bone: track for track in clip.tracks}
        self.assertIn('upper_leg.left', by_bone)
        self.assertIn('upper_leg.right', by_bone)
        self.assertIn('upper_arm.left', by_bone)
        self.assertAlmostEqual(by_bone['upper_leg.left'].keys[0][1],
                               by_bone['upper_leg.left'].keys[-1][1])
        self.assertAlmostEqual(by_bone['upper_leg.left'].keys[0][1], -by_bone['upper_leg.right'].keys[0][1])
        for track, doubled in zip(clip.tracks, stronger.tracks):
            self.assertEqual(len(track.keys), 5)
            self.assertTrue(all(a[0] < b[0] for a, b in zip(track.keys, track.keys[1:])))
            self.assertAlmostEqual(doubled.keys[0][1], 2 * track.keys[0][1])

    def test_walk_rejects_invalid_settings(self):
        for value in (True, '1.2', None, float('nan'), 0.1, 5):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                generate_walk(duration=value)
        for value in (False, 0, 3, float('nan')):
            with self.assertRaises((TypeError, ValueError)):
                generate_walk(strength=value)

    def test_human_provider_exposes_idle_and_locomotion(self):
        provider = get_provider('human')
        self.assertTrue(provider.supports_idle)
        self.assertTrue(provider.supports_locomotion)
        self.assertEqual(provider.idle(4, 1), provider.idle(4, 1))
        self.assertEqual(provider.locomotion(1.2, 1), provider.locomotion(1.2, 1))

    def test_locomotion_capability_is_optional_but_validated_when_declared(self):
        base = dict(key='test', label='Test', parameters=(), supports_rig=False,
                    supports_idle=False, uses_skin_weights=False, supports_materials=False,
                    mesh=lambda values: None)
        provider = SimpleNamespace(**base)
        self.assertIs(validate_provider(provider), provider)
        with self.assertRaisesRegex(ValueError, 'locomotion support requires rig support'):
            validate_provider(SimpleNamespace(**dict(base, supports_locomotion=True,
                                                    locomotion=lambda duration, strength: None)))
        rigged = dict(base, supports_rig=True, skeleton=lambda values: None, supports_locomotion=True)
        with self.assertRaisesRegex(TypeError, 'locomotion'):
            validate_provider(SimpleNamespace(**rigged))


if __name__ == '__main__':
    unittest.main()
