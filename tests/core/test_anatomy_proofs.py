# SPDX-License-Identifier: GPL-3.0-or-later
"""Behavioral evidence for a shared contract across two existing body plans."""
from dataclasses import replace
import unittest

from object_core.anatomy import ResolvedAnatomy
from object_core.models.mesh import MeshPart, ObjectMesh
from object_core.objects import get_provider
from object_core.providers.human import _human_anatomy, _neutral_surface_data
from object_core.providers.quadruped_anatomy import QuadrupedFrontRecipe
from object_core.providers.quadruped_geometry import _build_quadruped_mesh
from object_core.providers.quadruped_rigging import _build_quadruped_skeleton


def _defaults(provider):
    return {p.key: p.default for p in provider.parameters}


def _centroid(points):
    return tuple(sum(p[axis] for p in points) / len(points) for axis in range(3))


class AnatomyProofTests(unittest.TestCase):
    def assertPointAlmostEqual(self, first, second):
        for a, b in zip(first, second):
            self.assertAlmostEqual(a, b)

    def test_human_proof_retains_authored_ownership_and_bone_endpoints(self):
        provider = get_provider('human')
        neutral, authored = _neutral_surface_data()
        for values in (_defaults(provider), dict(height_cm=155, weight_kg=65, body_type='average')):
            anatomy = _human_anatomy(**values)
            self.assertIsInstance(anatomy, ResolvedAnatomy)
            self.assertEqual(anatomy, _human_anatomy(**values))
            mesh = provider.mesh(values)
            anatomy.validate_mesh(mesh)
            regions = {r.name: r for r in anatomy.regions}
            for side, indices in authored:
                self.assertEqual(tuple(sorted(indices)), regions['arm.' + side].vertex_indices)
            points = {p.name: p.position for p in anatomy.landmarks}
            bones = {b.name: b for b in provider.skeleton(values).bones}
            for chain in anatomy.chains:
                for index, name in enumerate(chain.bones):
                    self.assertEqual(bones[name].head, points[chain.landmarks[index]])
                    self.assertEqual(bones[name].tail, points[chain.landmarks[index + 1]])
        self.assertNotEqual(_human_anatomy(180, 95, 'average').landmarks,
                            _human_anatomy(155, 65, 'average').landmarks)

    def test_quadruped_proof_default_contrasting_and_boundaries(self):
        provider = get_provider('quadruped')
        samples = [_defaults(provider),
                   {p.key: p.minimum for p in provider.parameters},
                   {p.key: p.maximum for p in provider.parameters},
                   dict(body_length_cm=95, shoulder_height_cm=40, body_width_cm=28,
                        head_length_cm=30, tail_length_cm=50)]
        for values in samples:
            with self.subTest(values=values):
                dimensions = provider.dimensions(values)
                recipe = QuadrupedFrontRecipe()
                anatomy = recipe.resolve(dimensions)
                self.assertEqual(anatomy, recipe.resolve(dict(reversed(tuple(dimensions.items())))))
                mesh, resolved = _build_quadruped_mesh(dimensions, anatomy)
                skeleton = _build_quadruped_skeleton(dimensions, resolved)
                self.assertEqual(mesh, provider.mesh(values))
                self.assertEqual(skeleton, provider.skeleton(values))
                resolved.validate_mesh(mesh)
                points = {p.name: p.position for p in resolved.landmarks}
                bones = {b.name: b for b in skeleton.bones}
                for chain in resolved.chains:
                    for index, name in enumerate(chain.bones):
                        self.assertEqual(bones[name].head, points[chain.landmarks[index]])
                        self.assertEqual(bones[name].tail, points[chain.landmarks[index + 1]])
                self.assertNotEqual(points['ankle.front.left'], points['ground.front.left'])
                self.assertNotEqual(points['paw.front.left'], points['ground.front.left'])
                self.assertEqual(48, len(resolved.regions[1].vertex_indices))
                self.assertEqual('connected', resolved.connections[0].continuity)
                root, first_ring = resolved.connections[0].boundaries
                self.assertEqual((4, 8), (len(root), len(first_ring)))
                self.assertTrue(set(root) <= set(resolved.regions[0].vertex_indices))
                self.assertTrue(set(first_ring) <= set(resolved.regions[1].vertex_indices))
                # The declared attachment really has faces crossing its two boundaries.
                bridge = [f for f in mesh.parts[0].faces if set(f).intersection(root)
                          and set(f).intersection(first_ring)]
                self.assertEqual(8, len(bridge))

    def test_resolved_elbow_drives_both_geometry_and_rig(self):
        provider = get_provider('quadruped')
        dimensions = provider.dimensions(_defaults(provider))
        anatomy = QuadrupedFrontRecipe().resolve(dimensions)
        original, original_regions = _build_quadruped_mesh(dimensions, anatomy)
        changed = replace(anatomy, landmarks=tuple(
            replace(p, position=(p.position[0], p.position[1] + 3, p.position[2] + 2))
            if p.name == 'elbow.front.left' else p for p in anatomy.landmarks))
        mesh, regions = _build_quadruped_mesh(dimensions, changed)
        bones = {b.name: b for b in _build_quadruped_skeleton(dimensions, changed).bones}
        target = next(p.position for p in changed.landmarks if p.name == 'elbow.front.left')
        self.assertEqual(target, bones['fore_upper.left'].tail)
        self.assertEqual(target, bones['fore_lower.left'].head)
        # Third ring is the authored elbow, even when its tangent changes.
        indices = regions.regions[1].vertex_indices
        self.assertPointAlmostEqual(target, _centroid([mesh.parts[0].vertices[i] for i in indices[16:24]]))
        self.assertEqual(original_regions.regions, regions.regions)
        self.assertEqual(original.parts[0].faces, mesh.parts[0].faces)
        self.assertNotEqual(original.parts[0].vertices, mesh.parts[0].vertices)
        owned = set(indices)
        self.assertTrue(all(a == b for i, (a, b) in enumerate(zip(original.parts[0].vertices,
                                                                mesh.parts[0].vertices)) if i not in owned))

    def test_region_ownership_survives_large_vertex_edits(self):
        provider = get_provider('quadruped')
        dimensions = provider.dimensions(_defaults(provider))
        mesh, anatomy = _build_quadruped_mesh(dimensions, QuadrupedFrontRecipe().resolve(dimensions))
        part = mesh.parts[0]
        owned = set(anatomy.regions[1].vertex_indices)
        edited = ObjectMesh((MeshPart(part.name, tuple(
            (x + 100, y - 100, z) if i in owned else (x, y, z)
            for i, (x, y, z) in enumerate(part.vertices)), part.faces, part.uvs),))
        anatomy.validate_mesh(edited)
        self.assertEqual(owned, set(anatomy.regions[1].vertex_indices))


if __name__ == '__main__':
    unittest.main()
