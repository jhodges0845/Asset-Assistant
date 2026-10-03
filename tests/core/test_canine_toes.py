# SPDX-License-Identifier: GPL-3.0-or-later
"""Local paw detail preserves contact, ownership and connected construction."""
from collections import Counter
from dataclasses import replace
import unittest

from object_core.objects import get_provider
from object_core.providers.quadruped import _construction
from object_core.providers.quadruped_geometry import (
    _build_quadruped_cage, _ground_paw_surfaces, _shape_paw_surfaces)
from object_core.providers.quadruped_refinement import (
    _densify_paw_cages, refine_canine_surface)


class CanineToeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        provider = get_provider('quadruped')
        values = {p.key: p.default for p in provider.parameters}
        cls.mesh, cls.anatomy = _construction(provider.dimensions(values))

    def test_terminal_detail_retains_seams_and_nonlimb_ownership(self):
        cage, anatomy = _build_quadruped_cage(self.anatomy)
        detailed, resolved = _densify_paw_cages(cage, anatomy)
        original, part = cage.parts[0], detailed.parts[0]
        self.assertEqual(original.vertices, part.vertices[:len(original.vertices)])
        self.assertEqual(anatomy.connections, resolved.connections)
        original_regions = {r.name: set(r.vertex_indices) for r in anatomy.regions}
        for region in resolved.regions:
            if region.name not in ('body',) and not region.name.startswith('leg.front.'):
                self.assertEqual(original_regions[region.name], set(region.vertex_indices))
        new_indices = set(range(len(original.vertices), len(part.vertices)))
        limb_indices = set().union(*(set(r.vertex_indices) for r in resolved.regions
                                    if r.name.startswith('leg.front.')))
        self.assertTrue(new_indices)
        self.assertTrue(new_indices <= limb_indices)
        directed = Counter((a, b) for face in part.faces
                           for a, b in zip(face, face[1:] + face[:1]))
        self.assertTrue(all(n == 1 and directed[(b, a)] == 1
                            for (a, b), n in directed.items()))
        # Euler characteristic of the connected closed genus-zero surface.
        self.assertEqual(2, len(part.vertices) - len(directed) // 2 + len(part.faces))

    def test_toe_contour_only_retracts_low_front_surface_and_preserves_contact(self):
        cage, anatomy = _build_quadruped_cage(self.anatomy)
        refined, anatomy = refine_canine_surface(cage, anatomy)
        grounded = _ground_paw_surfaces(refined.parts[0].vertices, anatomy)
        plain = _shape_paw_surfaces(grounded, replace(anatomy,
            paw_profile=replace(anatomy.paw_profile, front_toe_indent_scale=0)))
        shaped = _shape_paw_surfaces(grounded, anatomy)
        changed = {i for i, (a, b) in enumerate(zip(plain, shaped)) if a != b}
        self.assertTrue(changed)
        regions = [r for r in anatomy.regions if r.name.startswith('leg.front.')]
        self.assertTrue(changed <= set().union(*(set(r.vertex_indices) for r in regions)))
        points = {p.name: p.position for p in anatomy.landmarks}
        for a, b in zip(plain, shaped):
            self.assertEqual(a[0], b[0])
            self.assertEqual(a[2], b[2])
            self.assertLessEqual(b[1], a[1])
        for region in regions:
            indices = set(region.vertex_indices)
            suffix = region.name[4:]
            upper = points[('ankle.' if suffix.startswith('front.') else 'hock.') + suffix][2]
            height = min(anatomy.paw_profile.height_cm, upper)
            low = [i for i in indices if plain[i][2] < height]
            rear = min(plain[i][1] for i in low)
            length = max(plain[i][1] for i in low) - rear
            self.assertTrue(changed & indices)
            for i in changed & indices:
                self.assertLess(shaped[i][2], height)
                self.assertGreater(plain[i][1], rear + .45 * length)
            self.assertAlmostEqual(0, min(shaped[i][2] for i in indices))

    def test_toe_depth_validation(self):
        profile = self.anatomy.paw_profile
        for value in (-.01, .201, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replace(profile, front_toe_indent_scale=value)
        for value in (True, None, '0.1'):
            with self.subTest(value=value), self.assertRaises(TypeError):
                replace(profile, front_toe_indent_scale=value)
        for value in (0, .2):
            self.assertEqual(value, replace(profile, front_toe_indent_scale=value).front_toe_indent_scale)
