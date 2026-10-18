# SPDX-License-Identifier: GPL-3.0-or-later
"""Cross-provider external Model JSON through the actual artist-facing operators."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
try:
    import bpy
except ModuleNotFoundError:
    bpy=None

@unittest.skipIf(bpy is None,'requires Blender')
class ModelJSONAcceptanceTests(unittest.TestCase):
    def setUp(self):
        import blender_adapter as addon
        self.addon=addon
        self.previous=bpy.context.window.scene
        self.before={kind:set(getattr(bpy.data,kind)) for kind in
                     ('objects','meshes','armatures','collections','materials','images','actions')}
        self.scene=bpy.data.scenes.new('ModelJSONAcceptance')
        bpy.context.window.scene=self.scene
        addon.register()
        self.temp=TemporaryDirectory()

    def tearDown(self):
        self.addon.unregister()
        bpy.context.window.scene=self.previous
        bpy.data.scenes.remove(self.scene)
        for kind,before in self.before.items():
            data=getattr(bpy.data,kind)
            for item in set(data)-before: data.remove(item,do_unlink=True)
        self.temp.cleanup()

    def prove(self,key,target,profile,combined=False,checkpoint=None):
        from object_core.objects import get_provider
        from blender_adapter.adapter import create_character
        from blender_adapter.modification import inspect_generated_asset
        provider=get_provider(key)
        values={field.key:field.default for field in provider.parameters}
        mesh=provider.mesh(values)
        root=create_character(mesh,scene=self.scene,
            skeleton=provider.skeleton(values),skin_weights=provider.skin_weights(mesh,values))
        root['object_type']=key
        for name,value in values.items(): root[name]=value
        self.scene.humanoid_settings.target=root
        bpy.context.view_layer.objects.active=root
        root.select_set(True)
        def vertices(asset):
            return tuple(tuple(v.co) for obj in asset.children if obj.type=='MESH' for v in obj.data.vertices)
        original=vertices(root)
        identity=inspect_generated_asset(root).asset_id
        rig=next(obj for obj in root.children if obj.type=='ARMATURE')
        export=Path(self.temp.name)/'context.json'
        request_path=Path(self.temp.name)/'returned.json'
        self.assertEqual(bpy.ops.asset_assistant.modify_export_inspection(filepath=str(export)),{'FINISHED'})
        document=json.loads(export.read_text(encoding='utf-8'))
        request=dict(schema=document['request_template']['schema'],asset_id=identity,provider_key=key,
            parameter_changes={},animation_export_names={},component_operations=[],
            semantic_operations=[dict(operation='shape',target=target,arguments=dict(profile=profile,amount=.6))])
        if combined:
            field=next(field for field in provider.parameters if not field.choices)
            changed=values[field.key] + (field.maximum-values[field.key])*.05
            request['parameter_changes']={field.key:changed}
        request_path.write_text(json.dumps(request),encoding='utf-8')
        self.assertEqual(bpy.ops.asset_assistant.modify_import_request(filepath=str(request_path)),{'FINISHED'})
        self.assertEqual(vertices(root),original)
        self.assertEqual(bpy.ops.asset_assistant.model_preview_imported(),{'FINISHED'})
        preview=bpy.data.objects[self.scene['asset_assistant_model_preview_root']]
        preview_vertices=vertices(preview)
        self.assertEqual(vertices(root),original)
        self.assertNotEqual(preview_vertices,original)
        self.assertEqual(bpy.ops.asset_assistant.model_cancel_preview(),{'FINISHED'})
        self.assertEqual(vertices(root),original)
        self.assertFalse(root.hide_get())
        self.assertEqual(bpy.ops.asset_assistant.model_preview_imported(),{'FINISHED'})
        self.assertEqual(bpy.ops.asset_assistant.model_apply_previewed(),{'FINISHED'})
        self.assertNotIn('asset_assistant_model_preview_root',self.scene)
        self.assertEqual(vertices(root),preview_vertices)
        snapshot=inspect_generated_asset(root)
        self.assertEqual(snapshot.asset_id,identity)
        self.assertTrue(snapshot.owns_geometry)
        self.assertEqual(len(snapshot.semantic_operations),1)
        applied_rig=next(obj for obj in root.children if obj.type=='ARMATURE')
        if combined:
            self.assertTrue(snapshot.owns_rig)
            rig=applied_rig
        else:
            self.assertIs(applied_rig,rig)
        body=next(obj for obj in root.children if obj.type=='MESH')
        self.assertTrue(any(mod.type=='ARMATURE' and mod.object==rig for mod in body.modifiers))
        self.assertGreater(len(body.vertex_groups),0)
        self.assertFalse(root.hide_get())
        self.assertEqual(self.scene.get('asset_assistant_modify_status'),'IMPORTED_APPLIED')
        if combined:
            self.assertAlmostEqual(root[field.key],changed)
            from blender_adapter.components import attach_rigid_component, inspect_component
            from object_core.components import ComponentRecord, ComponentKind, AttachmentMode
            box=get_provider('box')
            component_id='acceptance-'+key
            record=ComponentRecord(component_id=component_id,kind=ComponentKind.ACCESSORY,
                provider_key='proof.accessory',attachment_target='asset_root',
                attachment_mode=AttachmentMode.RIGID,owns_geometry=True)
            accessory=attach_rigid_component(root,box.mesh({f.key:f.default for f in box.parameters}),record)
            accessory_vertices=vertices(accessory)
            # Parameter regeneration must preserve attached components by blocking.
            request['parameter_changes']={field.key:values[field.key]}
            request['semantic_operations']=[]
            request_path.write_text(json.dumps(request),encoding='utf-8')
            self.assertEqual(bpy.ops.asset_assistant.modify_import_request(filepath=str(request_path)),{'FINISHED'})
            with self.assertRaisesRegex(RuntimeError,'attached components'):
                bpy.ops.asset_assistant.model_preview_imported()
            self.assertEqual(vertices(root),preview_vertices)
            self.assertEqual(vertices(accessory),accessory_vertices)
            self.assertEqual(inspect_component(root,component_id),record)
            self.assertIs(accessory.parent,root)
            self.assertNotIn('asset_assistant_model_preview_root',self.scene)
            if checkpoint:
                manifest=dict(asset_id=identity,provider=key,parameter=field.key,value=changed,
                    component_id=component_id,vertices=vertices(root),accessory_vertices=accessory_vertices)
                Path(str(checkpoint)+'.json').write_text(json.dumps(manifest),encoding='utf-8')
                self.assertEqual(bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint)),{'FINISHED'})
        # A subsequent artist edit must not be silently regenerated by preview.
        body.data.vertices[0].co.x += .01
        edited=vertices(root)
        self.assertFalse(inspect_generated_asset(root).owns_geometry)
        with self.assertRaises(RuntimeError):
            bpy.ops.asset_assistant.model_preview_imported()
        self.assertEqual(vertices(root),edited)
        self.assertNotIn('asset_assistant_model_preview_root',self.scene)


    def test_human_external_shoulders_edit(self): self.prove('human','shoulders','broad')
    def test_canine_external_chest_edit(self): self.prove('quadruped','chest','broad')
    def test_avian_external_chest_edit(self): self.prove('avian','chest','powerful')

    def test_human_parameter_and_component(self): self.prove('human','shoulders','broad',combined=True)
    def test_canine_parameter_and_component(self): self.prove('quadruped','chest','broad',combined=True)
    def test_avian_parameter_and_component(self): self.prove('avian','chest','powerful',combined=True)

    def prove_legacy_profile_is_preserved(self, key, target):
        from unittest.mock import patch
        from object_core.objects import get_provider
        from object_core.modification import SemanticOperation
        from object_core.providers.semantic_geometry import _transform
        from blender_adapter.adapter import create_character
        from blender_adapter.modification import inspect_generated_asset, _semantic_document
        provider = get_provider(key)
        values = {f.key:f.default for f in provider.parameters}
        base = provider.mesh(values)
        profile = 'powerful' if key == 'avian' else 'broad'
        operation = SemanticOperation('shape',target,(('profile',profile),('amount',.6)))
        if key == 'avian':
            from object_core.providers.avian_semantic import _selected
            legacy_patch = patch('object_core.providers.avian_semantic._chest_indices',
                side_effect=lambda mesh,dimensions,vertices: [i for i,v in enumerate(vertices)
                    if _selected('chest',v,dimensions)])
        else:
            module = 'human_semantic' if key == 'human' else 'quadruped_semantic'
            legacy_patch = patch('object_core.providers.' + module + '._blend_region_transform',
                side_effect=lambda vertices,faces,indices,args: _transform(vertices,indices,args))
        # Reproduce the previously persisted profile exactly.
        with legacy_patch:
            legacy = provider.semantic_mesh(base,values,(operation,))
        root = create_character(legacy,scene=self.scene)
        root['object_type'] = key
        for name,value in values.items(): root[name] = value
        root['asset_assistant_semantic_operations'] = json.dumps([_semantic_document(operation)])
        self.scene.humanoid_settings.target = root
        bpy.context.view_layer.objects.active = root
        root.select_set(True)
        body = next(obj for obj in root.children if obj.type == 'MESH')
        before = tuple(tuple(v.co) for v in body.data.vertices)
        metadata = root['asset_assistant_semantic_operations']
        snapshot = inspect_generated_asset(root)
        self.assertFalse(snapshot.owns_geometry)
        exported = Path(self.temp.name)/'legacy-context.json'
        returned = Path(self.temp.name)/'legacy-request.json'
        self.assertEqual(bpy.ops.asset_assistant.modify_export_inspection(filepath=str(exported)),{'FINISHED'})
        document = json.loads(exported.read_text(encoding='utf-8'))
        request = dict(schema=document['request_template']['schema'],asset_id=snapshot.asset_id,
                       provider_key=key,parameter_changes={},component_operations=[],
                       animation_export_names={},semantic_operations=[_semantic_document(operation)])
        returned.write_text(json.dumps(request),encoding='utf-8')
        self.assertEqual(bpy.ops.asset_assistant.modify_import_request(filepath=str(returned)),{'FINISHED'})
        with self.assertRaisesRegex(RuntimeError,'unowned or ambiguous geometry'):
            bpy.ops.asset_assistant.model_preview_imported()
        self.assertEqual(before,tuple(tuple(v.co) for v in body.data.vertices))
        self.assertEqual(metadata,root['asset_assistant_semantic_operations'])
        self.assertNotIn('asset_assistant_model_preview_root',self.scene)

    def test_legacy_human_shoulders_are_preserved(self):
        self.prove_legacy_profile_is_preserved('human','shoulders')

    def test_legacy_canine_chest_is_preserved(self):
        self.prove_legacy_profile_is_preserved('quadruped','chest')

    def test_legacy_avian_chest_is_preserved(self):
        self.prove_legacy_profile_is_preserved('avian','chest')
