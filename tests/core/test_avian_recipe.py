# SPDX-License-Identifier: GPL-3.0-or-later
"""Avian migration parity and authored anatomy binding."""
from dataclasses import FrozenInstanceError, asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import unittest

from object_core.objects import get_provider
from object_core.providers.avian_anatomy import AvianRecipe
from object_core.providers.avian_geometry import _build_avian_mesh
from object_core.providers.avian_rigging import _build_avian_skeleton


def portable_fingerprint(value):
    # Ignore insignificant libm/platform rounding while retaining topology,
    # names, hierarchy, UVs, weights and clip data in the parity check.
    def rounded(item):
        if isinstance(item, float):
            return round(item, 9) if round(item, 9) else 0.0
        if isinstance(item, dict):
            return {k: rounded(v) for k, v in item.items()}
        if isinstance(item, list):
            return [rounded(v) for v in item]
        return item
    data = rounded(json.loads(json.dumps(value, default=asdict)))
    return sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class AvianRecipeTests(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider('avian')
        self.values = {p.key: p.default for p in self.provider.parameters}
        self.anatomy = AvianRecipe().resolve(self.provider.dimensions(self.values))

    def test_preserves_clips_and_axial_rest_shape(self):
        baseline = json.loads((Path(__file__).parents[1] / 'fixtures/avian_recipe1_baseline.json').read_text())
        for sample in baseline['samples']:
            with self.subTest(sample=sample['sample']):
                values = sample['parameters']
                mesh = self.provider.mesh(values)
                skeleton = self.provider.skeleton(values)
                data = {}
                data.update({name: getattr(self.provider, name)(2.0, 1.0)
                             for name in ('flight',)})
                self.assertEqual({k: sample['portable_fingerprints'][k] for k in data},
                                 {k: portable_fingerprint({'duration':v.duration, 'tracks':v.tracks}) for k, v in data.items()})
                lift = skeleton.bones[0].head[2] - sample['nonwing_bones']['root']['head'][2]
                for bone in skeleton.bones:
                    if not bone.name.startswith(('wing.', 'leg.', 'foot.')):
                        expected = sample['nonwing_bones'][bone.name]
                        self.assertEqual(bone.parent, expected['parent'])
                        for endpoint in ('head', 'tail'):
                            for axis in range(3):
                                self.assertAlmostEqual(getattr(bone, endpoint)[axis],
                                    expected[endpoint][axis] + (lift if axis == 2 else 0))
                self.assertEqual(sample['bones'], len(skeleton.bones))

    def test_authored_foot_patch_keeps_material_ownership_after_vertex_edits(self):
        mesh = self.provider.mesh(self.values)
        anatomy = self.provider.anatomy(self.values)
        part = mesh.parts[0]
        moved = replace(mesh, parts=(replace(part, vertices=tuple(
            (-x, y+30, z+10) for x,y,z in part.vertices)),))
        for candidate in (mesh, moved):
            weights = self.provider.skin_weights(candidate,self.values)[0]
            for region in anatomy.regions:
                if region.name.startswith('leg.'):
                    foot = 'foot.' + region.name.rsplit('.',1)[1]
                    for i in region.vertex_indices[24:]:
                        self.assertEqual(len(weights.vertices[i]),1)
                        self.assertEqual(weights.vertices[i][0].bone_name,foot)
                        self.assertEqual(weights.vertices[i][0].weight,1.)

    def test_shoulder_bridge_faces_are_reflected_with_matching_winding(self):
        from scripts.anatomy_baseline import SAMPLES
        def cyclic(face):
            return min(face[i:]+face[:i] for i in range(len(face)))
        for values in (self.values, SAMPLES['avian']):
            part = self.provider.mesh(values).parts[0]
            anatomy = self.provider.anatomy(values)
            connections = [next(c for c in anatomy.connections if c.regions == ('body',name))
                           for name in ('wing.left','wing.right')]
            boundaries = [set(i for boundary in c.boundaries for i in boundary) for c in connections]
            mapping = {}
            for i in boundaries[1]:
                x,y,z = part.vertices[i]
                j = min(boundaries[0],key=lambda j:sum((a-b)**2 for a,b in zip((-x,y,z),part.vertices[j])))
                self.assertLess(sum((a-b)**2 for a,b in zip((-x,y,z),part.vertices[j])),1e-12)
                mapping[i] = j
            self.assertEqual(len(set(mapping.values())),len(mapping))
            def bridges(connection):
                root,ring = map(set,connection.boundaries)
                return [f for f in part.faces if root.intersection(f) and ring.intersection(f)]
            self.assertEqual({cyclic(f) for f in bridges(connections[0])},
                             {cyclic(tuple(mapping[i] for i in reversed(f))) for f in bridges(connections[1])})

    def test_resolution_is_immutable_deterministic_and_parameter_complete(self):
        self.assertEqual(self.anatomy, AvianRecipe().resolve(self.provider.dimensions(dict(reversed(list(self.values.items()))))))
        self.assertEqual(dict(self.anatomy.parameters), self.values)
        self.assertIsInstance(hash(self.anatomy), int)
        with self.assertRaises(FrozenInstanceError):
            self.anatomy.recipe_version = 'changed'
        for field in self.provider.parameters:
            changed = dict(self.values, **{field.key: field.default + 1})
            self.assertNotEqual(self.anatomy, AvianRecipe().resolve(self.provider.dimensions(changed)))

    def test_regions_partition_vertices_and_boundaries_have_real_bridges(self):
        mesh, anatomy = _build_avian_mesh(self.anatomy)
        self.assertEqual(anatomy, self.provider.anatomy(self.values))
        anatomy.validate_mesh(mesh)
        owned = [i for r in anatomy.regions for i in r.vertex_indices]
        self.assertEqual(sorted(owned), list(range(mesh.vertex_count)))
        regions = {r.name: set(r.vertex_indices) for r in anatomy.regions}
        for connection in anatomy.connections:
            root, ring = map(set, connection.boundaries)
            self.assertEqual((len(root), len(ring)), (4, 8))
            self.assertLessEqual(root, regions[connection.regions[0]])
            self.assertLessEqual(ring, regions[connection.regions[1]])
            bridges = [f for f in mesh.parts[0].faces if root.intersection(f) and ring.intersection(f)]
            self.assertEqual(len(bridges), 8)

    def test_attachments_stay_on_their_side_and_mesh_is_closed_and_oriented(self):
        from collections import Counter
        for values in (self.values, dict(self.values, body_width_cm=22, wingspan_cm=140,
                                         body_length_cm=55, body_height_cm=28, tail_length_cm=35)):
            mesh = self.provider.mesh(values)
            anatomy = self.provider.anatomy(values)
            part = mesh.parts[0]
            for connection in anatomy.connections:
                sign = -1 if connection.regions[1].endswith('.left') else 1
                self.assertTrue(all(sign * part.vertices[i][0] >= -1e-10
                                    for i in connection.boundaries[0]))
            edges = Counter((a, b) for face in part.faces
                            for a, b in zip(face, face[1:] + face[:1]))
            self.assertTrue(all(count == 1 and edges[b, a] == 1
                                for (a, b), count in edges.items()))

    def test_resolved_surface_landmark_drives_constructor(self):
        name = self.anatomy.tubes[1].landmarks[2]
        moved = replace(self.anatomy, landmarks=tuple(
            replace(p, position=(p.position[0], p.position[1] + 2, p.position[2]))
            if p.name == name else p for p in self.anatomy.landmarks))
        mesh, bound = _build_avian_mesh(moved)
        indices = next(r.vertex_indices for r in bound.regions if r.name == 'wing.left')[16:24]
        center = tuple(sum(mesh.parts[0].vertices[i][axis] for i in indices) / 8 for axis in range(3))
        expected = next(p.position for p in moved.landmarks if p.name == name)
        for a, b in zip(center, expected):
            self.assertAlmostEqual(a, b)
        self.assertEqual(mesh.parts[0].faces, self.provider.mesh(self.values).parts[0].faces)
        bones = {b.name: b for b in _build_avian_skeleton(moved).bones}
        self.assertEqual(bones['wing.upper.left'].tail, expected)
        self.assertEqual(bones['wing.lower.left'].head, expected)

    def test_resolved_joint_drives_both_adjacent_bones(self):
        chain = next(c for c in self.anatomy.chains if c.name == 'wing.left')
        name = chain.landmarks[1]
        moved = replace(self.anatomy, landmarks=tuple(
            replace(p, position=(p.position[0], p.position[1], p.position[2] + 2))
            if p.name == name else p for p in self.anatomy.landmarks))
        bones = {b.name: b for b in _build_avian_skeleton(moved).bones}
        expected = next(p.position for p in moved.landmarks if p.name == name)
        self.assertEqual(bones['wing.upper.left'].tail, expected)
        self.assertEqual(bones['wing.lower.left'].head, expected)
        self.assertEqual(chain.motion_role, 'flight')

    def test_wing_joint_paths_share_surface_landmarks_across_shapes(self):
        for width, span, height in ((16, 90, 20), (22, 140, 28), (5, 20, 6), (60, 320, 70)):
            values = dict(self.values, body_width_cm=width, wingspan_cm=span, body_height_cm=height)
            anatomy = self.provider.anatomy(values)
            for side in ('left', 'right'):
                name = 'wing.' + side
                tube = next(t for t in anatomy.tubes if t.name == name)
                chain = next(c for c in anatomy.chains if c.name == name)
                self.assertEqual(chain.landmarks, tuple(tube.landmarks[i] for i in (0, 2, 4)))

    def test_leg_surface_and_rig_share_descending_landmarks(self):
        for side in ('left', 'right'):
            tube = next(t for t in self.anatomy.tubes if t.name == 'leg.' + side)
            chain = next(c for c in self.anatomy.chains if c.name == tube.name)
            self.assertEqual(chain.landmarks, tuple(tube.landmarks[i] for i in (0, 2, 3, 4)))
            points = {p.name: p.position for p in self.anatomy.landmarks}
            heights = [points[n][2] for n in chain.landmarks]
            self.assertTrue(all(a > b for a, b in zip(heights, heights[1:])))
            bones = {b.name: b for b in _build_avian_skeleton(self.anatomy).bones}
            for i, name in enumerate(chain.bones):
                self.assertEqual(bones[name].head, points[chain.landmarks[i]])
                self.assertEqual(bones[name].tail, points[chain.landmarks[i + 1]])

    def test_support_chain_has_room_below_raised_torso(self):
        points = {p.name: p.position for p in self.anatomy.landmarks}
        for side in ('left', 'right'):
            tube = next(t for t in self.anatomy.tubes if t.name == 'leg.' + side)
            hip, knee, ankle = (points[tube.landmarks[i]] for i in (0, 2, 3))
            self.assertGreater(hip[2], self.values['body_height_cm'] * .30)
            self.assertGreater(knee[2] - ankle[2], self.values['body_height_cm'] * .15)
            self.assertLess(ankle[2], self.values['body_height_cm'] * .05)

    def test_feet_have_finite_grounded_soles_without_penetration(self):
        for values in (self.values, dict(self.values, body_length_cm=55, body_width_cm=22,
                                         body_height_cm=28, wingspan_cm=140, tail_length_cm=35)):
            mesh = self.provider.mesh(values)
            anatomy = self.provider.anatomy(values)
            self.assertGreaterEqual(min(v[2] for v in mesh.parts[0].vertices), 0)
            for region in anatomy.regions:
                if region.name.startswith('leg.'):
                    sole = [mesh.parts[0].vertices[i] for i in region.vertex_indices[24:]
                            if abs(mesh.parts[0].vertices[i][2]) < 1e-9]
                    self.assertEqual(len(sole), 15)
                    self.assertGreater(max(v[0] for v in sole) - min(v[0] for v in sole), .5)
                    self.assertGreater(max(v[1] for v in sole) - min(v[1] for v in sole), 1)

    def test_forward_toes_are_separated_and_tapered(self):
        mesh = self.provider.mesh(self.values)
        anatomy = self.provider.anatomy(self.values)
        for region in anatomy.regions:
            if not region.name.startswith('leg.'):
                continue
            ends = [[mesh.parts[0].vertices[i] for i in region.vertex_indices[40 + k * 4:44 + k * 4]]
                    for k in range(3)]
            self.assertTrue(all(len(end) == 4 for end in ends))
            self.assertGreater(min(p[0] for p in ends[0]), max(p[0] for p in ends[1]))
            self.assertGreater(min(p[0] for p in ends[1]), max(p[0] for p in ends[2]))
            self.assertGreater(ends[1][0][1], ends[0][0][1])
            self.assertAlmostEqual(ends[0][0][1], ends[2][0][1])
            self.assertTrue(all(min(p[2] for p in end) == 0 for end in ends))

    def test_rear_toes_extend_behind_ankles_with_ground_contact(self):
        mesh = self.provider.mesh(self.values)
        anatomy = self.provider.anatomy(self.values)
        points = {p.name: p.position for p in anatomy.landmarks}
        for region in anatomy.regions:
            if not region.name.startswith('leg.'):
                continue
            tube = next(t for t in anatomy.tubes if t.name == region.name)
            ankle = points[tube.landmarks[3]]
            tip = [mesh.parts[0].vertices[i] for i in region.vertex_indices[56:60]]
            self.assertTrue(all(p[1] < ankle[1] for p in tip))
            self.assertEqual(sum(p[2] == 0 for p in tip), 2)
            self.assertAlmostEqual(ankle[1] - tip[0][1], tube.rear_toe_length)
            self.assertGreater(max(p[0] for p in tip) - min(p[0] for p in tip), 0)
        for bad in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                replace(tube, rear_toe_length=bad)
        with self.assertRaises(TypeError):
            replace(tube, rear_toe_length=True)

    def test_claws_taper_above_ground_in_each_toe_direction(self):
        mesh = self.provider.mesh(self.values)
        anatomy = self.provider.anatomy(self.values)
        for region in anatomy.regions:
            if not region.name.startswith('leg.'):
                continue
            for digit, root_start in enumerate((40, 44, 48, 56)):
                root = [mesh.parts[0].vertices[i] for i in region.vertex_indices[root_start:root_start + 4]]
                claw = [mesh.parts[0].vertices[i] for i in region.vertex_indices[60 + digit * 5:65 + digit * 5]]
                self.assertEqual(len(claw), 5)
                self.assertTrue(all(p[2] > 0 for p in claw))
                direction = 1 if digit < 3 else -1
                self.assertGreater(direction * (claw[-1][1] - root[0][1]), 0)
                self.assertLess(max(p[0] for p in claw) - min(p[0] for p in claw),
                                max(p[0] for p in root) - min(p[0] for p in root))
        tube = anatomy.tubes[-1]
        for bad in (-1, float('nan')):
            with self.assertRaises(ValueError):
                replace(tube, claw_length=bad)

    def test_invalid_surface_profiles_and_landmark_references_are_rejected(self):
        tube = self.anatomy.tubes[0]
        for bad in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                replace(tube, toe_length=bad)
        with self.assertRaises(TypeError):
            replace(tube, toe_length=True)
        for values in ((0,) * len(tube.widths), (float('nan'),) * len(tube.widths), (1,)):
            with self.assertRaises(ValueError):
                replace(tube, widths=values)
        bad = replace(tube, landmarks=('unknown',) + tube.landmarks[1:])
        with self.assertRaisesRegex(ValueError, 'unknown landmark'):
            replace(self.anatomy, tubes=(bad,) + self.anatomy.tubes[1:])


if __name__ == '__main__':
    unittest.main()
