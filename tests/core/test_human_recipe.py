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
        self.assertEqual((anatomy.recipe_id, anatomy.recipe_version), ('human', '4'))
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


    def test_weight_locality_preserves_authored_arm_and_shoulder_join(self):
        values = dict(height_cm=180, weight_kg=95, body_type='average')
        mesh = human._human_mesh(**values)
        skeleton = human._human_skeleton(**values)
        anatomy = human._human_anatomy(**values)
        with patch.object(human, 'localize_upper_body_weights',
                          side_effect=lambda mesh, skeleton, weights, owners: weights), \
             patch.object(human, 'localize_arm_joint_weights',
                          side_effect=lambda mesh, skeleton, weights, owners: weights):
            original = human._surface_skin_weights(mesh, skeleton, anatomy)[0]
        owners = {i:r.name.split('.')[-1] for r in anatomy.regions
                  if r.name.startswith('arm.') for i in r.vertex_indices}
        repaired = human.localize_upper_body_weights(mesh, skeleton, (original,), owners)[0]
        arms = {i for r in anatomy.regions if r.name.startswith('arm.') for i in r.vertex_indices}
        for i in arms:
            self.assertEqual(repaired.vertices[i], original.vertices[i])
        joins = set()
        for face in mesh.parts[0].faces:
            for a, b in zip(face, face[1:] + face[:1]):
                if (a in arms) != (b in arms):
                    joins.add(b if a in arms else a)
        self.assertGreater(len(joins), 0)
        for i in joins:
            before = {w.bone_name:w.weight for w in original.vertices[i]}
            after = {w.bone_name:w.weight for w in repaired.vertices[i]}
            for side in ('left', 'right'):
                name = 'upper_arm.' + side
                self.assertAlmostEqual(before.get(name, 0), after.get(name, 0), places=12)


    def test_shoulder_collar_has_no_remote_forearm_influence(self):
        values = dict(height_cm=180, weight_kg=95, body_type='average')
        mesh = human._human_mesh(**values)
        skeleton = human._human_skeleton(**values)
        anatomy = human._human_anatomy(**values)
        weights = human._surface_skin_weights(mesh, skeleton, anatomy)[0]
        bones = {b.name:b for b in skeleton.bones}
        collars = 0
        blended_elbows = 0
        for region in anatomy.regions:
            if not region.name.startswith('arm.'):
                continue
            side = region.name.split('.')[-1]
            bone = bones['upper_arm.'+side]
            axis = tuple(b-a for a,b in zip(bone.head, bone.tail))
            for i in region.vertex_indices:
                point = mesh.parts[0].vertices[i]
                t = sum((p-a)*d for p,a,d in zip(point,bone.head,axis))/sum(d*d for d in axis)
                row = {w.bone_name:w.weight for w in weights.vertices[i]}
                if t <= .5:
                    self.assertNotIn('forearm.'+side, row)
                    collars += 1
                if t >= .5:
                    self.assertNotIn('torso', row)
                if .9 < t < 1.1 and 'upper_arm.'+side in row and 'forearm.'+side in row:
                    blended_elbows += 1
        self.assertGreater(collars, 100)
        self.assertGreater(blended_elbows, 10)


    def test_hip_weights_are_continuous_and_preserve_unrelated_regions(self):
        from math import dist
        for height, weight in ((180,95),(160,55)):
            values = dict(height_cm=height, weight_kg=weight, body_type='average')
            mesh = human._human_mesh(**values)
            skeleton = human._human_skeleton(**values)
            anatomy = human._human_anatomy(**values)
            with patch.object(human, 'blend_hip_weights', side_effect=lambda m,s,w,o:w):
                original = human._surface_skin_weights(mesh, skeleton, anatomy)[0]
            owners = {i:r.name.split('.')[-1] for r in anatomy.regions
                      if r.name.startswith('arm.') for i in r.vertex_indices}
            repaired = human.blend_hip_weights(mesh,skeleton,(original,),owners)[0]
            rows = [{w.bone_name:w.weight for w in row} for row in repaired.vertices]
            part = mesh.parts[0]
            for i,point in enumerate(part.vertices):
                if i in owners or point[2] < .36*height or point[2] > .71*height:
                    self.assertEqual(original.vertices[i], repaired.vertices[i])
                self.assertAlmostEqual(sum(rows[i].values()), 1.)
            edges = {tuple(sorted((a,b))) for f in part.faces for a,b in zip(f,f[1:]+f[:1])
                     if a not in owners and b not in owners
                     and .44*height < part.vertices[a][2] < .64*height
                     and .44*height < part.vertices[b][2] < .64*height}
            for a,b in edges:
                length = dist(part.vertices[a],part.vertices[b])
                if length > 1e-7:
                    jump = abs(rows[a].get('upper_leg.left',0)-rows[b].get('upper_leg.left',0))
                    self.assertLess(jump/length, .25)


if __name__ == '__main__':
    unittest.main()
