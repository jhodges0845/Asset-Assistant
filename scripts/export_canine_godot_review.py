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
from blender_adapter.animation import add_idle, add_locomotion, add_run, activate_generated_action, action_curves
from blender_adapter.materials import prepare_materials
from blender_adapter.targets import get_adapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sample', choices=('default', 'contrasting', 'short-wide'), default='default')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if (args.output / 'canine.glb').exists():
        parser.error('--output must be a fresh fixture directory')
    args.output.mkdir(parents=True, exist_ok=True)
    provider = get_provider('quadruped')
    values = {p.key: p.default for p in provider.parameters}
    if args.sample == 'contrasting':
        values.update(body_length_cm=95, shoulder_height_cm=40, body_width_cm=28,
                      head_length_cm=30, tail_length_cm=50)
    elif args.sample == 'short-wide':
        values.update(body_length_cm=25, shoulder_height_cm=15, body_width_cm=55,
                      head_length_cm=8, tail_length_cm=5)
    scene = bpy.data.scenes.new('Canine Godot oracle')
    bpy.context.window.scene = scene
    scene.render.fps = 24
    scene.render.fps_base = 1
    scene.frame_start = 1
    mesh = provider.mesh(values)
    root = create_character(mesh, scene=scene, skeleton=provider.skeleton(values),
                            skin_weights=provider.skin_weights(mesh, values))
    root['object_type'] = 'quadruped'
    for key, value in values.items():
        root[key] = value
    prepare_materials(root)
    add_idle(root, scene, 4., 1.)
    add_locomotion(root, scene, 1.2, 1.)
    add_run(root, scene, .64, 1.)
    result = get_adapter('GODOT', asset_use='ANIMATED').export(root, bpy.context, args.output / 'canine.glb')
    if not result.success:
        raise RuntimeError(result.issues)
    rig = next(o for o in root.children if o.type == 'ARMATURE')
    clips = {}
    for name, duration in (('Walk', 1.2), ('Idle', 4.), ('Run', .64)):
        action = activate_generated_action(root, name)
        curves = action_curves(action, action.slots[0])
        intervals = max(len(c.keyframe_points) - 1 for c in curves)
        for curve in curves:
            for key in curve.keyframe_points:
                phase_index = (key.co.x - action.frame_range[0]) / (duration * 24) * intervals
                if abs(phase_index - round(phase_index)) > .001:
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
            samples.append(dict(seconds=seconds, bones=bones))
        clips[name] = dict(duration=duration, import_bake_fps=intervals / duration, samples=samples)
    report = dict(schema_version=1, sample=args.sample, parameters=values,
                  blender_version=bpy.app.version_string,
                  commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  tolerance_cm=.002, clips=clips)
    (args.output / 'expected.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'project.godot').write_text('config_version=5\n[application]\nconfig/name="Canine playback probe"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    shutil.copyfile(ROOT / 'scripts/review_canine_godot.gd', args.output / 'review.gd')
    shutil.copyfile(ROOT / 'scripts/canine_godot_import.gd', args.output / 'canine_import.gd')
    shutil.copyfile(ROOT / 'scripts/render_canine_godot.gd', args.output / 'render.gd')
    print('CANINE_GODOT_FIXTURE_OK', args.output)


if __name__ == '__main__':
    main()
