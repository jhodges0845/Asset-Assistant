# SPDX-License-Identifier: GPL-3.0-or-later
"""Review eased quaternion blends from actual Idle to Flight poses.

Diagnostic only: does not add takeoff/landing or overwrite generated actions.
Run in Blender with -- --output report.json [--sample contrasting].
"""
import argparse
import json
from math import floor
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))


def review_transition(values, intervals=64, strength=1., flight_phase=.25):
    import bpy
    from object_core.objects import get_provider
    from blender_adapter.adapter import create_character
    from blender_adapter.animation import add_idle, add_flight
    from scripts.render_avian_review import evaluated_points
    from scripts.avian_review_metrics import surface_crossings, crossing_details
    from object_core.providers.avian_animation import _validate
    _validate(1.2,strength,.5,4.)
    if type(intervals) is not int or not 4 <= intervals <= 256:
        raise ValueError('Review requires 4..256 intervals')
    if not 0 <= flight_phase <= 1:
        raise ValueError('Flight phase must be in [0,1]')
    provider=get_provider('avian')
    mesh,anatomy=provider.mesh(values),provider.anatomy(values)
    previous=bpy.context.window.scene
    kinds=('objects','meshes','armatures','collections','actions','materials')
    before={kind:set(getattr(bpy.data,kind)) for kind in kinds}
    scene=bpy.data.scenes.new('AvianTransitionReview')
    try:
        bpy.context.window.scene=scene
        scene.frame_start=1
        scene.render.fps=24
        scene.render.fps_base=1
        root=create_character(mesh,scene=scene,skeleton=provider.skeleton(values),
                              skin_weights=provider.skin_weights(mesh,values))
        root['object_type']='avian'
        for key,value in values.items(): root[key]=value
        rig=next(o for o in root.children if o.type=='ARMATURE')
        body=next(o for o in root.children if o.type=='MESH')
        poses=[]
        endpoints=[]
        for generate,phase,duration in ((add_idle,0.,4.),(add_flight,flight_phase,1.2)):
            generate(root,scene,duration,strength)
            frame=1+duration*phase*24
            scene.frame_set(floor(frame),subframe=frame-floor(frame))
            bpy.context.view_layer.update()
            poses.append({b.name:(b.location.copy(),b.rotation_quaternion.copy()) for b in rig.pose.bones})
            endpoints.append(evaluated_points(body))
        rig.animation_data.action=None
        rows=[]
        endpoint_error=0.
        for step in range(intervals+1):
            t=step/intervals
            blend=t*t*(3-2*t)
            for bone in rig.pose.bones:
                loc0,q0=poses[0][bone.name]
                loc1,q1=poses[1][bone.name]
                bone.location=loc0.lerp(loc1,blend)
                bone.rotation_quaternion=q0.slerp(q1,blend)
            points=evaluated_points(body)
            pairs=surface_crossings(points,mesh.parts[0].faces)
            rows.append(dict(phase=t,surface_crossings=pairs))
            if step in (0,intervals):
                reference=endpoints[0 if step==0 else 1]
                endpoint_error=max(endpoint_error,max(sum((a-b)**2 for a,b in zip(p,q))**.5 for p,q in zip(points,reference)))
        pairs=sorted({tuple(pair) for row in rows for pair in row['surface_crossings']})
        return dict(parameters=values,strength=strength,flight_phase=flight_phase,
                    intervals=intervals,endpoint_error_cm=endpoint_error,
                    crossing_samples=sum(bool(r['surface_crossings']) for r in rows),
                    surface_crossing_details=crossing_details(mesh.parts[0].faces,anatomy.regions,pairs),samples=rows)
    finally:
        bpy.context.window.scene=previous
        bpy.data.scenes.remove(scene)
        for kind in kinds:
            data=getattr(bpy.data,kind)
            for item in set(data)-before[kind]: data.remove(item,do_unlink=True)


def main():
    from scripts.avian_review_samples import AVIAN_REVIEW_SAMPLES,review_values
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sample',choices=('default',)+tuple(AVIAN_REVIEW_SAMPLES),default='default')
    parser.add_argument('--strength',type=float,default=1.)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    report=review_transition(review_values(args.sample),strength=args.strength)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2))
    print(report['crossing_samples'],report['endpoint_error_cm'])

if __name__=='__main__': main()
