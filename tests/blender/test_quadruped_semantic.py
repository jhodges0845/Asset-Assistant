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

    def test_manual_artist_edit_blocks_recipe_apply(self):
        self.body.data.vertices[0].co.x += .123
        snapshot = inspect_generated_asset(self.root)
        operation = SemanticOperation('scale', 'tail', (('factor', 1.1),))
        plan = plan_modification(snapshot, ModificationRequest(semantic_operations=(operation,)))
        self.assertFalse(plan.safe_to_apply)


if __name__ == '__main__':
    unittest.main()
