# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure absolute Human hip deformation, not only edited-versus-base ratios."""
import argparse
import hashlib
import json
from math import dist
from pathlib import Path
import sys
import bpy
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from object_core.objects import get_provider
from object_core.providers.human import _human_anatomy
from blender_adapter.adapter import create_character
from scripts.review_semantic_deformation import evaluated, pose


def review_hips(height=180, weight=95):
    provider = get_provider('human')
    values = dict(height_cm=height, weight_kg=weight, body_type='average')
    mesh = provider.mesh(values)
    part = mesh.parts[0]
    anatomy = _human_anatomy(**values)
    arms = {i for r in anatomy.regions if r.name.startswith('arm.') for i in r.vertex_indices}
    hips = {i for i,p in enumerate(part.vertices) if i not in arms and .44*height < p[2] < .64*height}
    edges = {tuple(sorted((a,b))) for face in part.faces
             for a,b in zip(face, face[1:]+face[:1]) if a in hips and b in hips
             and dist(part.vertices[a],part.vertices[b]) > 1e-7}
    weights = provider.skin_weights(mesh, values)
    rows = [{w.bone_name:w.weight for w in row} for row in weights[0].vertices]
    gradient = max(abs(rows[a].get('upper_leg.left',0)-rows[b].get('upper_leg.left',0))
                   /dist(part.vertices[a],part.vertices[b]) for a,b in edges)
    previous = bpy.context.window.scene
    kinds = ('objects','meshes','armatures','collections','materials','actions')
    existing = {kind:set(getattr(bpy.data,kind)) for kind in kinds}
    scene = bpy.data.scenes.new('HipReview')
    bpy.context.window.scene = scene
    reports = []
    try:
        root = create_character(mesh,scene=scene,skeleton=provider.skeleton(values),skin_weights=weights)
        body = next(o for o in root.children if o.type=='MESH')
        rig = next(o for o in root.children if o.type=='ARMATURE')
        neutral = evaluated(body)
        for side in ('left','right'):
            for angle, knee in ((.95,0.),(-.6,0.),(.95,-1.2)):
                pose(rig,[('upper_leg.'+side,'x',angle),('lower_leg.'+side,'x',knee)])
                points = evaluated(body)
                ratios = [(dist(points[a],points[b])/dist(neutral[a],neutral[b]),a,b) for a,b in edges]
                low,high = min(ratios),max(ratios)
                reports.append(dict(side=side,angle=angle,knee_angle=knee,min_edge_ratio=low[0],max_edge_ratio=high[0],
                                    worst_stretch_edge=high[1:],worst_compression_edge=low[1:]))
        return dict(parameters=values,hip_edges=len(edges),max_weight_gradient_per_cm=gradient,poses=reports)
    finally:
        bpy.context.window.scene = previous
        bpy.data.scenes.remove(scene)
        for kind in kinds:
            for item in set(getattr(bpy.data,kind))-existing[kind]:
                getattr(bpy.data,kind).remove(item,do_unlink=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    from scripts.render_model_json_acceptance import source_evidence
    report=dict(cases=[review_hips(180,95),review_hips(160,55)],**source_evidence())
    report['review_script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['passed'] = all(.5 < p['min_edge_ratio'] and p['max_edge_ratio'] < 2.
                           for c in report['cases'] for p in c['poses'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps(report['cases'],indent=2))

    if not report['passed']:
        raise RuntimeError('Absolute hip edge screen failed; inspect the saved report')
