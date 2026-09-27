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

    def test_body_regions_do_not_acquire_limb_weights(self):
        samples = [self.values, dict(self.values, body_length_cm=95, shoulder_height_cm=40,
                                    body_width_cm=28, head_length_cm=30, tail_length_cm=50)]
        for values in samples:
            mesh, anatomy = _construction(self.provider.dimensions(values))
            rows = self.provider.skin_weights(mesh, values)[0].vertices
            for region in anatomy.regions:
                if region.name in ('torso', 'head', 'tail'):
                    for i in region.vertex_indices:
                        self.assertFalse(any(w.bone_name.endswith(('.left', '.right')) for w in rows[i]))

    def test_attachment_weights_are_local_blended_and_position_independent(self):
        from object_core.providers.quadruped_rigging import _attachment_weights
        attached = _attachment_weights(self.mesh, self.anatomy, 4)
        rows = self.provider.skin_weights(self.mesh, self.values)[0].vertices
        for connection in self.anatomy.connections:
            region = connection.regions[1]
            if not region.startswith('leg.'):
                continue
            chain = next(c for c in self.anatomy.chains if c.name == region)
            root, limb = connection.boundaries
            for i in root:
                self.assertEqual([(chain.parent_bone, 1)], [(w.bone_name, w.weight) for w in rows[i]])
            for i in limb:
                self.assertEqual({chain.parent_bone, chain.bones[0]}, {w.bone_name for w in rows[i]})
            amounts = {w.weight for row in attached.values() for w in row if w.bone_name == chain.bones[0]}
            self.assertGreater(len(amounts), 2)
            self.assertTrue(all(0 < w < 1 for w in amounts))
        moved = self.provider.semantic_mesh(self.mesh, self.values, (
            SemanticOperation('scale', 'leg.front.left', (('offset_x', 80), ('offset_y', -70))),))
        self.assertEqual(attached, _attachment_weights(moved, self.anatomy, 4))

    def test_missing_attachment_boundaries_are_rejected(self):
        from dataclasses import replace
        from object_core.providers.quadruped_rigging import _attachment_weights
        connection = replace(self.anatomy.connections[0], boundaries=((), ()))
        anatomy = replace(self.anatomy, connections=(connection,) + self.anatomy.connections[1:])
        with self.assertRaisesRegex(ValueError, 'boundary loops'):
            _attachment_weights(self.mesh, anatomy, 4)

    def test_paw_contact_is_local_monotone_and_grounded_at_parameter_corners(self):
        from itertools import product
        from object_core.providers.quadruped_anatomy import CanineRecipe
        from object_core.providers.quadruped_geometry import _ground_paw_surfaces
        samples = [self.values, dict(self.values, body_length_cm=95, shoulder_height_cm=40,
                                    body_width_cm=28, head_length_cm=30, tail_length_cm=50)]
        samples += [{p.key: getattr(p, endpoint) for p, endpoint in zip(self.provider.parameters, ends)}
                    for ends in product(('minimum', 'maximum'), repeat=len(self.provider.parameters))]
        for values in samples:
            with self.subTest(values=values):
                cage, anatomy = _build_quadruped_cage(CanineRecipe().resolve(self.provider.dimensions(values)))
                raw, anatomy = refine_canine_surface(cage, anatomy)
                mesh, resolved = _construction(self.provider.dimensions(values))
                before, after = raw.parts[0].vertices, mesh.parts[0].vertices
                points = {p.name: p.position for p in anatomy.landmarks}
                self.assertEqual(raw.parts[0].faces, mesh.parts[0].faces)
                self.assertEqual(anatomy.regions, resolved.regions)
                self.assertEqual(anatomy.connections, resolved.connections)
                changed_allowed = set()
                for region in anatomy.regions:
                    if not region.name.startswith('leg.'):
                        continue
                    suffix = region.name[4:]
                    upper = points[('ankle.' if suffix.startswith('front.') else 'hock.') + suffix][2]
                    ground = points['ground.' + suffix][2]
                    self.assertAlmostEqual(min(after[i][2] for i in region.vertex_indices), ground)
                    ordered = sorted(region.vertex_indices, key=lambda i: before[i][2])
                    # Adjacent source heights can differ by a single floating-point ULP.
                    self.assertTrue(all(after[a][2] <= after[b][2] + 1e-12
                                        for a, b in zip(ordered, ordered[1:])))
                    changed_allowed.update(i for i in region.vertex_indices if before[i][2] < upper)
                for i, (a, b) in enumerate(zip(before, after)):
                    self.assertEqual(a[:2], b[:2])
                    if i not in changed_allowed:
                        self.assertEqual(a, b)
                self.assertEqual(after, _ground_paw_surfaces(after, resolved))

    def test_modify_can_lift_grounded_paw_without_regrounding(self):
        region = next(r for r in self.anatomy.regions if r.name == 'leg.front.left')
        moved = self.provider.semantic_mesh(self.mesh, self.values, (
            SemanticOperation('scale', region.name, (('offset_z', 5),)),))
        self.assertAlmostEqual(min(moved.parts[0].vertices[i][2] for i in region.vertex_indices), 5)
