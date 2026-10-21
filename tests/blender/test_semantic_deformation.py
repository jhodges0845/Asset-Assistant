# SPDX-License-Identifier: GPL-3.0-or-later
"""Applied broad profiles must preserve the paired-pose deformation boundary."""
import unittest
from unittest.mock import patch
try:
    import bpy
except ModuleNotFoundError:
    bpy = None


@unittest.skipIf(bpy is None,'requires Blender')
class SemanticDeformationTests(unittest.TestCase):
    def prove(self,key):
        from scripts.review_semantic_deformation import review_case
        scene = bpy.context.window.scene
        kinds = ('objects','meshes','armatures','collections','materials','actions','scenes')
        before = {kind:set(getattr(bpy.data,kind)) for kind in kinds}
        results = {}
        for sample in ('default','contrasting'):
            for amount in (.6,1.5):
                with self.subTest(sample=sample,amount=amount):
                    report,parts = review_case(key,sample,amount)
                    results[(sample,amount)] = all(p['edge_limit_passed'] for p in report['poses'])
                    self.assertEqual(4,len(report['poses']))
                    self.assertNotEqual(parts['before'].vertices,parts['after'].vertices)
                    self.assertEqual(parts['before'].faces,parts['after'].faces)
                    self.assertIs(bpy.context.window.scene,scene)
                    self.assertEqual(before,{kind:set(getattr(bpy.data,kind)) for kind in kinds})

        self.assertTrue(all(results.values()))

    def test_human_shoulders_under_diagnostic_bends(self):
        self.prove('human')

    def test_canine_broad_chest_under_diagnostic_bends(self):
        self.prove('quadruped')

    def test_avian_chest_preserves_wings_under_diagnostic_bends(self):
        self.prove('avian')

    def test_invalid_review_keeps_scene_data_intact(self):
        from scripts.review_semantic_deformation import review_case
        scene = bpy.context.window.scene
        before = set(bpy.data.objects)
        for args in [('missing','default',.6),('human','missing',.6),('human','default',float('nan'))]:
            with self.assertRaises(ValueError): review_case(*args)
        self.assertIs(bpy.context.window.scene,scene)
        self.assertEqual(before,set(bpy.data.objects))

    def test_strict_screen_rejects_unbounded_profile_and_restores_scene(self):
        from scripts.review_semantic_deformation import review_case
        scene = bpy.context.window.scene
        kinds = ('objects','meshes','armatures','collections','materials','actions','scenes')
        before = {kind:set(getattr(bpy.data,kind)) for kind in kinds}
        # Reproduce the old unbounded profile while keeping current skin weights.
        # This guards the real screening/cleanup path without requiring a live defect.
        with patch('object_core.providers.human_semantic._limit_shoulder_displacement',
                   side_effect=lambda vertices, faces, changed: changed):
            with self.assertRaisesRegex(RuntimeError,'relative edge ratios'):
                review_case('human','contrasting',1.5)
        self.assertIs(bpy.context.window.scene,scene)
        self.assertEqual(before,{kind:set(getattr(bpy.data,kind)) for kind in kinds})
