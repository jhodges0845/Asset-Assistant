# SPDX-License-Identifier: GPL-3.0-or-later
"""Sampling and isolation checks for actual Avian action reviews."""
import unittest
try:
    import bpy
except ModuleNotFoundError:
    bpy = None
from object_core.objects import get_provider
from scripts.review_avian_gait import review_cycle


@unittest.skipIf(bpy is None, 'requires Blender')
class AvianGaitReviewTests(unittest.TestCase):
    def setUp(self):
        self.values = {p.key:p.default for p in get_provider('avian').parameters}

    def test_actual_actions_are_sampled_and_scene_data_is_restored(self):
        scene = bpy.context.window.scene
        kinds = ('scenes','objects','meshes','armatures','collections','actions','materials')
        before = {kind:set(getattr(bpy.data,kind)) for kind in kinds}
        for clip in ('idle','walk'):
            report = review_cycle(self.values,clip,intervals=8)
            self.assertEqual(len(report['samples']),9)
            self.assertGreater(report['maximum_surface_motion_cm'],.01)
            self.assertLess(report['loop_closure_error_cm'],1e-4)
            for name,summary in report['summary'].items():
                heights = [row['feet'][name]['minimum_z_cm'] for row in report['samples']]
                self.assertEqual(summary['minimum_z_cm'],min(heights))
                self.assertEqual(summary['penetrating_samples'] + summary['lifted_samples'] + summary['near_ground_samples'],9)
                self.assertEqual(len(report['fixed_sole_indices'][name]),15)
                if clip == 'idle':
                    self.assertLess(summary['maximum_fixed_sole_motion_cm'],1e-4)
            self.assertIs(bpy.context.window.scene,scene)
            for kind in kinds:
                self.assertEqual(set(getattr(bpy.data,kind)),before[kind],kind)

    def test_invalid_requests_fail_before_allocating_scene_data(self):
        before = set(bpy.data.scenes)
        for intervals in (True,3,257,4.5):
            with self.assertRaises(ValueError):
                review_cycle(self.values,intervals=intervals)
        with self.assertRaises(ValueError):
            review_cycle(self.values,clip='run')
        self.assertEqual(set(bpy.data.scenes),before)

    def test_walk_clearance_between_keys_on_both_shapes_and_strength_extremes(self):
        from scripts.anatomy_baseline import SAMPLES
        for values in (self.values,SAMPLES['avian']):
            for strength in (.1,1.,2.):
                report = review_cycle(values,intervals=127,strength=strength)
                self.assertLess(report['loop_closure_error_cm'],1e-4)
                for summary in report['summary'].values():
                    self.assertGreater(summary['minimum_z_cm'],.018)
                    self.assertEqual(summary['penetrating_samples'],0)
                    self.assertGreater(summary['maximum_minimum_z_cm'],.05)
