# SPDX-License-Identifier: GPL-3.0-or-later
"""Refinement preserves authored ownership and rejects invalid cages."""
import unittest

from object_core.objects import get_provider
from object_core.modification import SemanticOperation
from object_core.models import MeshPart, ObjectMesh
from object_core.providers.quadruped import _construction
from object_core.providers.quadruped_geometry import _build_quadruped_cage
from object_core.providers.quadruped_refinement import refine_canine_surface


class CanineRefinementTests(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider('quadruped')
        self.values = {p.key: p.default for p in self.provider.parameters}
        self.mesh, self.anatomy = _construction(self.provider.dimensions(self.values))

    def test_refined_connections_are_real_closed_edge_loops(self):
        part = self.mesh.parts[0]
        edges = {tuple(sorted((a, b))) for face in part.faces
                 for a, b in zip(face, face[1:] + face[:1])}
        self.assertTrue(all(len(face) == 4 for face in part.faces))
        self.assertEqual(set(range(len(part.vertices))), set(self.anatomy.regions[0].vertex_indices))
        for connection in self.anatomy.connections:
            for loop in connection.boundaries:
                self.assertEqual(len(loop), len(set(loop)))
                self.assertTrue(all(tuple(sorted((a, b))) in edges
                                    for a, b in zip(loop, loop[1:] + loop[:1])))

    def test_refinement_rejects_open_and_reversed_cages(self):
        cage, anatomy = _build_quadruped_cage(self.anatomy)
        part = cage.parts[0]
        for faces in (part.faces[1:], (tuple(reversed(part.faces[0])),) + part.faces[1:]):
            with self.assertRaises(ValueError):
                refine_canine_surface(ObjectMesh((MeshPart(part.name, part.vertices, faces),)), anatomy)

    def test_ear_edits_keep_head_skinning_and_head_edit_moves_ears(self):
        regions = {r.name: set(r.vertex_indices) for r in self.anatomy.regions}
        for side in ('left', 'right'):
            target = 'ear.' + side
            self.assertTrue(regions[target] <= regions['head'])
            moved = self.provider.semantic_mesh(self.mesh, self.values, (
                SemanticOperation('scale', target, (('offset_x', 80), ('offset_z', -60))),))
            weights = self.provider.skin_weights(moved, self.values)[0]
            for i in regions[target]:
                self.assertEqual({'head'}, {w.bone_name for w in weights.vertices[i]})
        moved = self.provider.semantic_mesh(self.mesh, self.values, (
            SemanticOperation('scale', 'head', (('offset_z', 3),)),))
        for i in regions['ear.left'] | regions['ear.right']:
            self.assertAlmostEqual(self.mesh.parts[0].vertices[i][2] + 3, moved.parts[0].vertices[i][2])

    def test_surface_starts_below_rig_pivots_and_on_correct_side(self):
        cage, anatomy = _build_quadruped_cage(self.anatomy)
        points = {p.name: p.position for p in anatomy.landmarks}
        for connection in anatomy.connections:
            if not connection.regions[1].startswith('leg.'):
                continue
            root, ring = connection.boundaries
            sign = -1 if connection.regions[1].endswith('.left') else 1
            self.assertTrue(all(cage.parts[0].vertices[i][0] * sign >= -1e-9 for i in root))
            center_z = sum(cage.parts[0].vertices[i][2] for i in ring) / len(ring)
            self.assertLess(center_z, points[connection.name][2])
