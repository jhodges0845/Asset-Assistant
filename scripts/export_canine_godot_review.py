# SPDX-License-Identifier: GPL-3.0-or-later
"""Export a canine GLB and Blender pose oracle for review_canine_godot.gd.

Run in a fresh Blender background process with --output DIRECTORY.
"""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from object_core.objects import get_provider
from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle, add_locomotion, add_run, add_flight, activate_generated_action, action_curves
from blender_adapter.materials import prepare_materials
from blender_adapter.targets import get_adapter


def main(provider_key='quadruped'):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--surface', action='store_true', help='Also sample 127-interval Blender skin-contact oracles')
    parser.add_argument('--sample', choices=('default', 'contrasting', 'short-wide'), default='default')
    parser.add_argument('--chest-amount',type=float,help='Avian powerful-chest edit before export')
    parser.add_argument('--edit-amount', type=float, help='Human broad-shoulder or Canine broad-chest edit')
    parser.add_argument('--posed-surface',action='store_true',help='Sample full evaluated surfaces for Godot')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.chest_amount is not None and (provider_key != 'avian' or not math.isfinite(args.chest_amount) or not 0 < args.chest_amount <= 1.5):
        parser.error('--chest-amount requires Avian and a finite amount in (0, 1.5]')
    if args.edit_amount is not None and (provider_key not in ('human', 'quadruped') or not math.isfinite(args.edit_amount) or not 0 < args.edit_amount <= 1.5):
        parser.error('--edit-amount requires Human/Canine and a finite amount in (0, 1.5]')
    if args.surface and args.edit_amount is not None:
        parser.error('Edited fixtures require --posed-surface; the contact-only oracle uses unedited geometry')
    if provider_key == 'human' and (args.sample != 'default' or args.surface):
        parser.error('Human currently supports the default sample and --posed-surface only')
    args.output = args.output.resolve()
    if (args.output / 'canine.glb').exists():
        parser.error('--output must be a fresh fixture directory')
    args.output.mkdir(parents=True, exist_ok=True)
    provider = get_provider(provider_key)
    values = {p.key: p.default for p in provider.parameters}
    if args.sample == 'contrasting':
        values.update(body_length_cm=95, shoulder_height_cm=40, body_width_cm=28,
                      head_length_cm=30, tail_length_cm=50)
    elif args.sample == 'short-wide':
        values.update(body_length_cm=25, shoulder_height_cm=15, body_width_cm=55,
                      head_length_cm=8, tail_length_cm=5)
    if provider_key == 'avian':
        if args.surface or args.sample == 'short-wide':
            parser.error('Avian uses default/contrasting pose review; canine surface probes are separate')
        from scripts.avian_review_samples import review_values
        values = review_values(args.sample)
    scene = bpy.data.scenes.new('Generated character Godot oracle')
    bpy.context.window.scene = scene
    scene.render.fps = 24
    scene.render.fps_base = 1
    scene.frame_start = 1
    mesh = provider.mesh(values)
    root = create_character(mesh, scene=scene, skeleton=provider.skeleton(values),
                            skin_weights=provider.skin_weights(mesh, values))
    root['object_type'] = provider_key
    for key, value in values.items():
        root[key] = value
    semantic_operations = []
    neutral_positions = None
    if args.chest_amount is not None or args.edit_amount is not None:
        from object_core.modification import SemanticOperation, ModificationRequest, plan_modification
        from blender_adapter.modification import inspect_generated_asset, apply_semantic_modification
        target = 'shoulders' if provider_key == 'human' else 'chest'
        profile = 'powerful' if provider_key == 'avian' else 'broad'
        amount = args.chest_amount if provider_key == 'avian' else args.edit_amount
        operation = SemanticOperation('shape',target,(('profile',profile),('amount',amount)))
        plan = plan_modification(inspect_generated_asset(root),ModificationRequest(semantic_operations=(operation,)))
        if not plan.safe_to_apply:
            raise RuntimeError('Semantic export fixture requires a safe plan')
        snapshot = apply_semantic_modification(root,plan)
        if not snapshot.owns_geometry:
            raise RuntimeError('Semantic export fixture lost geometry ownership')
        semantic_operations = [dict(operation=operation.operation,target=operation.target,arguments=operation.argument_values())]
    if args.chest_amount is not None or args.edit_amount is not None or args.posed_surface:
        bpy.context.view_layer.update()
        body = next(o for o in root.children if o.type == 'MESH')
        neutral_positions = []
        for vertex in body.data.vertices:
            point = body.matrix_world @ vertex.co
            neutral_positions.append([point.x,point.z,-point.y])
    prepare_materials(root)
    run_duration = .72 if provider_key == 'human' else .64
    add_idle(root, scene, 4., 1.)
    add_locomotion(root, scene, 1.2, 1.)
    if provider_key == 'avian':
        add_flight(root,scene,1.2,1.)
    else:
        add_run(root, scene, run_duration, 1.)
    result = get_adapter('GODOT', asset_use='ANIMATED').export(root, bpy.context, args.output / 'canine.glb')
    if not result.success:
        raise RuntimeError(result.issues)
    rig = next(o for o in root.children if o.type == 'ARMATURE')
    clips = {}
    for name, duration in (('Walk', 1.2), ('Idle', 4.), ('Flight',1.2) if provider_key == 'avian' else ('Run', run_duration)):
        action = activate_generated_action(root, name)
        curves = action_curves(action, action.slots[0])
        intervals = max(len(c.keyframe_points) - 1 for c in curves)
        for curve in curves:
            for key in curve.keyframe_points:
                phase_index = (key.co.x - action.frame_range[0]) / (duration * 24) * intervals
                if provider_key != 'human' and abs(phase_index - round(phase_index)) > .001:
                    raise ValueError('Source-aligned import requires a uniform key grid')
        samples = []
        for step in range(34):
            seconds = duration * step / 33
            frame = 1 + seconds * 24
            scene.frame_set(math.floor(frame), subframe=frame % 1)
            bpy.context.view_layer.update()
            bones = {}
            for bone in rig.pose.bones:
                p = rig.matrix_world @ bone.matrix.translation
                # Blender Z-up to glTF/Godot Y-up; world coordinates are meters.
                bones[bone.name] = [p.x, p.z, -p.y]
            row = dict(seconds=seconds, bones=bones)
            if args.posed_surface:
                evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
                surface = evaluated.to_mesh()
                try:
                    points = [evaluated.matrix_world @ vertex.co for vertex in surface.vertices]
                    row['positions_m'] = [[p.x,p.z,-p.y] for p in points]
                finally:
                    evaluated.to_mesh_clear()
            samples.append(row)
        clips[name] = dict(duration=duration, import_bake_fps=None if provider_key == 'human' else intervals / duration, samples=samples)
    report = dict(schema_version=1, provider=provider_key, sample=args.sample, parameters=values,
                  playback_sequence=['Walk','Idle','Flight' if provider_key=='avian' else 'Run','Idle'],
                  blender_version=bpy.app.version_string,
                  commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  tolerance_cm=.002, clips=clips,semantic_operations=semantic_operations)
    if neutral_positions is not None:
        report['neutral_positions_m'] = neutral_positions
    (args.output / 'expected.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'project.godot').write_text('config_version=5\n[application]\nconfig/name="Canine playback probe"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    shutil.copyfile(ROOT / 'scripts/review_canine_godot.gd', args.output / 'review.gd')
    shutil.copyfile(ROOT / 'scripts/canine_godot_import.gd', args.output / 'canine_import.gd')
    shutil.copyfile(ROOT / 'scripts/prepare_canine_godot_scene.gd', args.output / 'prepare_scene.gd')
    shutil.copyfile(ROOT / 'scripts/package_canine_godot_review.gd', args.output / 'package_review.gd')
    shutil.copyfile(ROOT / 'scripts/render_canine_godot.gd', args.output / 'render.gd')
    shutil.copyfile(ROOT / 'scripts/review_canine_godot_surface.gd', args.output / 'surface.gd')
    if args.posed_surface:
        shutil.copyfile(ROOT / 'scripts/review_avian_godot_skin.gd', args.output / 'skin.gd')
    if args.surface:
        from scripts.review_canine_gait import review_cycle
        cycles = [review_cycle(values, clip, intervals=127) for clip in ('walk', 'run')]
        neutral = {name: mesh.parts[0].vertices[index]
                   for name, index in cycles[0]['roll_pivot_vertex_indices'].items()}
        surface = dict(schema_version=1, sample=args.sample, neutral_pivots_cm=neutral,
                       cycles=cycles, tolerance_cm=.002)
        (args.output / 'surface-expected.json').write_text(json.dumps(surface) + '\n')
    print('CANINE_GODOT_FIXTURE_OK', args.output)


if __name__ == '__main__':
    main()
