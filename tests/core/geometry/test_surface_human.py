# SPDX-License-Identifier: GPL-3.0-or-later
import json
import tempfile
import unittest
from pathlib import Path
from object_core.geometry.surface_human import SurfaceHumanSpec,generate_surface_human
from object_core.providers.surface_human import SurfaceHumanProvider,audit_surface,load_surface_preset

class SurfaceHumanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mesh,cls.report=SurfaceHumanProvider().build(SurfaceHumanSpec())

    def test_closed_connected_orientable_nonzero_surface(self):
        self.assertTrue(self.report['passed'])
        self.assertEqual(self.report['euler_characteristic'],2)
        self.assertEqual(self.report['components'],1)
        self.assertGreater(self.mesh.vertex_count,10000)

    def test_deterministic_geometry_and_topology(self):
        self.assertEqual(self.mesh,generate_surface_human(SurfaceHumanSpec()))
        changed=generate_surface_human(SurfaceHumanSpec(chest_fullness=0.0))
        self.assertEqual(self.mesh.parts[0].faces,changed.parts[0].faces)
        self.assertNotEqual(self.mesh.parts[0].vertices,changed.parts[0].vertices)

    def test_neutral_surface_is_bilaterally_symmetric(self):
        # Decimal rounding can place exact mirrored values on opposite sides
        # of a rounding tie. Compare distances at the same 1e-5 cm tolerance.
        from itertools import product
        from math import floor
        from collections import defaultdict
        tolerance=1e-5
        points=self.mesh.parts[0].vertices
        bins=defaultdict(list)
        for point in points:
            bins[tuple(floor(c/tolerance) for c in point)].append(point)
        for x,y,z in points:
            target=(-x,y,z)
            cell=tuple(floor(c/tolerance) for c in target)
            candidates=(p for delta in product((-1,0,1),repeat=3)
                        for p in bins.get(tuple(cell[d]+delta[d] for d in range(3)),()))
            self.assertTrue(any(max(abs(p[d]-target[d]) for d in range(3))<=tolerance
                                for p in candidates), 'Missing mirror for %r' % (target,))

    def test_height_and_ground(self):
        for height in (150,200):
            mesh=generate_surface_human(SurfaceHumanSpec(height_cm=height))
            self.assertAlmostEqual(mesh.bounds_cm[0][2],0)
            self.assertAlmostEqual(mesh.bounds_cm[1][2],height)
            self.assertTrue(audit_surface(mesh)['passed'])

    def test_invalid_controls_fail_instead_of_silently_clamping(self):
        for value in (float('nan'),float('inf'),True,'175',0,250):
            with self.assertRaises(ValueError):SurfaceHumanSpec(height_cm=value)
        with self.assertRaises(ValueError):SurfaceHumanSpec(hip_scale=2)
        with self.assertRaises(ValueError):SurfaceHumanSpec(chest_fullness=-.1)
        with self.assertRaises(TypeError):generate_surface_human(None)

    def test_preset_rejects_unknown_fields_and_versions(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'preset.json'
            for value in ({}, {'schema_version':2,'generator':'surface-human-1','parameters':{}}, {'schema_version':1,'generator':'surface-human-1','parameters':{'invented_control':1}}):
                path.write_text(json.dumps(value))
                with self.assertRaises((ValueError,TypeError)):load_surface_preset(path)
            path.write_text(json.dumps({'schema_version':1,'generator':'surface-human-1','parameters':{}}))
            self.assertEqual(load_surface_preset(path),SurfaceHumanSpec())

    def test_report_does_not_claim_visual_or_animation_acceptance(self):
        self.assertEqual(self.report['quality_status'],'experimental_anatomical_study')
        self.assertIn('reference_likeness',self.report['not_checked'])
        self.assertFalse(SurfaceHumanProvider.supports_rig)

if __name__=='__main__':unittest.main()
