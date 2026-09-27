# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from types import SimpleNamespace

from scripts.canine_review_metrics import limb_ground_clearance


class CanineReviewMetricsTests(unittest.TestCase):
    def test_signed_clearance_uses_authored_limbs_and_centimeters(self):
        vertices = ((0, 0, -2), (0, 0, 3), (0, 0, 0), (0, 0, -100))
        regions = [SimpleNamespace(name=name, vertex_indices=indices) for name, indices in (
            ('leg.front.left', (0, 1)), ('leg.front.right', (1,)),
            ('leg.hind.left', (2,)), ('torso', (3,)))]
        result = limb_ground_clearance(vertices, regions)
        self.assertEqual(result['leg.front.left'],
                         dict(minimum_z_cm=-2, penetration_cm=2, gap_cm=0))
        self.assertEqual(result['leg.front.right'],
                         dict(minimum_z_cm=3, penetration_cm=0, gap_cm=3))
        self.assertEqual(result['leg.hind.left'],
                         dict(minimum_z_cm=0, penetration_cm=0, gap_cm=0))
        self.assertNotIn('torso', result)

    def test_missing_or_nonfinite_measurements_fail(self):
        region = SimpleNamespace(name='leg.front.left', vertex_indices=())
        with self.assertRaises(ValueError):
            limb_ground_clearance((), [region])
        with self.assertRaises(ValueError):
            limb_ground_clearance((), [])
        region.vertex_indices = (0,)
        for height in (float('nan'), float('inf'), -float('inf')):
            with self.subTest(height=height), self.assertRaises(ValueError):
                limb_ground_clearance(((0, 0, height),), [region])
