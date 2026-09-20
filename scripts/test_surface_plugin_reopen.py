# SPDX-License-Identifier: GPL-3.0-or-later
"""Real save/reopen check for the plugin mathematical Human."""
import json,sys,tempfile
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import blender_adapter
from object_core.objects import get_provider
blender_adapter.register()
try:
    settings=bpy.context.scene.humanoid_settings
    settings.object_type='human_surface_study'
    assert bpy.ops.humanoid.generate_blockout()=={'FINISHED'}
    root=settings.target;asset_id=root['asset_assistant_asset_id']
    with tempfile.TemporaryDirectory() as folder:
        path=str(Path(folder)/'surface.blend')
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        root=bpy.context.scene.humanoid_settings.target
        assert root['asset_assistant_asset_id']==asset_id
        assert root['object_type']=='human_surface_study'
        provider=get_provider(root['object_type'])
        values={field.key:root[field.key] for field in provider.parameters}
        mesh,report=provider.build_values(values)
        saved=json.loads(root['surface_generation_report'])
        assert saved['geometry_sha256']==report['geometry_sha256']
        body=next(o for o in root.children if o.type=='MESH')
        assert tuple(tuple(p.vertices) for p in body.data.polygons)==mesh.parts[0].faces
        scale=root['coordinate_scale']
        assert max(abs(body.data.vertices[i].co[d]/scale-v[d]) for i,v in enumerate(mesh.parts[0].vertices) for d in range(3))<.0001
        assert body.modifiers[0].type=='SUBSURF'
        print('SURFACE_PLUGIN_REOPEN_OK')
finally:
    blender_adapter.unregister()
