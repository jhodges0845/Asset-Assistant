# SPDX-License-Identifier: GPL-3.0-or-later
"""Reopen a study in Blender and check saved geometry against its resolved preset."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from surface_source_snapshot import verify_source
if (ROOT/'source_manifest.json').exists():verify_source(ROOT)
from object_core.providers.surface_human import SurfaceHumanProvider
from object_core.geometry.surface_human import SurfaceHumanSpec
report=json.loads(bpy.data.texts['GENERATION_REPORT.json'].as_string())
expected,fresh=SurfaceHumanProvider().build(SurfaceHumanSpec(**report['parameters']))
body=bpy.data.objects['Human surface - generated study'];part=expected.parts[0]
assert len(body.data.vertices)==len(part.vertices)
assert tuple(tuple(p.vertices) for p in body.data.polygons)==part.faces
error=max(abs(body.data.vertices[i].co[d]*100-v[d]) for i,v in enumerate(part.vertices) for d in range(3))
assert error<.0001,error
assert fresh['geometry_sha256']==report['geometry_sha256']
assert report['base_triangle_self_intersections']==0
assert len([o for o in bpy.data.scenes['Character'].objects if o.type=='MESH'])==1
assert len([o for o in bpy.data.scenes['Four view review'].objects if o.type=='MESH'])==4
print('REOPEN VERIFIED: parameters, topology, geometry fingerprint, one editable body, four review instances; max coordinate error cm:',error)
