# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from object_core.lod import plan_lods


class LODPlanTests(unittest.TestCase):
    def test_budgets_are_measured_from_source(self):
        self.assertEqual([160, 80], [level.triangle_budget for level in plan_lods(320)])

    def test_invalid_and_nonreducing_requests_are_rejected(self):
        for count, ratios in [(7, (.5,)), (True, (.5,)), (320, ()),
                              (320, (float('nan'),)), (320, (True,)),
                              (320, (1.,)), (320, (.25, .5)), (8, (.5, .25))]:
            with self.subTest(count=count, ratios=ratios), self.assertRaises(ValueError):
                plan_lods(count, ratios)
