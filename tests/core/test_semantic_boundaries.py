# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression for visible steps at broad shoulder/chest region boundaries."""
import unittest
from object_core.objects import get_provider
from object_core.modification import SemanticOperation


class SemanticBoundaryTests(unittest.TestCase):
    def prove(self, key, target):
        provider = get_provider(key)
        values = {f.key: f.default for f in provider.parameters}
        mesh = provider.mesh(values)
        part = mesh.parts[0]
        if key == 'human':
            from object_core.providers.human import _human_anatomy
            from object_core.providers.human_semantic import _bounds, _selected
            anatomy = _human_anatomy(**values)
            bounds = _bounds(anatomy.proportions, anatomy=anatomy)
            selected = {i for i,v in enumerate(part.vertices)
                        if _selected(target,v,anatomy.proportions,bounds)}
        else:
            from object_core.providers.quadruped import _construction
            _, anatomy = _construction(provider.dimensions(values))
            selected = set(next(r.vertex_indices for r in anatomy.regions if r.name == target))
        boundary = set()
        for face in part.faces:
            for a,b in zip(face, face[1:]+face[:1]):
                if (a in selected) != (b in selected):
                    boundary.add(a if a in selected else b)
        self.assertTrue(boundary)
        for amount in (0., .6, 1.5):
            with self.subTest(provider=key, amount=amount):
                operation = SemanticOperation('shape',target,(('profile','broad'),('amount',amount)))
                result = provider.semantic_mesh(mesh,values,(operation,)).parts[0]
                self.assertEqual(part.faces,result.faces)
                self.assertEqual(part.uvs,result.uvs)
                changed = set()
                for i,(before,after) in enumerate(zip(part.vertices,result.vertices)):
                    if i not in selected or i in boundary:
                        for a,b in zip(before,after):
                            self.assertAlmostEqual(a,b,places=12)
                    if before != after:
                        changed.add(i)
                if amount:
                    self.assertTrue(changed)
                    self.assertGreater(sum(abs(result.vertices[i][0]) for i in selected),
                                       sum(abs(part.vertices[i][0]) for i in selected))
                else:
                    for before,after in zip(part.vertices,result.vertices):
                        for a,b in zip(before,after):
                            self.assertAlmostEqual(a,b,places=12)

    def test_human_shoulders_preserve_seam_and_unselected_geometry(self):
        self.prove('human','shoulders')

    def test_canine_chest_preserves_seam_and_unselected_geometry(self):
        self.prove('quadruped','chest')

    def test_fully_selected_island_keeps_full_transform(self):
        from object_core.providers.semantic_geometry import _blend_region_transform
        vertices = ((0.,0.,0.),(1.,0.,0.),(0.,1.,0.))
        result = _blend_region_transform(vertices,((0,1,2),),(0,1,2),{'offset_z':2.})
        self.assertEqual(result,[(x,y,z+2.) for x,y,z in vertices])

    def test_boundary_only_region_does_not_make_a_step_or_move_other_island(self):
        from object_core.providers.semantic_geometry import _blend_region_transform
        vertices = ((0.,0.,0.),(1.,0.,0.),(0.,1.,0.),
                    (4.,0.,0.),(5.,0.,0.),(4.,1.,0.))
        faces = ((0,1,2),(3,4,5))
        result = _blend_region_transform(vertices,faces,(0,3,4,5),{'offset_z':2.})
        self.assertEqual(result[:3],list(vertices[:3]))
        self.assertEqual(result[3:],[(x,y,z+2.) for x,y,z in vertices[3:]])
