# SPDX-License-Identifier: GPL-3.0-or-later
"""The proximal parent blend ends before distal limb ownership begins."""
import unittest
from collections import deque

from object_core.objects import get_provider
from object_core.modification import SemanticOperation
from object_core.providers.quadruped import _construction
from object_core.providers.quadruped_rigging import generate_quadruped_skin_weights


class CanineAttachmentCollarTests(unittest.TestCase):
    def test_parent_fades_through_three_interior_rows_and_preserves_distal_weights(self):
        provider = get_provider('quadruped')
        defaults = {p.key: p.default for p in provider.parameters}
        for values in (defaults, dict(defaults, body_length_cm=95, shoulder_height_cm=40,
                                     body_width_cm=28, head_length_cm=30, tail_length_cm=50)):
            mesh, anatomy = _construction(provider.dimensions(values))
            skeleton = provider.skeleton(values)
            part = mesh.parts[0]
            neighbors = [set() for _ in part.vertices]
            for face in part.faces:
                for a, b in zip(face, face[1:] + face[:1]):
                    neighbors[a].add(b)
                    neighbors[b].add(a)
            rows = provider.skin_weights(mesh, values)[0].vertices
            from object_core.providers.quadruped_rigging import _weights_for_vertex
            for connection in anatomy.connections:
                name = connection.regions[1]
                if not name.startswith('leg.'):
                    continue
                chain = next(c for c in anatomy.chains if c.name == name)
                owned = set(next(r.vertex_indices for r in anatomy.regions if r.name == name))
                depths = dict.fromkeys(connection.boundaries[1], 0)
                queue = deque(depths)
                while queue:
                    i = queue.popleft()
                    for j in neighbors[i] & owned:
                        if j not in depths:
                            depths[j] = depths[i] + 1
                            queue.append(j)
                self.assertEqual(set(depths), owned)
                self.assertTrue({0, 1, 2, 3, 4} <= set(depths.values()))
                local = tuple(b for b in skeleton.bones if b.name in chain.bones)
                for i, depth in depths.items():
                    parent = next((w.weight for w in rows[i] if w.bone_name == chain.parent_bone), 0)
                    expected = {0: .25, 1: .2109375, 2: .125, 3: .0390625}.get(depth, 0)
                    self.assertAlmostEqual(parent, expected)
                    self.assertTrue({w.bone_name for w in rows[i]} <= set(chain.bones) | {chain.parent_bone})
                    if depth >= 4:
                        self.assertEqual(rows[i], _weights_for_vertex(part.vertices[i], local, 4))

    def test_parent_fade_survives_large_modify_edits_and_influence_limits(self):
        provider = get_provider('quadruped')
        values = {p.key: p.default for p in provider.parameters}
        mesh, anatomy = _construction(provider.dimensions(values))
        skeleton = provider.skeleton(values)
        moved = provider.semantic_mesh(mesh, values, (
            SemanticOperation('scale', 'leg.front.left', (('offset_x', 80), ('offset_y', -80))),))
        original = provider.skin_weights(mesh, values)[0].vertices
        for limit in (1, 2, 4):
            weights = generate_quadruped_skin_weights(moved, skeleton, anatomy=anatomy, max_influences=limit)
            self.assertEqual(weights, generate_quadruped_skin_weights(
                moved, skeleton, anatomy=anatomy, max_influences=limit))
            for i, row in enumerate(weights[0].vertices):
                self.assertLessEqual(len(row), limit)
                self.assertAlmostEqual(sum(w.weight for w in row), 1)
                self.assertTrue(all(0 < w.weight <= 1 for w in row))
                if limit == 4:
                    before = next((w.weight for w in original[i] if w.bone_name == 'spine'), 0)
                    after = next((w.weight for w in row if w.bone_name == 'spine'), 0)
                    self.assertAlmostEqual(before, after)

    def test_hind_soles_follow_pastern_without_lower_leg_shear(self):
        provider = get_provider('quadruped')
        defaults = {p.key: p.default for p in provider.parameters}
        for values in (defaults, dict(defaults, body_length_cm=95, shoulder_height_cm=40,
                                     body_width_cm=28, head_length_cm=30, tail_length_cm=50),
                       dict(defaults, body_length_cm=25, shoulder_height_cm=15, body_width_cm=55,
                            head_length_cm=8, tail_length_cm=5)):
            mesh, anatomy = _construction(provider.dimensions(values))
            weights = provider.skin_weights(mesh, values)[0].vertices
            for region in anatomy.regions:
                if not region.name.startswith('leg.hind.'):
                    continue
                sole = [i for i in region.vertex_indices if 0 <= mesh.parts[0].vertices[i][2] <= .1]
                self.assertTrue(sole)
                expected = 'hind_pastern.' + region.name.rsplit('.', 1)[1]
                for i in sole:
                    self.assertEqual([(w.bone_name, w.weight) for w in weights[i]], [(expected, 1.)])
