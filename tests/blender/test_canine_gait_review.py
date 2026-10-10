# SPDX-License-Identifier: GPL-3.0-or-later
"""Gait reports sample evaluated actions and leave caller-owned scenes intact."""
import unittest
from unittest.mock import patch

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from object_core.objects import get_provider
from scripts.review_canine_gait import review_cycle


@unittest.skipIf(bpy is None, 'requires Blender')
class CanineGaitReviewTests(unittest.TestCase):
    def setUp(self):
        provider = get_provider('quadruped')
        self.values = {p.key: p.default for p in provider.parameters}
        self.scene = bpy.context.window.scene
        self.frame = (self.scene.frame_current, self.scene.frame_subframe)
        self.names = ('objects', 'meshes', 'armatures', 'collections', 'actions', 'materials', 'scenes')
        self.before = {name: set(getattr(bpy.data, name)) for name in self.names}

    def assert_caller_preserved(self):
        self.assertIs(self.scene, bpy.context.window.scene)
        self.assertEqual(self.frame, (self.scene.frame_current, self.scene.frame_subframe))
        for name in self.names:
            self.assertEqual(self.before[name], set(getattr(bpy.data, name)), name)

    def test_real_walk_and_run_have_motion_closed_cycles_and_consistent_reports(self):
        for clip, duration in (('walk', 1.2), ('run', .64)):
            with self.subTest(clip=clip):
                report = review_cycle(self.values, clip, intervals=127)
                self.assertEqual(len(report['frames']), 128)
                self.assertGreater(report['maximum_vertex_motion_cm'], 1)
                self.assertLess(report['loop_closure_error_cm'], .0001)
                self.assertEqual(report['frames'][0]['phase'], 0)
                self.assertEqual(report['frames'][-1]['phase'], 1)
                self.assertAlmostEqual(report['frames'][-1]['frame'], 1 + duration * 24)
                self.assertEqual(len(report['limbs']), 4)
                for name, summary in report['limbs'].items():
                    heights = [f['ground_clearance'][name]['minimum_z_cm'] for f in report['frames']]
                    self.assertEqual(summary['minimum_z_cm'], min(heights))
                    self.assertEqual(summary['maximum_z_cm'], max(heights))
                    self.assertGreater(summary['sole_centroid_xy_excursion_cm'], .1)
                    self.assertTrue(report['sole_vertex_indices'][name])
                    self.assertGreaterEqual(summary['minimum_z_cm'], -.001)
                    self.assertLess(summary['maximum_clearance_target_error_cm'], .03)
                    self.assertLess(summary['maximum_forward_target_error_cm'], .03)
                    self.assertLess(summary['reference_stance_drift_cm'], .03)
                    self.assertGreater(summary['reference_stance_samples'], 2)
                    self.assertEqual(summary['reference_material_stance_samples'],
                                     summary['reference_stance_samples'])
                    self.assertGreaterEqual(summary['maximum_reference_vertex_displacement_cm'], 0.)
                    if name.startswith('leg.'):
                        toe = summary['toe_material_motion']
                        self.assertGreater(toe['near_ground_vertex_comparisons'], 0)
                        limit = .002 if '.front.' in name else .001
                        self.assertLess(toe['maximum_near_ground_episode_displacement_cm'], limit)
                    toe_ids = report['toe_vertex_indices'][name]
                    self.assertTrue(toe_ids)
                    self.assertLess(len(toe_ids), len(report['sole_vertex_indices'][name]))
                    self.assertTrue(set(toe_ids).issubset(report['sole_vertex_indices'][name]))
                    for metric in (summary, summary['toe_material_motion']):
                        self.assertEqual(metric['near_ground_tolerance_cm'], .1)
                        self.assertGreaterEqual(metric['near_ground_vertex_comparisons'], 0)
                        displacement = metric['maximum_near_ground_episode_displacement_cm']
                        if metric['near_ground_vertex_comparisons']:
                            self.assertGreaterEqual(displacement, 0.)
                        else:
                            self.assertIsNone(displacement)
                self.assert_caller_preserved()

    def test_failure_and_invalid_input_leave_caller_data_intact(self):
        for kwargs in (dict(intervals=True), dict(intervals=3), dict(intervals=257),
                       dict(clip='flight'), dict(strength=0)):
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, TypeError)):
                review_cycle(self.values, **kwargs)
            self.assert_caller_preserved()
        with patch('scripts.review_canine_gait.limb_support_footprint',
                   side_effect=RuntimeError('injected metric failure')):
            with self.assertRaisesRegex(RuntimeError, 'injected metric failure'):
                review_cycle(self.values, intervals=4)
        self.assert_caller_preserved()
