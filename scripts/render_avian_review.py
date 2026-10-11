# SPDX-License-Identifier: GPL-3.0-or-later
"""Render Avian neutral and coordinated joint review sheets in a fresh Blender process.

blender --background --factory-startup --python scripts/render_avian_review.py -- \
    --output artifacts/shared-anatomy/avian.png --pose neutral
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from object_core.objects import get_provider
from object_core.models import MeshPart
from blender_adapter.adapter import create_character
from scripts import render_human_review as sheets
from scripts.anatomy_baseline import SAMPLES

ISOLATED_POSES = {'wing-root': ('wing.upper.left', 'x', .4),
         'wing-elbow': ('wing.lower.left', 'z', .7),
         'hip': ('leg.upper.left', 'x', .4),
         'ankle': ('foot.left', 'x', .4)}

POSES = {name: (rotation,) for name, rotation in ISOLATED_POSES.items()}
# Diagnostic local-Z sweep: upper wings sweep back; elbows return the tips.
# This is not yet a production perched posture or an animation offset.
POSES['wing-fold'] = (
    ('wing.upper.left', 'z', 1.15),
    ('wing.lower.left', 'z', -2.0),
    ('wing.upper.right', 'z', -1.15),
    ('wing.lower.right', 'z', 2.0),
)



def evaluated_points(body):
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return tuple(tuple(float(c) * 100 for c in body.matrix_world @ v.co) for v in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()


def review_part(values, pose):
    provider = get_provider('avian')
    mesh, anatomy = provider.mesh(values), provider.anatomy(values)
    skeleton = provider.skeleton(values)
    report = {'parameters': values, 'recipe_version': anatomy.recipe_version,
              'pose': pose, 'vertices': mesh.vertex_count, 'faces': mesh.face_count,
              'bones': len(skeleton.bones), 'scope': 'Diagnostic pose, not a flight or perched acceptance test.'}
    points = mesh.parts[0].vertices
    if pose != 'neutral':
        root = create_character(mesh, scene=bpy.context.scene, skeleton=skeleton,
                                skin_weights=provider.skin_weights(mesh, values))
        body = next(o for o in root.children if o.type == 'MESH')
        rig = next(o for o in root.children if o.type == 'ARMATURE')
        before = evaluated_points(body)
        for name, axis, angle in POSES[pose]:
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'XYZ'
            setattr(bone.rotation_euler, axis, angle)
        points = evaluated_points(body)
        report['rotations'] = [dict(bone=name, axis=axis, radians=angle)
                               for name, axis, angle in POSES[pose]]
        if pose in ISOLATED_POSES:
            name, axis, angle = ISOLATED_POSES[pose]
            report.update(bone=name, rotation_axis=axis, rotation_radians=angle)
        wing_indices = [i for r in anatomy.regions if r.name.startswith('wing.')
                        for i in r.vertex_indices]
        report['wing_span_cm'] = {
            label: max(vertices[i][0] for i in wing_indices) - min(vertices[i][0] for i in wing_indices)
            for label, vertices in (('neutral', before), ('posed', points))}
        report['region_max_displacement_cm'] = {
            r.name: max(sum((points[i][a] - before[i][a]) ** 2 for a in range(3)) ** .5
                        for i in r.vertex_indices) for r in anatomy.regions}
    report['minimum_surface_z_cm'] = min(p[2] for p in points)
    return MeshPart('avian', points, mesh.parts[0].faces), report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sample', choices=('default', 'contrasting'), default='default')
    parser.add_argument('--pose', choices=('neutral',) + tuple(POSES), default='neutral')
    parser.add_argument('--view', choices=('four-view', 'top'), default='four-view')
    parser.add_argument('--samples', type=int, default=8)
    parser.add_argument('--resolution-x', type=int, default=1600)
    parser.add_argument('--resolution-y', type=int, default=600)
    parser.add_argument('--modes', nargs='+', choices=sheets.REVIEW_MODES, default=['clay'])
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    provider = get_provider('avian')
    values = {p.key: p.default for p in provider.parameters}
    if args.sample == 'contrasting':
        values.update(SAMPLES['avian'])
    sheets._clear_scene()
    part, report = review_part(values, args.pose)
    sheets._clear_scene()
    material = sheets._configure_scene(args, part)
    if args.view == 'top':
        # Reuse the review material/render setup, then frame one overhead bird.
        scene = bpy.context.scene
        body = next(o for o in scene.objects if o.type == 'MESH')
        for obj in list(scene.objects):
            if obj != body and obj.type in ('MESH', 'FONT', 'LIGHT'):
                bpy.data.objects.remove(obj, do_unlink=True)
        body.location = (0, 0, 0)
        body.rotation_euler = (0, 0, 0)
        low, high = sheets._bounds(part.vertices)
        width, depth = high[0] - low[0], high[1] - low[1]
        center = tuple((a + b) / 2 for a, b in zip(low, high))
        camera = scene.camera
        camera.location = (center[0], center[1], high[2] + max(width, depth) * 2)
        camera.rotation_euler = (0, 0, 0)
        camera.data.ortho_scale = max(width, depth * args.resolution_x / args.resolution_y) * 1.12
        camera.data.clip_end = max(width, depth) * 5
        sheets._add_lighting(center[2], width, high[2] - low[2])
        bpy.context.view_layer.update()
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
