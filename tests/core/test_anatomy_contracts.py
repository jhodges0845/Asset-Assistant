# SPDX-License-Identifier: GPL-3.0-or-later
from dataclasses import FrozenInstanceError, replace
import unittest

from object_core.anatomy import (
    AnatomyConnection, AnatomyRegion, JointChain, Landmark, ResolvedAnatomy,
)
from object_core.models.mesh import MeshPart, ObjectMesh


def specimen():
    return ResolvedAnatomy(
        'example', '1', [('size', 1.0)],
        landmarks=[Landmark('root', [0, 0, 0]), Landmark('shoulder', [0, 0, 1]),
                   Landmark('elbow', [1, 0, 1]), Landmark('wrist', [2, 0, 1])],
        regions=[AnatomyRegion('torso', 'body', [0]),
                 AnatomyRegion('limb.left', 'body', [2, 1]),
                 AnatomyRegion('limb.right', 'body', [])],
        chains=[JointChain('torso', ['root', 'shoulder'], ['spine']),
                JointChain('limb', ['shoulder', 'elbow', 'wrist'], ['upper', 'lower'],
                           'spine', [0, 1, 0], 'support')],
        connections=[AnatomyConnection('shoulder', ['torso', 'limb.left'],
                                       'connected', [[0], [1]])],
        symmetry=[['limb.left', 'limb.right']],
    )


class AnatomyContractTests(unittest.TestCase):
    def test_immutable_deterministic_and_hashable(self):
        first = specimen()
        self.assertEqual(first, specimen())
        self.assertEqual(hash(first), hash(specimen()))
        with self.assertRaises(FrozenInstanceError):
            first.recipe_id = 'changed'
        source = [0, 1]
        region = AnatomyRegion('arm', 'body', source)
        source.append(2)
        self.assertEqual(region.vertex_indices, (0, 1))
        self.assertEqual(first.regions[1].vertex_indices, (1, 2))

    def test_parameter_order_normalized_and_identity_complete(self):
        anatomy = specimen()
        first = replace(anatomy, parameters=[('b', 2), ('a', 1)])
        self.assertEqual(first, replace(anatomy, parameters=[('a', 1), ('b', 2)]))
        self.assertNotEqual(first, replace(first, recipe_version='2'))
        self.assertNotEqual(first, replace(first, parameters=[('a', 2), ('b', 2)]))

    def test_region_ownership_survives_vertex_movement(self):
        anatomy = specimen()
        for coordinates in (((0, 0, 0), (1, 0, 0), (0, 1, 0)),
                            ((100, 0, 0), (-20, 10, 0), (0, 1, 70))):
            anatomy.validate_mesh(ObjectMesh((MeshPart('body', coordinates, ((0, 1, 2),)),)))
        self.assertEqual(anatomy.regions[1].vertex_indices, (1, 2))

    def test_mesh_bounds_and_missing_part(self):
        mesh = ObjectMesh((MeshPart('body', ((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),))
        anatomy = specimen()
        for region in (AnatomyRegion('torso', 'missing', (0,)),
                       AnatomyRegion('torso', 'body', (3,))):
            with self.assertRaises(ValueError):
                replace(anatomy, regions=(region,) + anatomy.regions[1:]).validate_mesh(mesh)
        connection = replace(anatomy.connections[0], boundaries=((0,), (3,)))
        with self.assertRaises(ValueError):
            replace(anatomy, connections=(connection,)).validate_mesh(mesh)

    def test_bad_references_and_cycles_rejected(self):
        anatomy = specimen()
        variants = [
            dict(landmarks=anatomy.landmarks[:-1]),
            dict(chains=(replace(anatomy.chains[0], parent_bone='missing'),)),
            dict(chains=(replace(anatomy.chains[0], parent_bone='lower'), anatomy.chains[1])),
            dict(chains=anatomy.chains + (replace(anatomy.chains[1], name='duplicate'),)),
            dict(connections=(replace(anatomy.connections[0], regions=('torso', 'missing')),)),
            dict(symmetry=(('torso', 'missing'),)),
            dict(symmetry=(('torso', 'limb.left'), ('limb.left', 'limb.right'))),
            dict(regions=anatomy.regions + (anatomy.regions[0],)),
            dict(parameters=(('size', 1), ('size', 2))),
        ]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                replace(anatomy, **variant)

    def test_malformed_local_data_rejected(self):
        factories = [
            lambda: Landmark('', (0, 0, 0)),
            lambda: Landmark('a', (0, 0)),
            lambda: Landmark('a', (0, float('nan'), 0)),
            lambda: AnatomyRegion('a', 'body', (-1,)),
            lambda: AnatomyRegion('a', 'body', (True,)),
            lambda: AnatomyRegion('a', 'body', (1, 1)),
            lambda: JointChain('a', ('a', 'b'), ()),
            lambda: JointChain('a', ('a', 'a'), ('bone',)),
            lambda: JointChain('a', ('a', 'b'), ('bone',), bend_direction=(0, 0, 0)),
            lambda: AnatomyConnection('a', ('a', 'a'), 'connected'),
            lambda: AnatomyConnection('a', ('a', 'b'), 'unknown'),
            lambda: AnatomyConnection('a', ('a', 'b'), 'connected', ((),)),
            lambda: ResolvedAnatomy('a', '1', (('size', float('inf')),)),
        ]
        for factory in factories:
            with self.subTest(factory=factory), self.assertRaises(ValueError):
                factory()
        with self.assertRaises(TypeError):
            Landmark('a', (False, 0, 0))
        with self.assertRaises(TypeError):
            ResolvedAnatomy('a', '1', (('size', []),))
        with self.assertRaises(TypeError):
            replace(specimen(), regions=('bad',))


if __name__ == '__main__':
    unittest.main()
