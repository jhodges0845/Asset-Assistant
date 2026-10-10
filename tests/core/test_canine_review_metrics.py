# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from types import SimpleNamespace

from scripts.canine_review_metrics import limb_ground_clearance, limb_support_footprint


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


class CanineSupportFootprintTests(unittest.TestCase):
    def test_clips_edges_and_excludes_other_regions(self):
        # Sloped rectangle: its 0..0.1 cm band is 2 cm wide and 0.1 cm long.
        vertices = ((0, 0, -1), (2, 0, -1), (2, 2, 1), (0, 2, 1), (100, 100, 0))
        region = SimpleNamespace(name='leg.front.left', vertex_indices=(0, 1, 2, 3))
        result = limb_support_footprint(vertices, ((0, 1, 2, 3),), [region])[region.name]
        self.assertAlmostEqual(result['near_ground_hull_area_cm2'], .2)
        self.assertAlmostEqual(result['width_cm'], 2)
        self.assertAlmostEqual(result['length_cm'], .1)
        self.assertEqual(result['tolerance_cm'], .1)

    def test_distinguishes_point_flat_support_and_lift(self):
        region = SimpleNamespace(name='leg.front.left', vertex_indices=(0, 1, 2, 3))
        faces = ((0, 1, 2, 3),)
        for height, expected in ((0, 6), (.05, 6), (1, 0), (-1, 0)):
            vertices = tuple((x, y, height) for x, y in ((0, 0), (2, 0), (2, 3), (0, 3)))
            result = limb_support_footprint(vertices, faces, [region])[region.name]
            self.assertEqual(result['near_ground_hull_area_cm2'], expected)
        region.vertex_indices = (0,)
        result = limb_support_footprint(((1, 2, 0),), (), [region])[region.name]
        self.assertEqual(result['near_ground_hull_area_cm2'], 0)
        self.assertEqual(result['width_cm'], 0)

    def test_rejects_invalid_tolerance_and_coordinates(self):
        region = SimpleNamespace(name='leg.front.left', vertex_indices=(0,))
        for tolerance in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                limb_support_footprint(((0, 0, 0),), (), [region], tolerance)
        for coordinate in (float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                limb_support_footprint(((coordinate, 0, 0),), (), [region])


    def test_generated_footprints_are_symmetric_and_lift_with_modify(self):
        from object_core.objects import get_provider
        from object_core.providers.quadruped import _construction
        from object_core.modification import SemanticOperation
        provider = get_provider('quadruped')
        defaults = {p.key: p.default for p in provider.parameters}
        for values in (defaults, dict(defaults, body_length_cm=95, shoulder_height_cm=40,
                                     body_width_cm=28, head_length_cm=30, tail_length_cm=50)):
            mesh, anatomy = _construction(provider.dimensions(values))
            part = mesh.parts[0]
            report = limb_support_footprint(part.vertices, part.faces, anatomy.regions)
            for family in ('front', 'hind'):
                left, right = (report['leg.' + family + '.' + side] for side in ('left', 'right'))
                self.assertGreater(left['near_ground_hull_area_cm2'], 0)
                for key in left:
                    self.assertAlmostEqual(left[key], right[key])
            moved = provider.semantic_mesh(mesh, values, (
                SemanticOperation('scale', 'leg.front.left', (('offset_z', 5),)),))
            lifted = limb_support_footprint(moved.parts[0].vertices, part.faces, anatomy.regions)
            self.assertEqual(lifted['leg.front.left']['near_ground_hull_area_cm2'], 0)
            for name in report.keys() - {'leg.front.left'}:
                self.assertEqual(report[name], lifted[name])


class CanineMaterialMotionTests(unittest.TestCase):
    def test_detects_opposing_vertex_slip_hidden_by_centroid(self):
        from scripts.canine_review_metrics import stance_material_motion
        from object_core.animation.contact import ContactCycle
        schedule = ContactCycle(1, 4, .75, 1)
        phases = (0., .25, .5, .75)
        patches = tuple(((-1-t, -4*t, 0), (1+t, -4*t, 0)) for t in phases)
        result = stance_material_motion(phases, patches, schedule)
        self.assertEqual(result['reference_material_stance_samples'], 3)
        self.assertAlmostEqual(result['maximum_reference_vertex_displacement_cm'], .5)

    def test_wraps_stance_and_compensates_reference_travel(self):
        from scripts.canine_review_metrics import stance_material_motion
        from object_core.animation.contact import ContactCycle
        schedule = ContactCycle(1, 4, .6, 1, .75)
        phases = (0., .25, .5, .75)
        patches = tuple(((2, -4*((t-.75) % 1), 0),) for t in phases)
        result = stance_material_motion(phases, patches, schedule)
        self.assertEqual(result['reference_material_stance_samples'], 3)
        self.assertAlmostEqual(result['maximum_reference_vertex_displacement_cm'], 0)

    def test_rejects_invalid_samples(self):
        from scripts.canine_review_metrics import stance_material_motion
        from object_core.animation.contact import ContactCycle
        schedule = ContactCycle(1, 4, .6, 1)
        for phases, patches in (((), ()),
                                ((0., .2), (((0, 0, 0),), ())),
                                ((.2, .1), (((0, 0, 0),), ((0, 0, 0),))),
                                ((0., .2), (((0, 0, 0),), ((0, float('nan'), 0),)))):
            with self.subTest(phases=phases), self.assertRaises(ValueError):
                stance_material_motion(phases, patches, schedule)

    def test_insufficient_stance_samples_report_unknown_not_zero(self):
        from scripts.canine_review_metrics import stance_material_motion
        from object_core.animation.contact import ContactCycle
        result = stance_material_motion((0.,), (((0, 0, 0),),), ContactCycle(1, 4, .6, 1))
        self.assertEqual(result['reference_material_stance_samples'], 1)
        self.assertIsNone(result['maximum_reference_vertex_displacement_cm'])
