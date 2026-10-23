# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
try:
    import bpy
except ModuleNotFoundError:
    bpy=None

@unittest.skipIf(bpy is None,'requires Blender')
class HumanContactBlenderTests(unittest.TestCase):
    def test_actual_walk_and_run_contact_between_keys(self):
        from scripts.review_human_motion import review_cycle
        for clip in ('walk','run'):
            report=review_cycle(180,95,clip,31)
            self.assertGreaterEqual(report['minimum_foot_z_cm'],0.)
            self.assertGreaterEqual(report['min_edge_ratio'],.5)
            self.assertLessEqual(report['max_edge_ratio'],2.)
            self.assertLess(report['max_stance_target_error_cm'],.003)
            self.assertLess(report['closure_error_cm'],.0001)
            if clip=='walk':
                self.assertLess(report['maximum_lowest_foot_z_cm'],.03)
            else:
                self.assertGreater(report['maximum_lowest_foot_z_cm'],.1)
