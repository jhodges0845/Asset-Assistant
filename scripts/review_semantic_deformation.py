# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare semantic profile deformation with the unedited asset in identical poses."""
import argparse
import hashlib
import subprocess
import json
from math import dist, isfinite
from pathlib import Path
import sys
from types import SimpleNamespace

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_adapter.adapter import create_character
from blender_adapter.modification import inspect_generated_asset, apply_semantic_modification
from object_core.modification import SemanticOperation, ModificationRequest, plan_modification
from object_core.objects import get_provider
from object_core.models import MeshPart
from object_core.providers.avian_posture import COMPACT_FOLD_ROTATIONS

POSES = {
    'avian': {'wing-up': [('wing.upper.left','x',.4)],
              'wing-down': [('wing.upper.left','x',-.4)],
              'elbow': [('wing.lower.left','z',.4)],
              'combined': list(COMPACT_FOLD_ROTATIONS)},
    'human': {'shoulder': [('upper_arm.left','z',1.05)],
              'shoulder-back': [('upper_arm.left','z',-.6)],
              'elbow': [('forearm.left','z',1.2)],
              'combined': [('upper_arm.left','z',1.05),('forearm.left','z',1.2)]},
    'quadruped': {'shoulder': [('fore_upper.left','x',.35)],
                  'shoulder-back': [('fore_upper.left','x',-.35)],
                  'elbow': [('fore_lower.left','x',-.45)],
                  'combined': [('fore_upper.left','x',.35),('fore_lower.left','x',-.45)]}}


def evaluated(body):
    bpy.context.view_layer.update()
    obj = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = obj.to_mesh()
    try:
        return tuple(tuple(float(c)*100 for c in obj.matrix_world @ v.co) for v in mesh.vertices)
    finally:
        obj.to_mesh_clear()


def pose(rig, rotations):
    for bone in rig.pose.bones:
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = (0,0,0)
    for name,axis,angle in rotations:
        setattr(rig.pose.bones[name].rotation_euler,axis,angle)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def review_case(key, sample, amount, *, enforce_limits=True):
    if key not in POSES or sample not in ('default','contrasting'):
        raise ValueError('Unsupported deformation review case')
    if not isfinite(amount) or not 0 < amount <= 1.5:
        raise ValueError('Amount must be finite and in (0, 1.5]')
    previous = bpy.context.window.scene
    kinds = ('objects','meshes','armatures','collections','materials','actions')
    existing = {kind:set(getattr(bpy.data,kind)) for kind in kinds}
    scene = bpy.data.scenes.new('SemanticDeformationReview')
    bpy.context.window.scene = scene
    try:
        provider = get_provider(key)
        values = {p.key:p.default for p in provider.parameters}
        if sample == 'contrasting':
            values.update({
                'human': dict(height_cm=160,weight_kg=55),
                'quadruped': dict(body_length_cm=100,shoulder_height_cm=65,body_width_cm=30),
                'avian': dict(body_length_cm=65,body_width_cm=24,body_height_cm=30,
                              wingspan_cm=145,tail_length_cm=35),
            }[key])
        mesh = provider.mesh(values)
        root = create_character(mesh,scene=scene,skeleton=provider.skeleton(values),
                                skin_weights=provider.skin_weights(mesh,values))
        root['object_type'] = key
        for name,value in values.items(): root[name] = value
        body = next(obj for obj in root.children if obj.type=='MESH')
        rig = next(obj for obj in root.children if obj.type=='ARMATURE')
        weights = tuple(tuple((g.group,g.weight) for g in v.groups) for v in body.data.vertices)
        neutral = evaluated(body)
        baseline = {}
        for name,rotations in POSES[key].items():
            pose(rig,rotations)
            baseline[name] = evaluated(body)
        pose(rig,[])
        target = 'shoulders' if key=='human' else 'chest'
        profile = 'powerful' if key=='avian' else 'broad'
        operation = SemanticOperation('shape',target,(('profile',profile),('amount',amount)))
        plan = plan_modification(inspect_generated_asset(root),ModificationRequest(semantic_operations=(operation,)))
        require(plan.safe_to_apply,'Semantic apply must remain safe')
        snapshot = apply_semantic_modification(root,plan)
        require(snapshot.owns_geometry,'Applied geometry lost ownership')
        require(weights==tuple(tuple((g.group,g.weight) for g in v.groups) for v in body.data.vertices),
                'Semantic apply changed skin weights')
        edited_neutral = evaluated(body)
        unchanged = [i for i,(a,b) in enumerate(zip(neutral,edited_neutral)) if dist(a,b)<1e-8]
        require(unchanged and len(unchanged)<len(neutral),'Expected localized nonzero edit')
        faces = mesh.parts[0].faces
        edges = {tuple(sorted((a,b))) for face in faces for a,b in zip(face,face[1:]+face[:1])}
        reports, parts = [], {}
        for name,rotations in POSES[key].items():
            pose(rig,rotations)
            points = evaluated(body)
            require(all(isfinite(c) for point in points for c in point),'Nonfinite posed surface')
            leakage = max(dist(baseline[name][i],points[i]) for i in unchanged)
            motion = max(dist(a,b) for a,b in zip(edited_neutral,points))
            edge_rows = []
            for a,b in edges:
                baseline_length = dist(baseline[name][a],baseline[name][b])
                if baseline_length <= 1e-7:
                    continue
                edited_length = dist(points[a],points[b])
                edge_rows.append(dict(indices=(a,b),ratio=edited_length/baseline_length,
                    baseline_rest_cm=dist(neutral[a],neutral[b]),
                    edited_rest_cm=dist(edited_neutral[a],edited_neutral[b]),
                    baseline_posed_cm=baseline_length,edited_posed_cm=edited_length))
            edge_rows.sort(key=lambda row:row['ratio'])
            low,high = edge_rows[0]['ratio'],edge_rows[-1]['ratio']
            edge_passed = low>.5 and high<2.
            require(leakage<1e-5,'Profile changed evaluated vertices outside its rest edit')
            require(motion>.1,'Diagnostic pose did not move the limb')
            if enforce_limits:
                require(edge_passed,
                        f'{key}/{sample}/{amount}/{name}: relative edge ratios {low}..{high}')
            reports.append(dict(pose=name,rotations=rotations,unchanged_vertex_error_cm=leakage,
                                motion_cm=motion,min_edge_ratio=low,max_edge_ratio=high,
                                edge_limit_passed=edge_passed,
                                worst_edges=[edge_rows[0],edge_rows[-1]]))
            if name=='combined':
                parts = dict(before=MeshPart('before',baseline[name],faces),after=MeshPart('after',points,faces))
        return dict(provider=key,sample=sample,amount=amount,profile=profile,parameters=values,
                    unchanged_vertices=len(unchanged),poses=reports), parts
    finally:
        bpy.context.window.scene = previous
        bpy.data.scenes.remove(scene)
        for kind in kinds:
            data = getattr(bpy.data,kind)
            for item in set(data)-existing[kind]: data.remove(item,do_unlink=True)


def render_pair(key, parts, output):
    from scripts import render_human_review as sheets
    sheets._clear_scene()
    before,after = parts['before'],parts['after']
    args = SimpleNamespace(resolution_x=1600,resolution_y=600,samples=8,modes=['clay'])
    material = sheets._configure_scene(args,MeshPart('bounds',before.vertices+after.vertices,before.faces))
    objects = [obj for obj in bpy.context.scene.objects if obj.type=='MESH']
    for label,part in parts.items():
        for obj in objects:
            obj.data.clear_geometry()
            obj.data.from_pydata(part.vertices,[],part.faces)
            obj.data.update()
        sheets._render_modes(args,material,output/(key+'-combined-'+label+'.png'))



def write_report_page(output, document):
    rows = []
    for case in document['cases']:
        for pose_report in case['poses']:
            cells = [case['provider'],case['sample'],str(case['amount']),pose_report['pose'],
                     f"{pose_report['min_edge_ratio']:.3f}",f"{pose_report['max_edge_ratio']:.3f}",
                     'Pass' if pose_report['edge_limit_passed'] else 'Inspect']
            rows.append('<tr>' + ''.join('<td>'+cell+'</td>' for cell in cells) + '</tr>')
    images = []
    for key in dict.fromkeys(case['provider'] for case in document['cases']):
        images.append('<h2>'+key.title()+' - default, amount 0.6, combined bend</h2>')
        for label in ('before','after'):
            path = key+'-combined-'+label+'.png'
            if (output/path).is_file():
                images.append('<h3>'+label.title()+'</h3><img alt="'+key+' '+label+'" src="'+path+'">')
    page = '''<!doctype html><meta charset="utf-8"><title>Semantic deformation review</title>
<style>body{max-width:1500px;margin:30px auto;padding:0 24px;background:#20262c;color:#edf1f4;font:17px system-ui}
img{width:100%}td,th{padding:6px 14px;text-align:left}table{border-collapse:collapse}tr:nth-child(even){background:#303941}a{color:#9ed9ff}</style>
<h1>Paired semantic deformation review</h1><p>Diagnostic screening only. Compare the edited
shape to the unedited shape in the same pose. Edge ratios outside 0.5 to 2 require inspection;
an already compressed baseline edge can inflate this ratio. No self-intersection, volume,
animation or final artistic acceptance is implied.</p><p><a href="report.json">Full report and worst-edge lengths</a></p>
''' + '<h2>Screen: '+('passed' if document['passed'] else 'FAILED - quality work remains')+'</h2>'
    page += '<table><tr><th>Provider</th><th>Shape</th><th>Amount</th><th>Pose</th><th>Min ratio</th><th>Max ratio</th><th>Screen</th></tr>'
    page += ''.join(rows)+'</table>'+''.join(images)
    (output/'index.html').write_text(page,encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--providers',nargs='+',choices=tuple(POSES),default=list(POSES))
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    args.output = args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=True)
    reports = []
    for key in dict.fromkeys(args.providers):
        for sample in ('default','contrasting'):
            for amount in (.6,1.5):
                report,parts = review_case(key,sample,amount,enforce_limits=False)
                reports.append(report)
                if args.render and sample=='default' and amount==.6:
                    render_pair(key,parts,args.output)
    from scripts.render_model_json_acceptance import source_evidence
    passed = all(p['edge_limit_passed'] for r in reports for p in r['poses'])
    document = dict(passed=passed,cases=reports,blender=bpy.app.version_string,**source_evidence(),
                    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    review_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    scope='Paired diagnostic poses; excludes self-intersection, volume, animation and final artistic acceptance.')
    (args.output/'report.json').write_text(json.dumps(document,indent=2),encoding='utf-8')
    write_report_page(args.output,document)
    require(passed,'Relative edge screening failed; see the complete report.json and paired images')
    print(f'All {len(reports)} semantic deformation cases passed ({sum(len(r["poses"]) for r in reports)} paired poses)')


if __name__=='__main__':
    main()
