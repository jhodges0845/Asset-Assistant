# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
try:
    import bpy
except ModuleNotFoundError:
    bpy=None

@unittest.skipIf(bpy is None,'requires Blender')
class AvianTransitionTests(unittest.TestCase):
    def test_fold_to_flight_blends_are_clear_and_match_actual_endpoints(self):
        from scripts.review_avian_transition import review_transition
        from scripts.avian_review_samples import AVIAN_REVIEW_SAMPLES,review_values
        scene=bpy.context.window.scene
        kinds=('scenes','objects','meshes','armatures','actions','materials','collections')
        before={kind:set(getattr(bpy.data,kind)) for kind in kinds}
        for name in ('default',)+tuple(AVIAN_REVIEW_SAMPLES):
            for strength in (.1,1.,2.):
                report=review_transition(review_values(name),intervals=64,strength=strength)
                self.assertEqual(report['crossing_samples'],0,(name,strength))
                self.assertLess(report['endpoint_error_cm'],1e-4)
        self.assertIs(bpy.context.window.scene,scene)
        self.assertEqual(before,{kind:set(getattr(bpy.data,kind)) for kind in kinds})
