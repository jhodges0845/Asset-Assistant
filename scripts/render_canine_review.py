# SPDX-License-Identifier: GPL-3.0-or-later
"""Render canine clay/silhouette/wireframe sheets through the real provider.

blender --background --factory-startup --python scripts/render_canine_review.py -- \
    --output artifacts/shared-anatomy/canine-neutral.png --sample default
Use --pose knee or hock for independently evaluated hind-left joint diagnostics.
The adjacent JSON records parameters, counts, recipe version and pose movement.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from object_core.objects import get_provider
from object_core.models import MeshPart
from object_core.providers.quadruped import _construction
from blender_adapter.adapter import create_character
# These existing mesh/material/camera helpers are independent of Human anatomy.
from scripts import render_human_review as sheets


def evaluated_points(body):
    bpy.context.view_layer.update()
    obj = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = obj.to_mesh()
    try:
        return tuple(vertex.co.copy() for vertex in mesh.vertices)
    finally:
        obj.to_mesh_clear()


def review_part(values, pose):
    provider = get_provider('quadruped')
    mesh, anatomy = _construction(provider.dimensions(values))
    skeleton = provider.skeleton(values)
    evidence = {'parameters': values, 'recipe_id': anatomy.recipe_id,
                'recipe_version': anatomy.recipe_version, 'pose': pose,
                'vertices': mesh.vertex_count, 'faces': mesh.face_count,
                'bones': len(skeleton.bones),
                'landmarks': [asdict(p) for p in anatomy.landmarks]}
    if pose == 'neutral':
        return mesh.parts[0], evidence
    root = create_character(mesh, name='CaninePoseReview', scene=bpy.context.scene,
                            skeleton=skeleton, skin_weights=provider.skin_weights(mesh, values))
    body = next(o for o in root.children if o.type == 'MESH')
    rig = next(o for o in root.children if o.type == 'ARMATURE')
    before = evaluated_points(body)
    bone_name, angle = {'knee': ('hind_lower.left', -.45),
                        'hock': ('hind_pastern.left', .45)}[pose]
    bone = rig.pose.bones[bone_name]
    bone.rotation_mode = 'XYZ'
    bone.rotation_euler.x = angle
    after = evaluated_points(body)
    owned = set(next(r.vertex_indices for r in anatomy.regions if r.name == 'leg.hind.left'))
    displacement = max((after[i] - before[i]).length for i in owned)
    # Other authored limbs must not acquire the diagnostic joint's weights.
    other = {i for r in anatomy.regions if r.name.startswith('leg.')
             and r.name != 'leg.hind.left' for i in r.vertex_indices}
    leakage = max((after[i] - before[i]).length for i in other)
    if displacement < .001 or leakage > 1e-6:
        raise RuntimeError('Canine diagnostic pose failed movement/isolation checks')
    evidence.update(bone=bone_name, angle_radians=angle,
                    limb_displacement_cm=displacement * 100,
                    other_limb_displacement_cm=leakage * 100)
    part = MeshPart(mesh.parts[0].name,
                    tuple(tuple(float(c) * 100 for c in point) for point in after),
                    mesh.parts[0].faces)
    return part, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sample', choices=('default', 'contrasting'), default='default')
    parser.add_argument('--pose', choices=('neutral', 'knee', 'hock'), default='neutral')
    parser.add_argument('--samples', type=int, default=4)
    parser.add_argument('--resolution-x', type=int, default=1200)
    parser.add_argument('--resolution-y', type=int, default=500)
    parser.add_argument('--modes', nargs='+', choices=sheets.REVIEW_MODES,
                        default=list(sheets.REVIEW_MODES))
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    provider = get_provider('quadruped')
    values = {p.key: p.default for p in provider.parameters}
    if args.sample == 'contrasting':
        values.update(body_length_cm=95, shoulder_height_cm=40, body_width_cm=28,
                      head_length_cm=30, tail_length_cm=50)
    sheets._clear_scene()
    part, evidence = review_part(values, args.pose)
    sheets._clear_scene()
    material = sheets._configure_scene(args, part)
    label_material = bpy.data.materials.new('Canine review labels')
    label_material.use_nodes = True
    sheets._configure_silhouette_material(label_material)
    for obj in bpy.context.scene.objects:
        if obj.type == 'FONT':
            obj.data.materials.append(label_material)
            obj.data.size *= 1.5
    for mode in args.modes:
        sheets._configure_material(material, mode)
        bpy.context.scene.render.filepath = str(sheets._mode_output(args.output, mode))
        bpy.ops.render.render(write_still=True)
    evidence['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    evidence['working_tree_changes'] = subprocess.check_output(
        ['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines()
    args.output.with_suffix('.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
