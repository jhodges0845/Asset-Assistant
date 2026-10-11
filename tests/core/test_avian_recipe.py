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

    def test_recipe2_preserves_mesh_clips_and_nonwing_rest_bones(self):
        baseline = json.loads((Path(__file__).parents[1] / 'fixtures/avian_recipe1_baseline.json').read_text())
        for sample in baseline['samples']:
            with self.subTest(sample=sample['sample']):
                values = sample['parameters']
                mesh = self.provider.mesh(values)
                skeleton = self.provider.skeleton(values)
                data = {'mesh': mesh}
                data.update({name: getattr(self.provider, name)(2.0, 1.0)
                             for name in ('idle', 'locomotion', 'flight')})
                self.assertEqual({k: sample['portable_fingerprints'][k] for k in data},
                                 {k: portable_fingerprint(v) for k, v in data.items()})
                for bone in skeleton.bones:
                    if not bone.name.startswith('wing.'):
                        self.assertEqual(sample['nonwing_bones'][bone.name],
                                         json.loads(json.dumps(asdict(bone))))
                self.assertEqual(sample['bones'], len(skeleton.bones))

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

    def test_invalid_surface_profiles_and_landmark_references_are_rejected(self):
        tube = self.anatomy.tubes[0]
        for values in ((0,) * len(tube.widths), (float('nan'),) * len(tube.widths), (1,)):
            with self.assertRaises(ValueError):
                replace(tube, widths=values)
        bad = replace(tube, landmarks=('unknown',) + tube.landmarks[1:])
        with self.assertRaisesRegex(ValueError, 'unknown landmark'):
            replace(self.anatomy, tubes=(bad,) + self.anatomy.tubes[1:])


if __name__ == '__main__':
    unittest.main()
