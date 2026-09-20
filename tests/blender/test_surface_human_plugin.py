# SPDX-License-Identifier: GPL-3.0-or-later
import json
import unittest
from unittest.mock import patch
import bpy
import blender_adapter
from blender_adapter import ui
from object_core.objects import get_provider


class SurfaceHumanPluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blender_adapter.register()

    @classmethod
    def tearDownClass(cls):
        blender_adapter.unregister()

    def test_operator_matches_provider_and_failed_replace_preserves_asset(self):
        scene=bpy.data.scenes.new('Surface plugin integration')
        previous=bpy.context.window.scene;bpy.context.window.scene=scene
        try:
            scene.unit_settings.scale_length=.01
            settings=scene.humanoid_settings;settings.object_type='human_surface_study'
            self.assertEqual(bpy.ops.humanoid.generate_blockout(),{'FINISHED'})
            root=settings.target;name=root.name
            self.assertEqual(settings.asset_use,'STATIC')
            self.assertFalse(ui.HUMANOID_OT_rig.poll(bpy.context))
            provider=get_provider(settings.object_type)
            values={p.key:getattr(settings,ui._field_name(provider,p)) for p in provider.parameters}
            mesh,report=provider.build_values(values)
            saved=json.loads(root['surface_generation_report'])
            self.assertEqual(saved['geometry_sha256'],report['geometry_sha256'])
            self.assertEqual(saved['base_triangle_self_intersections'],0)
            body=next(o for o in root.children if o.type=='MESH')
            self.assertEqual(len(body.data.vertices),42186)
            self.assertEqual(tuple(tuple(p.vertices) for p in body.data.polygons),mesh.parts[0].faces)
            self.assertLess(max(abs(body.data.vertices[i].co[d]-v[d]) for i,v in enumerate(mesh.parts[0].vertices) for d in range(3)),.0001)
            self.assertEqual(body.modifiers[0].type,'SUBSURF')
            self.assertEqual(root['asset_assistant_source'],'GENERATED')
            with patch('blender_adapter.surface_human_runtime.validate_control_surface',side_effect=ValueError('test collision rejection')):
                with self.assertRaises(RuntimeError):bpy.ops.asset_assistant.generate_replace_current()
            self.assertEqual(settings.target.name,name)
            self.assertIn(name,bpy.data.objects)
            self.assertFalse(any(m.name.startswith('Surface validation temporary') for m in bpy.data.meshes))
        finally:
            for obj in list(scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
            bpy.context.window.scene=previous;bpy.data.scenes.remove(scene)
