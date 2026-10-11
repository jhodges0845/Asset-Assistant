# SPDX-License-Identifier: GPL-3.0-or-later
"""Human recipe integration and boundary regressions."""
import unittest
from unittest.mock import patch

from object_core.models import BodyType
from object_core.models.mesh import MeshPart, ObjectMesh
from object_core.modification import SemanticOperation
from object_core.objects import get_provider
from object_core.providers import human
from object_core.providers.human_anatomy import HumanRecipe


class HumanRecipeTests(unittest.TestCase):
    def test_mesh_and_rig_consume_the_same_resolved_instance(self):
        values = dict(height_cm=183.125, weight_kg=86.5, body_type='average')
        with patch.object(human, 'shape_human_surface', wraps=human.shape_human_surface) as mesh_builder, \
             patch.object(human, 'surface_skeleton', wraps=human.surface_skeleton) as rig_builder:
            human._human_mesh(**values)
            human._human_skeleton(**values)
        anatomy = mesh_builder.call_args.args[1]
        self.assertIs(anatomy, rig_builder.call_args.args[0])
        self.assertTrue(anatomy is human._human_anatomy(**values), "normalized calls must reuse anatomy")
        self.assertEqual((anatomy.recipe_id, anatomy.recipe_version), ('human', '1'))
        self.assertEqual(dict(anatomy.parameters), values)
        self.assertEqual(16, sum(len(chain.bones) for chain in anatomy.chains))

    def test_recipe_version_participates_in_cache_identity(self):
        original = human._human_anatomy(180, 95, 'average')
        original_mesh = human._human_mesh(180, 95, 'average')
        with patch.object(HumanRecipe, 'recipe_version', 'test-next'):
            changed = human._human_anatomy(180, 95, 'average')
            changed_mesh = human._human_mesh(180, 95, 'average')
        self.assertEqual(changed.recipe_version, 'test-next')
        self.assertTrue(changed is not original)
        self.assertTrue(changed_mesh is not original_mesh)
        self.assertEqual(changed_mesh, original_mesh)

    def test_height_boundaries_resolve_for_every_body_type(self):
        for height in (120.0, 240.0):
            for body_type in BodyType:
                for weight in (30.0, 300.0):
                    with self.subTest(height=height, body_type=body_type, weight=weight):
                        anatomy = human._human_anatomy(height, weight, body_type.value)
                        skeleton = human.surface_skeleton(anatomy)
                        self.assertEqual(16, len(skeleton.bones))
                        self.assertAlmostEqual(dict(anatomy.parameters)['height_cm'], height)
        for height in (119.99, 240.01):
            with self.assertRaises(ValueError):
                human._human_anatomy(height, 95, 'average')

    def test_authored_limbs_are_disjoint_and_match_rig_side(self):
        anatomy = human._human_anatomy(180, 95, 'average')
        mesh = human._human_mesh(180, 95, 'average')
        regions = {r.name: set(r.vertex_indices) for r in anatomy.regions}
        self.assertEqual(regions['body'], set(range(len(mesh.parts[0].vertices))))
        seen = set()
        for name in ('arm.left', 'arm.right', 'leg.left', 'leg.right'):
            self.assertTrue(regions[name])
            self.assertFalse(seen.intersection(regions[name]))
            seen.update(regions[name])
            sign = 1 if name.endswith('.left') else -1
            self.assertTrue(all(mesh.parts[0].vertices[i][0] * sign > 0 for i in regions[name]))
        self.assertEqual(len(anatomy.connections), 4)
        self.assertEqual(len(anatomy.symmetry), 2)

    def test_semantic_ownership_rejects_reindexed_topology(self):
        provider = get_provider('human')
        values = dict(height_cm=180, weight_kg=95, body_type='average')
        mesh = provider.mesh(values)
        part = mesh.parts[0]
        changed = ObjectMesh((MeshPart(part.name, part.vertices, tuple(reversed(part.faces)),
                                      tuple(reversed(part.uvs))),))
        operation = SemanticOperation('scale', 'arm.left', (('factor', 1.1),))
        with self.assertRaisesRegex(ValueError, 'authored surface topology'):
            provider.semantic_mesh(changed, values, (operation,))

    def test_recipe_rejects_missing_or_wrong_part_ownership(self):
        from dataclasses import replace
        regions = human._human_regions()
        with self.assertRaises(ValueError):
            HumanRecipe(regions[:-1])
        with self.assertRaises(ValueError):
            HumanRecipe((replace(regions[0], mesh_part='other'),) + regions[1:])


if __name__ == '__main__':
    unittest.main()
