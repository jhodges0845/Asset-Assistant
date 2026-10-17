# SPDX-License-Identifier: GPL-3.0-or-later
"""Sample actual Avian Idle/Walk/Flight actions in an isolated Blender scene.

Scheduled stance and fixed-ground diagnostics do not establish physical contact.
Run in Blender with -- --output report.json [--sample contrasting].
"""
import argparse
import json
from math import floor, isfinite
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from object_core.objects import get_provider
from scripts.avian_review_samples import AVIAN_REVIEW_SAMPLES, review_values


def review_cycle(values, clip='walk', intervals=64, strength=1.0):
    import bpy
    from blender_adapter.adapter import create_character
    from blender_adapter.animation import add_idle, add_locomotion, add_flight
    if clip not in ('idle', 'walk', 'flight'):
        raise ValueError('Review supports idle, walk or flight')
    if isinstance(intervals, bool) or not isinstance(intervals, int) or not 4 <= intervals <= 256:
        raise ValueError('Review requires 4..256 intervals')
    from object_core.providers.avian_animation import _validate
    _validate(1.2, strength, .5, 4.)
    provider = get_provider('avian')
    mesh, anatomy = provider.mesh(values), provider.anatomy(values)
    duration = 4.0 if clip == 'idle' else 1.2
    feet = {r.name: r.vertex_indices[24:] for r in anatomy.regions if r.name.startswith('leg.')}
    wing_indices = tuple(i for r in anatomy.regions if r.name.startswith('wing.') for i in r.vertex_indices)
    neutral_wing_span = max(mesh.parts[0].vertices[i][0] for i in wing_indices)-min(mesh.parts[0].vertices[i][0] for i in wing_indices)
    soles = {name: tuple(i for i in indices if abs(mesh.parts[0].vertices[i][2]) < 1e-8)
             for name, indices in feet.items()}
    if not all(soles.values()):
        raise ValueError('Review requires neutral sole vertices')
    from object_core.providers.avian_gait import contact_schedule
    from scripts.canine_review_metrics import stance_material_motion
    schedules = contact_schedule(duration, strength, values['body_height_cm'], provider.skeleton(values)) if clip == 'walk' else {}
    from scripts.avian_review_metrics import surface_crossings, crossing_details
    neutral_crossings = surface_crossings(mesh.parts[0].vertices, mesh.parts[0].faces)
    neutral_pairs = set(neutral_crossings)
    previous = bpy.context.window.scene
    kinds = ('objects', 'meshes', 'armatures', 'collections', 'actions', 'materials')
    before = {kind: set(getattr(bpy.data, kind)) for kind in kinds}
    scene = bpy.data.scenes.new('AvianMotionReview')
    try:
        bpy.context.window.scene = scene
        scene.render.fps, scene.render.fps_base = 24, 1
        scene.frame_start = 1
        root = create_character(mesh, scene=scene, skeleton=provider.skeleton(values),
                                skin_weights=provider.skin_weights(mesh, values))
        root['object_type'] = 'avian'
        for key, value in values.items():
            root[key] = value
        body = next(o for o in root.children if o.type == 'MESH')
        rig = next(o for o in root.children if o.type == 'ARMATURE')
        {'idle':add_idle, 'walk':add_locomotion, 'flight':add_flight}[clip](root, scene, duration, strength)
        rows, first = [], None
        maximum_motion = 0.0
        for sample in range(intervals + 1):
            frame = 1 + duration * sample / intervals * 24
            scene.frame_set(floor(frame), subframe=frame - floor(frame))
            bpy.context.view_layer.update()
            evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
            surface = evaluated.to_mesh()
            try:
                points = tuple(tuple(float(c) * 100 for c in evaluated.matrix_world @ v.co)
                               for v in surface.vertices)
            finally:
                evaluated.to_mesh_clear()
            if len(points) != mesh.vertex_count or not all(isfinite(c) for p in points for c in p):
                raise ValueError('Review requires finite unchanged evaluated topology')
            if first is None:
                first = points
            displacement = max(sum((a-b)**2 for a,b in zip(p,q))**.5 for p,q in zip(first,points))
            maximum_motion = max(maximum_motion, displacement)
            crossings = surface_crossings(points, mesh.parts[0].faces)
            rows.append(dict(phase=sample/intervals, frame=frame,
                root_head_cm=tuple(float(c)*100 for c in rig.matrix_world @ rig.pose.bones['root'].head),
                wing_span_cm=max(points[i][0] for i in wing_indices)-min(points[i][0] for i in wing_indices),
                surface_crossings=crossings,
                new_surface_crossings=sorted(set(crossings)-neutral_pairs),
                feet={name: dict(minimum_z_cm=min(points[i][2] for i in indices),
                    fixed_sole_positions_cm=[points[i] for i in soles[name]]) for name,indices in feet.items()}))
        summary = {}
        for name in feet:
            heights = [row['feet'][name]['minimum_z_cm'] for row in rows]
            worst = min(range(len(heights)), key=heights.__getitem__)
            summary[name] = dict(minimum_z_cm=heights[worst], worst_phase=rows[worst]['phase'],
                maximum_minimum_z_cm=max(heights),
                penetrating_samples=sum(z < -.02 for z in heights),
                lifted_samples=sum(z > .02 for z in heights),
                near_ground_samples=sum(abs(z) <= .02 for z in heights),
                maximum_fixed_sole_motion_cm=max(
                    sum((a-b)**2 for a,b in zip(point,initial))**.5
                    for row in rows
                    for point,initial in zip(row['feet'][name]['fixed_sole_positions_cm'],
                                             rows[0]['feet'][name]['fixed_sole_positions_cm'])))
            if name in schedules:
                schedule = schedules[name]
                summary[name]['scheduled_stance'] = stance_material_motion(
                    [row['phase'] for row in rows[:-1]],
                    [row['feet'][name]['fixed_sole_positions_cm'] for row in rows[:-1]],
                    schedule, tolerance_cm=.05)
                summary[name]['schedule'] = dict(touchdown_phase=schedule.touchdown_phase,
                    duty_factor=schedule.duty_factor, stride_cm=schedule.stride_cm,
                    requested_stride_cm=values['body_height_cm']*.08*strength,
                    stride_limited=schedule.stride_cm < values['body_height_cm']*.08*strength-1e-9,
                    swing_height_cm=schedule.swing_height_cm)
        return dict(clip=clip, parameters=values, recipe_version=anatomy.recipe_version,
                    duration=duration, strength=strength, intervals=intervals, ground_tolerance_cm=.02,
                    fixed_sole_indices=soles, maximum_surface_motion_cm=maximum_motion,
                    neutral_surface_crossings=neutral_crossings,
                    surface_crossing_details=crossing_details(mesh.parts[0].faces, anatomy.regions,
                        sorted({tuple(pair) for row in rows for pair in row["surface_crossings"]})),
                    neutral_wing_span_cm=neutral_wing_span,
                    root_vertical_range_cm=max(row['root_head_cm'][2] for row in rows)-min(row['root_head_cm'][2] for row in rows),
                    maximum_wing_span_cm=max(row['wing_span_cm'] for row in rows),
                    crossing_samples=sum(bool(row['surface_crossings']) for row in rows),
                    maximum_crossing_pairs=max(len(row['surface_crossings']) for row in rows),
                    intersection_scope='Non-adjacent surface crossings only; excludes shared-vertex faces, containment and coplanar contact.',
                    loop_closure_error_cm=displacement, summary=summary, samples=rows)
    finally:
        bpy.context.window.scene = previous
        for kind in kinds:
            data = getattr(bpy.data, kind)
            for item in set(data) - before[kind]:
                data.remove(item, do_unlink=True)
        bpy.data.scenes.remove(scene)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sample', choices=('default',) + tuple(AVIAN_REVIEW_SAMPLES), default='default')
    parser.add_argument('--intervals', type=int, default=64)
    parser.add_argument('--strength', type=float, default=1.0)
    parser.add_argument('--clips', nargs='+', choices=('idle','walk','flight'), default=('idle','walk','flight'))
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    provider = get_provider('avian')
    values = review_values(args.sample)
    report = dict(schema_version=8, sample=args.sample,
        interpretation='Sampled in-place fixed-ground heights and fixed neutral sole vertices. Walk stance uses the authored schedule and reference +Y travel; it is not physical slip proof. Flight ground heights are diagnostic only, not planted-contact requirements. Between-sample extremes are not bounded.',
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_changes=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines(),
        cycles=[review_cycle(values,clip,args.intervals,args.strength) for clip in args.clips])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({c['clip']:c['summary'] for c in report['cycles']},indent=2))


if __name__ == '__main__':
    main()
