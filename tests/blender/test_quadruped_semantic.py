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

    def test_manual_artist_edit_blocks_recipe_apply(self):
        self.body.data.vertices[0].co.x += .123
        snapshot = inspect_generated_asset(self.root)
        operation = SemanticOperation('scale', 'tail', (('factor', 1.1),))
        plan = plan_modification(snapshot, ModificationRequest(semantic_operations=(operation,)))
        self.assertFalse(plan.safe_to_apply)


if __name__ == '__main__':
    unittest.main()
