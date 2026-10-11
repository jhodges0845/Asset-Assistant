# SPDX-License-Identifier: GPL-3.0-or-later
"""Facial and paw relief preserve ownership, bilateral symmetry and support."""
import unittest
from math import isfinite
from object_core.objects import get_provider
from object_core.providers.quadruped import _construction
from object_core.providers.quadruped_detail import shape_canine_face, shape_canine_paw_detail
from object_core.providers.quadruped_geometry import _build_quadruped_cage, _ground_paw_surfaces, _shape_paw_surfaces
from object_core.providers.quadruped_refinement import refine_canine_surface
from object_core.modification import SemanticOperation


class CanineDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = get_provider('quadruped')
        cls.values = {p.key:p.default for p in cls.provider.parameters}
        cls.mesh, cls.anatomy = _construction(cls.provider.dimensions(cls.values))
        cage, bound = _build_quadruped_cage(cls.anatomy)
        raw, cls.bound = refine_canine_surface(cage, bound)
        cls.plain = _shape_paw_surfaces(_ground_paw_surfaces(raw.parts[0].vertices, cls.bound), cls.bound)

    def test_face_relief_is_local_symmetric_and_follows_head_modify(self):
        shaped = shape_canine_face(self.plain, self.bound)
        regions = {r.name:set(r.vertex_indices) for r in self.bound.regions}
        changed = {i for i,(a,b) in enumerate(zip(self.plain, shaped)) if a != b}
        self.assertTrue(changed)
        self.assertTrue(changed <= regions['head']-regions['ear.left']-regions['ear.right'])
        actual = {tuple(round(c,6) for c in v) for i,v in enumerate(shaped) if i in regions['head']}
        self.assertTrue(all((-round(x,6),round(y,6),round(z,6)) in actual for i,(x,y,z) in enumerate(shaped) if i in regions['head']))
        self.assertTrue(all(all(isfinite(c) for c in v) for v in shaped))
        moved = self.provider.semantic_mesh(self.mesh, self.values,
            (SemanticOperation('scale','head',(('offset_z',3),)),))
        for i in changed:
            self.assertAlmostEqual(self.mesh.parts[0].vertices[i][2]+3,moved.parts[0].vertices[i][2])

    def test_pad_relief_keeps_ground_points_and_each_limb_ownership(self):
        shaped = shape_canine_paw_detail(self.plain,self.bound)
        changed = {i for i,(a,b) in enumerate(zip(self.plain,shaped)) if a != b}
        limbs = [r for r in self.bound.regions if r.name.startswith('leg.')]
        self.assertTrue(changed <= set().union(*(set(r.vertex_indices) for r in limbs)))
        for r in limbs:
            self.assertTrue(changed & set(r.vertex_indices))
            self.assertAlmostEqual(0,min(shaped[i][2] for i in r.vertex_indices))
            self.assertTrue(any(shaped[i][2]>self.plain[i][2] for i in r.vertex_indices))
            self.assertTrue(any(shaped[i][1]>self.plain[i][1] for i in r.vertex_indices))
        for a,b in zip(self.plain,shaped):
            self.assertEqual(a[0],b[0])
            self.assertGreaterEqual(b[2],a[2])
            if a[2] == 0:
                self.assertEqual(a,b)
