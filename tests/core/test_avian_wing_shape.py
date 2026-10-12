# SPDX-License-Identifier: GPL-3.0-or-later
"""Wing profile changes preserve the surrounding bird and rest rig."""
from dataclasses import asdict, replace
import json
from math import isfinite
from pathlib import Path
import unittest

from object_core.objects import get_provider
from object_core.models import ObjectMesh


class AvianWingShapeTests(unittest.TestCase):
    def test_attachment_refinement_preserves_body_shape_and_axial_rig_under_vertical_lift(self):
        samples = json.loads((Path(__file__).parents[1] / 'fixtures/avian_wing_shape_baseline.json').read_text())
        provider = get_provider('avian')
        for name, sample in samples.items():
            with self.subTest(sample=name):
                mesh = provider.mesh(sample['parameters'])
                anatomy = provider.anatomy(sample['parameters'])
                indices = [i for r in anatomy.regions if r.name == 'body' for i in r.vertex_indices]
                self.assertEqual(len(indices), 72)
                lift = mesh.parts[0].vertices[0][2] - sample['nonwing_vertices'][0][2]
                self.assertGreater(lift, 0)
                for actual, expected in zip((mesh.parts[0].vertices[i] for i in indices), sample['nonwing_vertices'][:72]):
                    expected = (expected[0], expected[1], expected[2] + lift)
                    for a, b in zip(actual, expected):
                        self.assertAlmostEqual(a, b, places=9)
                self.assertEqual(mesh.vertex_count, 312)
                self.assertEqual(mesh.face_count, 326)
                # An older generated cage must not receive current-recipe weights.
                old_part = replace(mesh.parts[0], faces=tuple(tuple(f) for f in sample['faces']), uvs=())
                with self.assertRaisesRegex(ValueError, 'authored topology'):
                    provider.skin_weights(ObjectMesh((old_part,)), sample['parameters'])
                bones = json.loads(json.dumps(asdict(provider.skeleton(sample['parameters']))))['bones']
                expected_bones = [b for b in sample['skeleton']['bones'] if not b['name'].startswith(('wing.', 'leg.', 'foot.'))]
                for actual, expected in zip([b for b in bones if not b['name'].startswith(('wing.', 'leg.', 'foot.'))], expected_bones):
                    self.assertEqual(actual['name'], expected['name'])
                    self.assertEqual(actual['parent'], expected['parent'])
                    for endpoint in ('head', 'tail'):
                        for axis in range(3):
                            self.assertAlmostEqual(actual[endpoint][axis], expected[endpoint][axis] + (lift if axis == 2 else 0))


    def test_wing_middle_is_broad_thin_and_tapers_to_tip(self):
        provider = get_provider('avian')
        defaults = {p.key: p.default for p in provider.parameters}
        for values in (defaults, dict(defaults, body_length_cm=55, body_width_cm=22,
                                     body_height_cm=28, wingspan_cm=140, tail_length_cm=35)):
            anatomy = provider.anatomy(values)
            wings = [t for t in anatomy.tubes if t.name.startswith('wing.')]
            self.assertEqual(wings[0].widths, wings[1].widths)
            self.assertEqual(wings[0].depths, wings[1].depths)
            for wing in wings:
                self.assertGreater(wing.widths[2], wing.depths[2] * 3)
                self.assertGreater(wing.widths[2], wing.widths[1])
                self.assertGreater(wing.widths[2], wing.widths[3])
                self.assertLess(wing.widths[-1], wing.widths[2] * .15)
            mesh = provider.mesh(values)
            self.assertTrue(all(isfinite(c) for v in mesh.parts[0].vertices for c in v))
            regions = {r.name: r.vertex_indices for r in anatomy.regions}
            left = sorted(tuple(round(c, 6) for c in v) for i, v in enumerate(mesh.parts[0].vertices)
                          if i in regions['wing.left'])
            right = sorted((round(-v[0], 6), round(v[1], 6), round(v[2], 6))
                           for i, v in enumerate(mesh.parts[0].vertices) if i in regions['wing.right'])
            self.assertEqual(left, right)
