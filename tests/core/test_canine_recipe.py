# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from dataclasses import replace

from object_core.models import MeshPart, ObjectMesh
from object_core.modification import AssetSnapshot, ModificationRequest, SemanticOperation, plan_modification
from object_core.objects import get_provider
from object_core.providers.quadruped import _construction
from object_core.providers.quadruped_geometry import _build_quadruped_mesh
from object_core.providers.quadruped_rigging import _build_quadruped_skeleton
from object_core.providers.quadruped_anatomy import CanineRecipe


class CanineRecipeTests(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider('quadruped')
        self.values = {p.key: p.default for p in self.provider.parameters}
        self.mesh, self.anatomy = _construction(self.provider.dimensions(self.values))
        self.regions = {r.name: set(r.vertex_indices) for r in self.anatomy.regions}

    def operation(self, target, operation='scale', **args):
        return SemanticOperation(operation, target, tuple(args.items()))

    def test_complete_recipe_caches_and_binds_all_chains_and_limbs(self):
        cached = _construction(dict(reversed(tuple(self.provider.dimensions(self.values).items()))))
        self.assertIs(cached[1], self.anatomy)
        self.assertEqual('canine', self.anatomy.recipe_id)
        self.assertEqual(17, sum(len(c.bones) for c in self.anatomy.chains))
        bones = {b.name: b for b in self.provider.skeleton(self.values).bones}
        points = {p.name: p.position for p in self.anatomy.landmarks}
        for chain in self.anatomy.chains:
            for i, name in enumerate(chain.bones):
                self.assertEqual(bones[name].head, points[chain.landmarks[i]])
                self.assertEqual(bones[name].tail, points[chain.landmarks[i + 1]])
        owned = set()
        for connection in self.anatomy.connections:
            region = self.regions[connection.regions[1]]
            self.assertFalse(owned.intersection(region))
            owned.update(region)
            self.assertEqual(64 if '.hind.' in connection.regions[1] else 48, len(region))
            root, ring = connection.boundaries
            self.assertEqual((4, 8), (len(root), len(ring)))
            self.assertTrue(set(root) <= self.regions['torso'])
            self.assertTrue(set(ring) <= region)
        self.assertEqual(4, len(self.anatomy.connections))
        self.assertTrue(all(self.regions.values()))

    def test_hind_landmark_drives_mesh_and_rig(self):
        changed = replace(self.anatomy, landmarks=tuple(
            replace(p, position=(p.position[0], p.position[1] + 2, p.position[2]))
            if p.name == 'knee.hind.right' else p for p in self.anatomy.landmarks))
        mesh, anatomy = _build_quadruped_mesh(changed)
        bones = {b.name: b for b in _build_quadruped_skeleton(changed).bones}
        target = next(p.position for p in changed.landmarks if p.name == 'knee.hind.right')
        indices = next(r.vertex_indices for r in anatomy.regions if r.name == 'leg.hind.right')[16:24]
        center = tuple(sum(mesh.parts[0].vertices[i][axis] for i in indices) / len(indices) for axis in range(3))
        for a, b in zip(center, target):
            self.assertAlmostEqual(a, b)
        self.assertEqual(target, bones['hind_upper.right'].tail)
        self.assertEqual(target, bones['hind_lower.right'].head)

    def test_hock_landmark_drives_surface_and_distal_bone(self):
        changed = replace(self.anatomy, landmarks=tuple(
            replace(p, position=(p.position[0], p.position[1] - 2, p.position[2] + 1))
            if p.name == 'hock.hind.left' else p for p in self.anatomy.landmarks))
        mesh, anatomy = _build_quadruped_mesh(changed)
        bones = {b.name: b for b in _build_quadruped_skeleton(changed).bones}
        target = next(p.position for p in changed.landmarks if p.name == 'hock.hind.left')
        indices = next(r.vertex_indices for r in anatomy.regions if r.name == 'leg.hind.left')[32:40]
        for axis in range(3):
            self.assertAlmostEqual(target[axis], sum(mesh.parts[0].vertices[i][axis] for i in indices) / 8)
        self.assertEqual(target, bones['hind_lower.left'].tail)
        self.assertEqual(target, bones['hind_pastern.left'].head)
        self.assertEqual('hind_lower.left', bones['hind_pastern.left'].parent)

    def test_hind_stance_and_connected_topology_across_parameter_corners(self):
        from collections import Counter
        from itertools import product
        for endpoints in product(('minimum', 'maximum'), repeat=len(self.provider.parameters)):
            values = {p.key: getattr(p, endpoint) for p, endpoint in zip(self.provider.parameters, endpoints)}
            with self.subTest(values=values):
                mesh, anatomy = _construction(self.provider.dimensions(values))
                points = {p.name: p.position for p in anatomy.landmarks}
                regions = {r.name: r.vertex_indices for r in anatomy.regions}
                for side in ('left', 'right'):
                    hip, knee, hock, paw = (points[n + '.hind.' + side] for n in ('hip', 'knee', 'hock', 'paw'))
                    self.assertGreater(knee[1], hip[1])
                    self.assertLess(hock[1], hip[1])
                    self.assertGreater(paw[1], hock[1])
                    self.assertTrue(hip[2] > knee[2] > hock[2] > paw[2] > 0)
                    self.assertGreater(min(mesh.parts[0].vertices[i][2] for i in regions['leg.hind.' + side]), 0)
                part = mesh.parts[0]
                directed = Counter((a, b) for face in part.faces for a, b in zip(face, face[1:] + face[:1]))
                self.assertTrue(all(n == 1 and directed[(b, a)] == 1 for (a, b), n in directed.items()))
                neighbors = {i: set() for i in range(len(part.vertices))}
                for a, b in directed:
                    neighbors[a].add(b)
                seen, pending = set(), [0]
                while pending:
                    current = pending.pop()
                    if current not in seen:
                        seen.add(current)
                        pending.extend(neighbors[current] - seen)
                self.assertEqual(len(part.vertices), len(seen))
                left = {tuple(round(c, 7) for c in (-part.vertices[i][0], *part.vertices[i][1:]))
                        for i in regions['leg.hind.left']}
                right = {tuple(round(c, 7) for c in part.vertices[i]) for i in regions['leg.hind.right']}
                self.assertEqual(left, right)
                # Edge winding alone cannot catch a 180-degree ring-frame flip.
                # Tube face normals must point away from their local centerline.
                for side in ('left', 'right'):
                    owned = regions['leg.hind.' + side]
                    rings = [owned[i:i + 8] for i in range(0, len(owned), 8)]
                    centers = [tuple(sum(part.vertices[i][k] for i in ring) / 8 for k in range(3))
                               for ring in rings]
                    for level in range(len(rings) - 1):
                        for segment in range(8):
                            nxt = (segment + 1) % 8
                            a, b, c, d = (part.vertices[i] for i in (
                                rings[level][segment], rings[level][nxt],
                                rings[level + 1][nxt], rings[level + 1][segment]))
                            u, v = (tuple(point[k] - a[k] for k in range(3)) for point in (b, d))
                            normal = (u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0])
                            radial = tuple((a[k] + b[k] + c[k] + d[k]) / 4
                                           - (centers[level][k] + centers[level + 1][k]) / 2 for k in range(3))
                            self.assertGreater(sum(normal[k] * radial[k] for k in range(3)), 0)

    def test_each_published_operation_changes_only_its_authored_region(self):
        for target, kind in self.provider.semantic_apply_capabilities:
            changed = self.provider.semantic_mesh(self.mesh, self.values, (self.operation(target, kind, offset_y=2),))
            self.assertEqual(self.mesh.parts[0].faces, changed.parts[0].faces)
            self.assertEqual(self.mesh.parts[0].uvs, changed.parts[0].uvs)
            for i, (a, b) in enumerate(zip(self.mesh.parts[0].vertices, changed.parts[0].vertices)):
                if i in self.regions[target]:
                    self.assertAlmostEqual(a[1] + 2, b[1])
                else:
                    self.assertEqual(a, b)

    def test_moved_limb_retains_semantic_and_skinning_side_ownership(self):
        target = 'leg.front.left'
        moved = self.provider.semantic_mesh(self.mesh, self.values, (self.operation(target, offset_x=80),))
        changed = self.provider.semantic_mesh(moved, self.values, (self.operation(target, offset_z=2),))
        weights = self.provider.skin_weights(changed, self.values)[0]
        for i in self.regions[target]:
            self.assertAlmostEqual(moved.parts[0].vertices[i][2] + 2, changed.parts[0].vertices[i][2])
            self.assertFalse(any(w.bone_name.endswith('.right') for w in weights.vertices[i]))
        self.assertTrue(all(sum(w.weight for w in v) > .99999 for v in weights.vertices))

    def test_limb_weights_stay_in_authored_chain_after_large_edits(self):
        # Reproduce a front leg moved onto the hind leg, then challenge both
        # sides/families near unrelated head, tail and opposite-side bones.
        for region in (r for r in self.anatomy.regions if r.name.startswith('leg.')):
            chain = next(c for c in self.anatomy.chains if c.name == region.name)
            connection = next(c for c in self.anatomy.connections if c.regions[1] == region.name)
            boundary = set(connection.boundaries[1])
            for offset in ((0, -44.8, 0), (80, 44.8, 35), (0, -80, 45)):
                with self.subTest(region=region.name, offset=offset):
                    moved = self.provider.semantic_mesh(self.mesh, self.values, (
                        self.operation(region.name, **dict(zip(('offset_x', 'offset_y', 'offset_z'), offset))),))
                    weights = self.provider.skin_weights(moved, self.values)[0]
                    for i in region.vertex_indices:
                        allowed = set(chain.bones)
                        if i in boundary:
                            allowed.add(chain.parent_bone)
                        self.assertTrue({w.bone_name for w in weights.vertices[i]} <= allowed)
                        self.assertAlmostEqual(1, sum(w.weight for w in weights.vertices[i]))

    def test_attachment_can_blend_to_parent_and_distal_limb_cannot(self):
        weights = self.provider.skin_weights(self.mesh, self.values)[0]
        for connection in self.anatomy.connections:
            region = connection.regions[1]
            chain = next(c for c in self.anatomy.chains if c.name == region)
            boundary = set(connection.boundaries[1])
            self.assertTrue(any(w.bone_name == chain.parent_bone
                                for i in boundary for w in weights.vertices[i]))
            for i in self.regions[region] - boundary:
                self.assertTrue({w.bone_name for w in weights.vertices[i]} <= set(chain.bones))

    def test_chain_local_weights_are_deterministic_at_parameter_limits(self):
        from object_core.providers.quadruped_rigging import generate_quadruped_skin_weights
        for endpoint in ('minimum', 'maximum'):
            values = {p.key: getattr(p, endpoint) for p in self.provider.parameters}
            mesh, anatomy = _construction(self.provider.dimensions(values))
            skeleton = self.provider.skeleton(values)
            for limit in (1, 2, 4):
                weights = generate_quadruped_skin_weights(mesh, skeleton, anatomy=anatomy, max_influences=limit)
                self.assertEqual(weights, generate_quadruped_skin_weights(
                    mesh, skeleton, anatomy=anatomy, max_influences=limit))
                for vertex in weights[0].vertices:
                    self.assertTrue(1 <= len(vertex) <= limit)
                    self.assertAlmostEqual(1, sum(w.weight for w in vertex))
                    self.assertTrue(all(w.weight > 0 for w in vertex))
        for invalid in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                generate_quadruped_skin_weights(self.mesh, self.provider.skeleton(self.values),
                                                anatomy=self.anatomy, max_influences=invalid)

    def test_named_profiles_are_useful_and_unknown_profiles_fail(self):
        for target, profile in (('chest', 'broad'), ('waist', 'tucked'), ('head', 'broad'),
                                ('muzzle', 'long'), ('tail', 'long'), ('leg.hind.left', 'sturdy')):
            changed = self.provider.semantic_mesh(self.mesh, self.values, (
                self.operation(target, 'shape', profile=profile),))
            self.assertNotEqual(self.mesh.parts[0].vertices, changed.parts[0].vertices)
        with self.assertRaises(ValueError):
            self.provider.semantic_mesh(self.mesh, self.values, (self.operation('head', 'shape', profile='unknown'),))

    def test_invalid_numbers_and_unimplemented_targets_are_rejected(self):
        for arguments in ({'factor': 10}, {'offset_x': float('nan')}, {'x': True}):
            with self.assertRaises((ValueError, TypeError)):
                self.provider.semantic_mesh(self.mesh, self.values, (self.operation('head', **arguments),))
        for target in ('ear.left', 'coat', 'missing'):
            self.assertNotIn((target, 'shape'), self.provider.semantic_apply_capabilities)
            with self.assertRaises(ValueError):
                self.provider.semantic_mesh(self.mesh, self.values, (self.operation(target),))

    def test_topology_changes_are_rejected_for_semantics_and_weights(self):
        part = self.mesh.parts[0]
        bad = ObjectMesh((MeshPart(part.name, part.vertices, tuple(reversed(part.faces))),))
        with self.assertRaisesRegex(ValueError, 'authored surface topology'):
            self.provider.semantic_mesh(bad, self.values, (self.operation('head'),))
        with self.assertRaisesRegex(ValueError, 'authored surface topology'):
            self.provider.skin_weights(bad, self.values)

    def test_planner_allows_real_regions_and_blocks_unimplemented_ears(self):
        snapshot = AssetSnapshot(asset_id='canine', provider_key='quadruped', provider_label='Quadruped',
                                 parameters=tuple(self.values.items()), owns_geometry=True)
        for target, accepted in (('chest', True), ('waist', True), ('leg.front.left', True), ('ear.left', False)):
            plan = plan_modification(snapshot, ModificationRequest(semantic_operations=(self.operation(target),)))
            self.assertEqual(accepted, plan.safe_to_apply)


if __name__ == '__main__':
    unittest.main()
