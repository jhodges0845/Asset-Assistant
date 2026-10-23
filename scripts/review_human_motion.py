# SPDX-License-Identifier: GPL-3.0-or-later
"""Sample actual Human actions. Diagnostics do not prove continuous contact or collision safety."""
import argparse
import hashlib
import json
from math import dist, floor, isfinite
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def review_cycle(height=180, weight=95, clip='walk', intervals=64, strength=1.):
    import bpy
    from object_core.objects import get_provider
    from object_core.providers.human import _human_anatomy
    from blender_adapter.adapter import create_character
    from blender_adapter.animation import add_locomotion, add_run
    from scripts.review_semantic_deformation import evaluated
    if clip not in ('walk', 'run') or isinstance(intervals, bool) or not isinstance(intervals, int) or not 4 <= intervals <= 256:
        raise ValueError('Expected walk/run and 4..256 intervals')
    values = dict(height_cm=height, weight_kg=weight, body_type='average')
    provider = get_provider('human')
    mesh = provider.mesh(values)
    part = mesh.parts[0]
    anatomy = _human_anatomy(**values)
    feet = {side: tuple(i for r in anatomy.regions if r.name == 'leg.'+side
                       for i in r.vertex_indices if part.vertices[i][2] < height*.075)
            for side in ('left', 'right')}
    edges = sorted({tuple(sorted((a,b))) for face in part.faces
                    for a,b in zip(face,face[1:]+face[:1])
                    if dist(part.vertices[a],part.vertices[b]) > 1e-7})
    lengths = [dist(part.vertices[a],part.vertices[b]) for a,b in edges]
    from object_core.providers.human_gait import contact_schedule
    duration = 1.2 if clip == 'walk' else .72
    schedules = contact_schedule(duration,strength,height,clip=='run')
    soles = {side:tuple(i for i in indices if 0 <= part.vertices[i][2] <= .1) for side,indices in feet.items()}
    neutral_y = {side:sum(part.vertices[i][1] for i in indices)/len(indices) for side,indices in soles.items()}
    previous = bpy.context.window.scene
    kinds = ('objects','meshes','armatures','collections','materials','actions')
    existing = {kind:set(getattr(bpy.data,kind)) for kind in kinds}
    scene = bpy.data.scenes.new('HumanMotionReview')
    try:
        bpy.context.window.scene = scene
        scene.render.fps = 24
        scene.render.fps_base = 1
        scene.frame_start = 1
        root = create_character(mesh,scene=scene,skeleton=provider.skeleton(values),
                                skin_weights=provider.skin_weights(mesh,values))
        root['object_type'] = 'human'
        for key,value in values.items(): root[key] = value
        body = next(o for o in root.children if o.type == 'MESH')
        duration = 1.2 if clip == 'walk' else .72
        (add_locomotion if clip == 'walk' else add_run)(root,scene,duration,strength)
        frames = []
        first = None
        for index in range(intervals+1):
            frame = 1+duration*24*index/intervals
            scene.frame_set(floor(frame),subframe=frame-floor(frame))
            bpy.context.view_layer.update()
            points = evaluated(body)
            if len(points) != len(part.vertices) or not all(isfinite(c) for p in points for c in p):
                raise ValueError('Nonfinite coordinates or changed topology')
            if first is None: first = points
            ratios = [dist(points[a],points[b])/length for (a,b),length in zip(edges,lengths)]
            low,high = min(range(len(ratios)),key=ratios.__getitem__),max(range(len(ratios)),key=ratios.__getitem__)
            stance_errors = {}
            for side,schedule in schedules.items():
                target = schedule.target(index/intervals)
                if target.in_stance:
                    y = sum(points[i][1] for i in soles[side])/len(soles[side])
                    stance_errors[side] = max(abs(y-neutral_y[side]-target.forward_cm),
                                              abs(min(points[i][2] for i in feet[side])-.02))
            frames.append(dict(phase=index/intervals, stance_target_error_cm=stance_errors,
                foot_min_z_cm={side:min(points[i][2] for i in indices) for side,indices in feet.items()},
                min_edge_ratio=ratios[low],max_edge_ratio=ratios[high],
                compressed_edge=edges[low],stretched_edge=edges[high]))
        return dict(parameters=values,clip=clip,intervals=intervals,strength=strength,
            max_stance_target_error_cm=max(e for f in frames for e in f["stance_target_error_cm"].values()),
            closure_error_cm=max(dist(a,b) for a,b in zip(first,points)),
            minimum_foot_z_cm=min(z for row in frames for z in row['foot_min_z_cm'].values()),
            maximum_lowest_foot_z_cm=max(min(row['foot_min_z_cm'].values()) for row in frames),
            min_edge_ratio=min(row['min_edge_ratio'] for row in frames),
            max_edge_ratio=max(row['max_edge_ratio'] for row in frames),frames=frames)
    finally:
        bpy.context.window.scene = previous
        bpy.data.scenes.remove(scene)
        for kind in kinds:
            for item in set(getattr(bpy.data,kind))-existing[kind]:
                getattr(bpy.data,kind).remove(item,do_unlink=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--strength',type=float,default=1.)
    parser.add_argument('--intervals',type=int,default=64)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    paths = ['object_core/animation/walk.py','object_core/animation/run.py',
             'object_core/providers/human.py','object_core/providers/human_anatomy.py',
             'object_core/geometry/surface_human.py','object_core/rigging/surface_human.py',
             'object_core/providers/human_gait.py','object_core/animation/weighted_contact.py',
             'blender_adapter/animation.py','scripts/review_human_motion.py']
    report = dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        cases=[review_cycle(h,w,c,args.intervals,args.strength) for h,w in ((180,95),(160,55)) for c in ('walk','run')])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps([{k:v for k,v in case.items() if k!='frames'} for case in report['cases']],indent=2))
