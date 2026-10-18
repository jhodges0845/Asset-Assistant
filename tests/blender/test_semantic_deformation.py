# SPDX-License-Identifier: GPL-3.0-or-later
"""Applied broad profiles must preserve the paired-pose deformation boundary."""
import unittest
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
                    report,parts = review_case(key,sample,amount,enforce_limits=False)
                    results[(sample,amount)] = all(p['edge_limit_passed'] for p in report['poses'])
                    self.assertEqual(4,len(report['poses']))
                    self.assertNotEqual(parts['before'].vertices,parts['after'].vertices)
                    self.assertEqual(parts['before'].faces,parts['after'].faces)
                    self.assertIs(bpy.context.window.scene,scene)
                    self.assertEqual(before,{kind:set(getattr(bpy.data,kind)) for kind in kinds})

        if key == 'quadruped':
            self.assertTrue(all(results.values()))
        elif key == 'avian':
            # Current chest selection cuts across authored wing regions.
            self.assertFalse(any(results.values()))
        else:
            # Keep the screening failure explicit until Human quality work resolves it.
            self.assertTrue(results[('default',.6)])
            self.assertFalse(results[('contrasting',1.5)])

    def test_human_profile_diagnostics_record_known_limits(self):
        self.prove('human')

    def test_canine_broad_chest_under_diagnostic_bends(self):
        self.prove('quadruped')

    def test_avian_chest_diagnostics_record_wing_boundary_failure(self):
        self.prove('avian')

    def test_invalid_review_keeps_scene_data_intact(self):
        from scripts.review_semantic_deformation import review_case
        scene = bpy.context.window.scene
        before = set(bpy.data.objects)
        for args in [('missing','default',.6),('human','missing',.6),('human','default',float('nan'))]:
            with self.assertRaises(ValueError): review_case(*args)
        self.assertIs(bpy.context.window.scene,scene)
        self.assertEqual(before,set(bpy.data.objects))

    def test_strict_screen_rejects_known_human_case_and_restores_scene(self):
        from scripts.review_semantic_deformation import review_case
        scene = bpy.context.window.scene
        kinds = ('objects','meshes','armatures','collections','materials','actions','scenes')
        before = {kind:set(getattr(bpy.data,kind)) for kind in kinds}
        for key in ('human','avian'):
            with self.subTest(provider=key), self.assertRaisesRegex(RuntimeError,'relative edge ratios'):
                review_case(key,'contrasting',1.5)
        self.assertIs(bpy.context.window.scene,scene)
        self.assertEqual(before,{kind:set(getattr(bpy.data,kind)) for kind in kinds})
