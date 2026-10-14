# SPDX-License-Identifier: GPL-3.0-or-later
"""Render Avian neutral and coordinated joint review sheets in a fresh Blender process.

blender --background --factory-startup --python scripts/render_avian_review.py -- \
    --output artifacts/shared-anatomy/avian.png --pose neutral
"""
import argparse
import json
from math import floor, isfinite
from pathlib import Path
import subprocess
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from object_core.objects import get_provider
from object_core.providers.avian_posture import COMPACT_FOLD_ROTATIONS
from object_core.models import MeshPart
from blender_adapter.adapter import create_character
from scripts import render_human_review as sheets
from scripts.avian_review_samples import AVIAN_REVIEW_SAMPLES, review_values
from scripts.avian_review_metrics import surface_crossings

ISOLATED_POSES = {'wing-root': ('wing.upper.left', 'x', .4),
         'wing-elbow': ('wing.lower.left', 'z', .7),
         'hip': ('leg.upper.left', 'x', .4),
         'ankle': ('foot.left', 'x', .4)}

POSES = {name: (rotation,) for name, rotation in ISOLATED_POSES.items()}
# Diagnostic local-Z sweep: upper wings sweep back; elbows return the tips.
# This is not yet a production perched posture or an animation offset.
POSES['wing-fold'] = (
    ('wing.upper.left', 'z', 1.15),
    ('wing.lower.left', 'z', -2.1),
    ('wing.upper.right', 'z', -1.15),
    ('wing.lower.right', 'z', 2.1),
)

POSES['wing-fold-compact'] = COMPACT_FOLD_ROTATIONS


def evaluated_points(body):
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return tuple(tuple(float(c) * 100 for c in body.matrix_world @ v.co) for v in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()


def review_part(values, pose, phase=0., strength=1., pose_fraction=1.):
    if not isfinite(phase) or not 0 <= phase <= 1:
        raise ValueError('Review phase must be in [0, 1]')
    if not isfinite(pose_fraction) or not 0 <= pose_fraction <= 1:
        raise ValueError('Pose fraction must be in [0, 1]')
    provider = get_provider('avian')
    mesh, anatomy = provider.mesh(values), provider.anatomy(values)
    skeleton = provider.skeleton(values)
    report = {'parameters': values, 'recipe_version': anatomy.recipe_version,
              'pose': pose, 'vertices': mesh.vertex_count, 'faces': mesh.face_count,
              'bones': len(skeleton.bones), 'scope': 'Diagnostic pose, not a flight or perched acceptance test.'}
    points = mesh.parts[0].vertices
    baseline_crossings = surface_crossings(points, mesh.parts[0].faces)
    if pose != 'neutral':
        root = create_character(mesh, scene=bpy.context.scene, skeleton=skeleton,
                                skin_weights=provider.skin_weights(mesh, values))
        body = next(o for o in root.children if o.type == 'MESH')
        rig = next(o for o in root.children if o.type == 'ARMATURE')
        before = evaluated_points(body)
        baseline_crossings = surface_crossings(before, mesh.parts[0].faces)
        if pose == 'walk':
            from blender_adapter.animation import add_locomotion
            root['object_type'] = 'avian'
            for key, value in values.items():
                root[key] = value
            scene = bpy.context.scene
            duration = 1.2
            add_locomotion(root, scene, duration, strength)
            frame = scene.frame_start + duration * phase * scene.render.fps / scene.render.fps_base
            scene.frame_set(floor(frame), subframe=frame-floor(frame))
            report.update(phase=phase, strength=strength, frame=frame,
                          scope='Actual generated Walk action at the specified cycle phase.')
        else:
            for name, axis, angle in POSES[pose]:
                bone = rig.pose.bones[name]
                bone.rotation_mode = 'XYZ'
                setattr(bone.rotation_euler, axis, angle * pose_fraction)
            report['rotations'] = [dict(bone=name, axis=axis, radians=angle * pose_fraction)
                                   for name, axis, angle in POSES[pose]]
        points = evaluated_points(body)
        if pose in ISOLATED_POSES:
            name, axis, angle = ISOLATED_POSES[pose]
            report.update(bone=name, rotation_axis=axis, rotation_radians=angle * pose_fraction)
        wing_indices = [i for r in anatomy.regions if r.name.startswith('wing.')
                        for i in r.vertex_indices]
        report['wing_span_cm'] = {
            label: max(vertices[i][0] for i in wing_indices) - min(vertices[i][0] for i in wing_indices)
            for label, vertices in (('neutral', before), ('posed', points))}
        report['region_max_displacement_cm'] = {
            r.name: max(sum((points[i][a] - before[i][a]) ** 2 for a in range(3)) ** .5
                        for i in r.vertex_indices) for r in anatomy.regions}
    report['nonadjacent_surface_crossings'] = surface_crossings(points, mesh.parts[0].faces)
    report['neutral_surface_crossings'] = baseline_crossings
    report['new_surface_crossings'] = sorted(set(report['nonadjacent_surface_crossings']) - set(baseline_crossings))
    report['intersection_scope'] = 'Non-adjacent triangle surface crossings; excludes shared-vertex faces, containment and coplanar contact.'
    report['feet'] = {}
    foot_points = []
    for region in anatomy.regions:
        if region.name.startswith('leg.'):
            vertices = [points[i] for i in region.vertex_indices[24:]]
            contact = [p for p in vertices if abs(p[2]) < 1e-5]
            report['feet'][region.name] = {
                'minimum_z_cm': min(p[2] for p in vertices),
                'ground_vertex_count': len(contact),
                'contact_width_cm': max((p[0] for p in contact), default=0) - min((p[0] for p in contact), default=0),
                'contact_length_cm': max((p[1] for p in contact), default=0) - min((p[1] for p in contact), default=0)}
            foot_points.extend(vertices)
    report['foot_bounds_cm'] = sheets._bounds(foot_points)
    report['minimum_surface_z_cm'] = min(p[2] for p in points)
    return MeshPart('avian', points, mesh.parts[0].faces), report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sample', choices=('default',) + tuple(AVIAN_REVIEW_SAMPLES), default='default')
    parser.add_argument('--pose', choices=('neutral', 'walk') + tuple(POSES), default='neutral')
    parser.add_argument('--pose-fraction', type=float, default=1., help='Fraction of diagnostic joint rotations, 0..1')
    parser.add_argument('--phase', type=float, default=0.)
    parser.add_argument('--strength', type=float, default=1.)
    parser.add_argument('--view', choices=('four-view', 'top', 'feet', 'side'), default='four-view')
    parser.add_argument('--samples', type=int, default=8)
    parser.add_argument('--resolution-x', type=int, default=1600)
    parser.add_argument('--resolution-y', type=int, default=600)
    parser.add_argument('--modes', nargs='+', choices=sheets.REVIEW_MODES, default=['clay'])
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    provider = get_provider('avian')
    values = review_values(args.sample)
    sheets._clear_scene()
    part, report = review_part(values, args.pose, args.phase, args.strength, args.pose_fraction)
    sheets._clear_scene()
    if args.view == 'feet':
        anatomy = provider.anatomy(values)
        leg_indices = {i for r in anatomy.regions if r.name.startswith('leg.') for i in r.vertex_indices}
        part = MeshPart('avian-feet', part.vertices,
                        tuple(face for face in part.faces if set(face) <= leg_indices))
    material = sheets._configure_scene(args, part)
    if args.view in ('top', 'feet', 'side'):
        # Reuse the review material/render setup, then frame one overhead bird.
        scene = bpy.context.scene
        body = next(o for o in scene.objects if o.type == 'MESH')
        for obj in list(scene.objects):
            if obj != body and obj.type in ('MESH', 'FONT', 'LIGHT'):
                bpy.data.objects.remove(obj, do_unlink=True)
        body.location = (0, 0, 0)
        body.rotation_euler = (0, 0, 0)
        low, high = sheets._bounds(part.vertices)
        if args.view == 'feet':
            low, high = report['foot_bounds_cm']
        width, depth = high[0] - low[0], high[1] - low[1]
        center = tuple((a + b) / 2 for a, b in zip(low, high))
        camera = scene.camera
        camera.location = (center[0], center[1], high[2] + max(width, depth) * 2)
        camera.rotation_euler = (0, 0, 0)
        camera.data.ortho_scale = max(width, depth * args.resolution_x / args.resolution_y) * 1.12
        camera.data.clip_end = max(width, depth) * 5
        sheets._add_lighting(center[2], width, high[2] - low[2])
        bpy.context.view_layer.update()
        if args.view == 'feet':
            from mathutils import Vector
            span = max(width, depth)
            camera.location = (center[0] + span, center[1] + span, center[2] + span * .7)
            camera.rotation_euler = (Vector(center) - camera.location).to_track_quat('-Z', 'Y').to_euler()
            camera.data.ortho_scale = span * 1.7
            report['framing'] = 'Isolated leg surfaces; torso, wings and attachment bridges hidden for foot inspection.'
        elif args.view == 'side':
            from mathutils import Vector
            camera.location = (high[0] + max(width, depth) * 2, center[1], center[2])
            camera.rotation_euler = (Vector(center) - camera.location).to_track_quat('-Z', 'Y').to_euler()
            camera.data.ortho_scale = max(depth, (high[2] - low[2]) * args.resolution_x / args.resolution_y) * 1.12
            bpy.context.view_layer.update()
            sheets._validate_camera_frame(camera, [body], scene)
        else:
            sheets._validate_camera_frame(camera, [body], scene)
    report['view'] = args.view
    for mode in args.modes:
        sheets._configure_material(material, mode)
        bpy.context.scene.render.filepath = str(sheets._mode_output(args.output, mode))
        bpy.ops.render.render(write_still=True)
    report['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    report['working_tree_changes'] = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines()
    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
