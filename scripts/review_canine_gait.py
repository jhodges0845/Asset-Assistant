# SPDX-License-Identifier: GPL-3.0-or-later
"""Sample real Blender walk/run deformation against the fixed Z=0 ground plane.

blender --background --factory-startup --python scripts/review_canine_gait.py -- \
    --output artifacts/shared-anatomy/canine-gait.json --sample default

This measures an in-place cycle against declared stance and reference travel.
Reference-compensated sole drift is not generated root motion or physical contact
area. Samples cannot bound between-sample peaks.
"""
from __future__ import annotations

import argparse
import json
from math import floor, hypot, isfinite
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from object_core.objects import get_provider
from object_core.providers.quadruped import _construction
from object_core.providers.quadruped_gait import contact_schedule
from scripts.canine_review_metrics import limb_ground_clearance, limb_support_footprint


def review_cycle(values, clip='walk', duration=None, strength=1.0, intervals=32):
    """Create an isolated scene, sample its generated action, then remove it.

    A fixed set of neutral sole vertices supplies a material-patch centroid;
    tracking the lowest posed vertex instead would switch points during a bend.
    All positions are evaluated in world centimeters, including rig deformation.
    """
    import bpy
    from blender_adapter.adapter import create_character
    from blender_adapter.animation import add_locomotion, add_run

    if clip not in ('walk', 'run'):
        raise ValueError('Gait review supports walk or run')
    if isinstance(intervals, bool) or not isinstance(intervals, int) or not 4 <= intervals <= 256:
        raise ValueError('Gait review requires 4..256 sampling intervals')
    duration = (1.2 if clip == 'walk' else .64) if duration is None else duration
    provider = get_provider('quadruped')
    # Validate clip parameters before allocating Blender data.
    getattr(provider, 'locomotion' if clip == 'walk' else 'run')(duration, strength, values=values)
    mesh, anatomy = _construction(provider.dimensions(values))
    sole_indices = {r.name: tuple(i for i in r.vertex_indices
                    if 0 <= mesh.parts[0].vertices[i][2] <= .1)
                    for r in anatomy.regions if r.name.startswith('leg.')}
    if not all(sole_indices.values()):
        raise ValueError('Gait review requires neutral sole vertices in Z=0..0.1 cm')
    schedules = contact_schedule(duration, strength, values['shoulder_height_cm'], clip == 'run')
    neutral_y = {name: sum(mesh.parts[0].vertices[i][1] for i in indices) / len(indices)
                 for name, indices in sole_indices.items()}
    previous_scene = bpy.context.window.scene
    collections = ('objects', 'meshes', 'armatures', 'collections', 'actions', 'materials')
    before = {name: set(getattr(bpy.data, name)) for name in collections}
    scene = bpy.data.scenes.new('CanineGaitReview')
    try:
        bpy.context.window.scene = scene
        scene.render.fps = 24
        scene.render.fps_base = 1
        scene.frame_start = 1
        root = create_character(mesh, name='CanineGaitReview', scene=scene,
                                skeleton=provider.skeleton(values),
                                skin_weights=provider.skin_weights(mesh, values))
        root['object_type'] = provider.key
        for key, value in values.items():
            root[key] = value
        body = next(obj for obj in root.children if obj.type == 'MESH')
        (add_locomotion if clip == 'walk' else add_run)(root, scene, duration, strength)
        frames = []
        first_points = None
        maximum_motion = 0.0
        for index in range(intervals + 1):
            seconds = duration * index / intervals
            frame = scene.frame_start + seconds * scene.render.fps / scene.render.fps_base
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
                raise ValueError('Gait review requires finite, unchanged evaluated topology')
            if first_points is None:
                first_points = points
            maximum_motion = max(maximum_motion, max(
                sum((a - b) ** 2 for a, b in zip(p, q)) ** .5
                for p, q in zip(first_points, points)))
            centroids = {name: tuple(sum(points[i][axis] for i in indices) / len(indices)
                                     for axis in range(3))
                         for name, indices in sole_indices.items()}
            frames.append(dict(phase=index / intervals, seconds=seconds, frame=frame,
                               ground_clearance=limb_ground_clearance(points, anatomy.regions),
                               support_footprint=limb_support_footprint(
                                   points, mesh.parts[0].faces, anatomy.regions),
                               sole_centroid_cm=centroids,
                               contact_targets={name: asdict(schedule.target(index / intervals))
                                                for name, schedule in schedules.items()}))
        summary = {}
        for name in sole_indices:
            heights = [r['ground_clearance'][name]['minimum_z_cm'] for r in frames]
            centers = [r['sole_centroid_cm'][name] for r in frames]
            worst = min(range(len(heights)), key=heights.__getitem__)
            schedule = schedules[name]
            # Repeat the closed cycle to measure one complete stance even when
            # it crosses phase zero. Root travel is a reference, not animation.
            stance = []
            for turn in (0, 1):
                for row in frames[:-1]:
                    phase = turn + row['phase']
                    if schedule.touchdown_phase <= phase < schedule.touchdown_phase + schedule.duty_factor:
                        point = row['sole_centroid_cm'][name]
                        stance.append((point[0], point[1] + phase * schedule.stride_cm))
            drift = max((hypot(a[0]-b[0], a[1]-b[1]) for a in stance for b in stance), default=0.)
            summary[name] = dict(
                reference_stance_samples=len(stance), reference_stance_drift_cm=drift,
                maximum_forward_target_error_cm=max(abs(row['sole_centroid_cm'][name][1] - neutral_y[name]
                    - row['contact_targets'][name]['forward_cm']) for row in frames),
                maximum_clearance_target_error_cm=max(abs(row['ground_clearance'][name]['minimum_z_cm']
                    - row['contact_targets'][name]['lift_cm'] - .02) for row in frames),
                minimum_z_cm=min(heights), maximum_z_cm=max(heights),
                maximum_penetration_cm=max(0.0, -min(heights)),
                worst_phase=frames[worst]['phase'],
                sole_centroid_xy_excursion_cm=max(hypot(a[0] - b[0], a[1] - b[1])
                                                  for a in centers for b in centers))
        return dict(parameters=dict(values), recipe_version=anatomy.recipe_version,
                    blender_version=bpy.app.version_string,
                    clip=clip, duration_seconds=duration, strength=strength,
                    gait='diagonal_running_trot' if clip == 'run' else 'four_beat_walk',
                    contact_reference={name: dict(asdict(schedule), reference_speed_cm_s=schedule.reference_speed_cm_s)
                                       for name, schedule in schedules.items()},
                    intervals=intervals, fps=24, ground_plane_z_cm=0.0,
                    sole_selection_band_cm=[0.0, .1], sole_vertex_indices=sole_indices,
                    vertices=mesh.vertex_count, faces=mesh.face_count,
                    maximum_vertex_motion_cm=maximum_motion,
                    loop_closure_error_cm=max(sum((a - b) ** 2 for a, b in zip(p, q)) ** .5
                                              for p, q in zip(first_points, points)),
                    limbs=summary, frames=frames)
    finally:
        bpy.context.window.scene = previous_scene
        for name in collections:
            data = getattr(bpy.data, name)
            for item in set(data) - before[name]:
                data.remove(item, do_unlink=True)
        bpy.data.scenes.remove(scene)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sample', choices=('default', 'contrasting', 'short-wide'), default='default')
    parser.add_argument('--intervals', type=int, default=32)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    provider = get_provider('quadruped')
    values = {p.key: p.default for p in provider.parameters}
    if args.sample == 'contrasting':
        values.update(body_length_cm=95, shoulder_height_cm=40, body_width_cm=28,
                      head_length_cm=30, tail_length_cm=50)
    elif args.sample == 'short-wide':
        values.update(body_length_cm=25, shoulder_height_cm=15, body_width_cm=55,
                      head_length_cm=8, tail_length_cm=5)
    report = dict(schema_version=2, sample=args.sample,
        interpretation='In-place sampled diagnostics with declared stance and reference travel; drift is measured after reference +Y travel, not generated root motion or physical contact area.',
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        working_tree_changes=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines(),
        cycles=[review_cycle(values, clip, intervals=args.intervals) for clip in ('walk', 'run')])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('CANINE_GAIT_REVIEW_OK', args.output)


if __name__ == '__main__':
    main()
