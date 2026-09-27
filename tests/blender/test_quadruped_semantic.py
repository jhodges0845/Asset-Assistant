# SPDX-License-Identifier: GPL-3.0-or-later
"""Quadruped recipes use the existing inspect/plan/apply and artist ownership path."""
import unittest
try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.modification import inspect_generated_asset, apply_semantic_modification
from object_core.modification import ModificationRequest, SemanticOperation, plan_modification
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, 'requires Blender')
class QuadrupedSemanticTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.scene = bpy.data.scenes.new('QuadrupedSemanticTest')
        bpy.context.window.scene = self.scene
        self.before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes', 'armatures', 'collections')}
        provider = get_provider('quadruped')
        values = {p.key: p.default for p in provider.parameters}
        mesh = provider.mesh(values)
        self.root = create_character(mesh, name=provider.label, scene=self.scene,
                                     skeleton=provider.skeleton(values), skin_weights=provider.skin_weights(mesh, values))
        self.root['object_type'] = provider.key
        for key, value in values.items():
            self.root[key] = value
        self.body = next(o for o in self.root.children if o.type == 'MESH')

    def tearDown(self):
        bpy.context.window.scene = self.previous_scene
        for kind in ('objects', 'meshes', 'armatures', 'collections'):
            for item in set(getattr(bpy.data, kind)) - self.before[kind]:
                getattr(bpy.data, kind).remove(item, do_unlink=True)
        bpy.data.scenes.remove(self.scene)

    def test_plan_is_non_mutating_and_apply_preserves_rigged_ownership(self):
        original = tuple(tuple(v.co) for v in self.body.data.vertices)
        operation = SemanticOperation('shape', 'chest', (('profile', 'broad'), ('amount', .7)))
        snapshot = inspect_generated_asset(self.root)
        plan = plan_modification(snapshot, ModificationRequest(semantic_operations=(operation,)))
        self.assertTrue(plan.safe_to_apply)
        self.assertEqual(original, tuple(tuple(v.co) for v in self.body.data.vertices))
        result = apply_semantic_modification(self.root, plan)
        body = next(o for o in self.root.children if o.type == 'MESH')
        rig = next(o for o in self.root.children if o.type == 'ARMATURE')
        self.assertTrue(result.owns_geometry)
        self.assertEqual(1, len(result.semantic_operations))
        self.assertNotEqual(original, tuple(tuple(v.co) for v in body.data.vertices))
        self.assertTrue(any(m.type == 'ARMATURE' and m.object == rig for m in body.modifiers))
        self.assertGreater(len(body.vertex_groups), 0)

    def test_moved_front_limb_ignores_hind_pose_after_modify_apply(self):
        from object_core.providers.quadruped import _construction
        provider = get_provider('quadruped')
        values = {p.key: p.default for p in provider.parameters}
        _, anatomy = _construction(provider.dimensions(values))
        indices = next(r.vertex_indices for r in anatomy.regions if r.name == 'leg.front.left')
        operation = SemanticOperation('scale', 'leg.front.left',
                                      (('offset_y', -values['body_length_cm'] * .64),))
        plan = plan_modification(inspect_generated_asset(self.root),
                                 ModificationRequest(semantic_operations=(operation,)))
        self.assertTrue(plan.safe_to_apply)
        apply_semantic_modification(self.root, plan)
        body = next(o for o in self.root.children if o.type == 'MESH')
        rig = next(o for o in self.root.children if o.type == 'ARMATURE')

        def evaluated():
            bpy.context.view_layer.update()
            obj = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = obj.to_mesh()
            try:
                return tuple(v.co.copy() for v in mesh.vertices)
            finally:
                obj.to_mesh_clear()

        before = evaluated()
        hind = rig.pose.bones['hind_upper.left']
        hind.rotation_mode = 'XYZ'
        hind.rotation_euler.x = .6
        after = evaluated()
        self.assertLess(max((after[i] - before[i]).length for i in indices), 1e-6)
        hind_indices = next(r.vertex_indices for r in anatomy.regions if r.name == 'leg.hind.left')
        self.assertGreater(max((after[i] - before[i]).length for i in hind_indices), .01)
        hind.rotation_euler.x = 0
        fore = rig.pose.bones['fore_upper.left']
        fore.rotation_mode = 'XYZ'
        fore.rotation_euler.x = .6
        after = evaluated()
        self.assertGreater(max((after[i] - before[i]).length for i in indices), .01)

    def test_hock_is_independently_posable_and_existing_clips_resolve(self):
        from object_core.providers.quadruped import _construction
        from scripts.render_canine_review import evaluated_points
        provider = get_provider('quadruped')
        values = {p.key: p.default for p in provider.parameters}
        _, anatomy = _construction(provider.dimensions(values))
        rig = next(o for o in self.root.children if o.type == 'ARMATURE')
        self.assertEqual(17, len(rig.pose.bones))
        for clip in (provider.idle(2, 1), provider.locomotion(2, 1), provider.run(1, 1)):
            self.assertTrue(all(t.bone in rig.pose.bones for t in clip.tracks))
        before = evaluated_points(self.body)
        knee = rig.pose.bones['hind_lower.left'].head.copy()
        hock = rig.pose.bones['hind_pastern.left']
        old_head, old_tail = hock.head.copy(), hock.tail.copy()
        hock.rotation_mode = 'XYZ'
        hock.rotation_euler.x = .45
        after = evaluated_points(self.body)
        self.assertLess((hock.head - old_head).length, 1e-6)
        self.assertLess((rig.pose.bones['hind_lower.left'].head - knee).length, 1e-6)
        self.assertGreater((hock.tail - old_tail).length, .01)
        regions = {r.name: r.vertex_indices for r in anatomy.regions}
        paw = next(p.position for p in anatomy.landmarks if p.name == 'paw.hind.left')
        # Refined indices are not ring order: select the vertices nearest the paw.
        distal = sorted(regions['leg.hind.left'], key=lambda i: sum(
            (before[i][k] * 100 - paw[k])**2 for k in range(3)))[:8]
        self.assertGreater(max((after[i] - before[i]).length for i in distal), .01)
        for name in ('leg.hind.right', 'leg.front.left', 'leg.front.right'):
            self.assertLess(max((after[i] - before[i]).length for i in regions[name]), 1e-6)

    def test_refined_ears_apply_and_follow_head_pose(self):
        from object_core.providers.quadruped import _construction
        from scripts.render_canine_review import evaluated_points
        provider = get_provider('quadruped')
        values = {p.key: p.default for p in provider.parameters}
        _, anatomy = _construction(provider.dimensions(values))
        operation = SemanticOperation('scale', 'ear.left', (('factor', 1.2),))
        plan = plan_modification(inspect_generated_asset(self.root),
                                 ModificationRequest(semantic_operations=(operation,)))
        self.assertTrue(plan.safe_to_apply)
        apply_semantic_modification(self.root, plan)
        body = next(o for o in self.root.children if o.type == 'MESH')
        rig = next(o for o in self.root.children if o.type == 'ARMATURE')
        before = evaluated_points(body)
        rig.pose.bones['head'].rotation_mode = 'XYZ'
        rig.pose.bones['head'].rotation_euler.x = .3
        after = evaluated_points(body)
        for region in anatomy.regions:
            if region.name.startswith('ear.'):
                self.assertGreater(min((after[i] - before[i]).length for i in region.vertex_indices), .001)
            if region.name.startswith('leg.'):
                self.assertLess(max((after[i] - before[i]).length for i in region.vertex_indices), 1e-6)

    def test_shoulder_pose_keeps_chest_head_and_tail_fixed(self):
        from object_core.providers.quadruped import _construction
        from scripts.render_canine_review import evaluated_points
        provider = get_provider('quadruped')
        values = {p.key: p.default for p in provider.parameters}
        _, anatomy = _construction(provider.dimensions(values))
        before = evaluated_points(self.body)
        rig = next(o for o in self.root.children if o.type == 'ARMATURE')
        bone = rig.pose.bones['fore_upper.left']
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler.x = .35
        after = evaluated_points(self.body)
        for region in anatomy.regions:
            displacement = max((after[i] - before[i]).length for i in region.vertex_indices)
            if region.name in ('torso', 'head', 'tail', 'leg.front.right', 'leg.hind.left', 'leg.hind.right'):
                self.assertLess(displacement, 1e-6, region.name)
            elif region.name == 'leg.front.left':
                self.assertGreater(displacement, .01)

    def test_previous_recipe_surface_is_preserved_and_modify_is_blocked(self):
        import json
        from pathlib import Path
        from object_core.models import MeshPart, ObjectMesh
        document = json.loads((Path(__file__).resolve().parents[1] / 'fixtures' / 'canine_v2_default.json').read_text())
        raw = document['part']
        mesh = ObjectMesh((MeshPart(raw['name'], raw['vertices'], raw['faces'], raw['uvs']),))
        legacy = create_character(mesh, name='SavedCanineV2', scene=self.scene)
        legacy['object_type'] = 'quadruped'
        for key, value in document['parameters'].items():
            legacy[key] = value
        body = next(o for o in legacy.children if o.type == 'MESH')
        before = tuple(tuple(v.co) for v in body.data.vertices)
        snapshot = inspect_generated_asset(legacy)
        self.assertFalse(snapshot.owns_geometry)
        operation = SemanticOperation('scale', 'leg.hind.left', (('factor', 1.1),))
        plan = plan_modification(snapshot, ModificationRequest(semantic_operations=(operation,)))
        self.assertFalse(plan.safe_to_apply)
        with self.assertRaises(ValueError):
            apply_semantic_modification(legacy, plan)
        self.assertEqual(before, tuple(tuple(v.co) for v in body.data.vertices))
        self.assertEqual(280, len(body.data.vertices))

    def test_manual_artist_edit_blocks_recipe_apply(self):
        self.body.data.vertices[0].co.x += .123
        snapshot = inspect_generated_asset(self.root)
        operation = SemanticOperation('scale', 'tail', (('factor', 1.1),))
        plan = plan_modification(snapshot, ModificationRequest(semantic_operations=(operation,)))
        self.assertFalse(plan.safe_to_apply)


if __name__ == '__main__':
    unittest.main()
