# SPDX-License-Identifier: GPL-3.0-or-later
"""Wing ownership must survive posing and topology-preserving artist edits."""
from dataclasses import replace
import unittest

from object_core.objects import get_provider
from object_core.models import ObjectMesh
from object_core.providers.avian_rigging import generate_avian_skin_weights


class AvianWeightOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider('avian')
        self.values = {p.key: p.default for p in self.provider.parameters}
        self.mesh = self.provider.mesh(self.values)
        self.anatomy = self.provider.anatomy(self.values)

    def test_wing_influence_is_confined_to_authored_wings(self):
        weights = self.provider.skin_weights(self.mesh, self.values)[0].vertices
        for region in self.anatomy.regions:
            for i in region.vertex_indices:
                names = {w.bone_name for w in weights[i]}
                if region.name.startswith('wing.'):
                    side = region.name.split('.')[1]
                    self.assertLessEqual(names, {'spine', 'wing.upper.' + side, 'wing.lower.' + side})
                else:
                    self.assertFalse(any(n.startswith('wing.') for n in names))
                self.assertAlmostEqual(sum(w.weight for w in weights[i]), 1)

    def test_edited_wing_keeps_ownership_after_crossing_body_and_midline(self):
        owned = set(next(r.vertex_indices for r in self.anatomy.regions if r.name == 'wing.left'))
        part = self.mesh.parts[0]
        vertices = tuple((x + 100, y - 50, z - 30) if i in owned else (x, y, z)
                         for i, (x, y, z) in enumerate(part.vertices))
        edited = ObjectMesh((replace(part, vertices=vertices),))
        weights = self.provider.skin_weights(edited, self.values)[0].vertices
        original = self.provider.skin_weights(self.mesh, self.values)[0].vertices
        for i, influences in enumerate(weights):
            if i in owned:
                self.assertTrue(all(w.bone_name in ('spine', 'wing.upper.left', 'wing.lower.left')
                                    for w in influences))
            else:
                self.assertEqual(influences, original[i])

    def test_attachment_keeps_parent_blend_without_distal_parent_leakage(self):
        weights = self.provider.skin_weights(self.mesh, self.values)[0].vertices
        for connection in self.anatomy.connections:
            if not connection.regions[1].startswith('wing.'):
                continue
            for i in connection.boundaries[0]:
                self.assertEqual([(w.bone_name, w.weight) for w in weights[i]], [('spine', 1)])
            for i in connection.boundaries[1]:
                names = {w.bone_name: w.weight for w in weights[i]}
                self.assertGreater(names['spine'], 0)
                self.assertLess(names['spine'], 1)
            region = next(r for r in self.anatomy.regions if r.name == connection.regions[1])
            for i in region.vertex_indices[-8:]:
                self.assertNotIn('spine', {w.bone_name for w in weights[i]})

    def test_changed_topology_is_rejected_instead_of_guessing_ownership(self):
        part = self.mesh.parts[0]
        for altered in (replace(part, faces=part.faces[:-1], uvs=part.uvs[:-1]),
                        replace(part, name='renamed')):
            with self.assertRaisesRegex(ValueError, 'authored topology'):
                self.provider.skin_weights(ObjectMesh((altered,)), self.values)

    def test_influence_limit_is_validated_and_respected(self):
        skeleton = self.provider.skeleton(self.values)
        for bad in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                generate_avian_skin_weights(self.mesh, skeleton, anatomy=self.anatomy, max_influences=bad)
        for limit in (1, 2, 4):
            weights = generate_avian_skin_weights(self.mesh, skeleton, anatomy=self.anatomy, max_influences=limit)
            for influences in weights[0].vertices:
                self.assertLessEqual(len(influences), limit)
                self.assertAlmostEqual(sum(w.weight for w in influences), 1)
