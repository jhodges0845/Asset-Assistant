# SPDX-License-Identifier: GPL-3.0-or-later
"""Save a four-view, three-cycle canine review scene with real editable actions.

Run in a fresh Blender background process. --render writes an MP4 beside the
.blend file. The saved scene is a diagnostic artifact, not a generated asset.
"""
from __future__ import annotations
import argparse
from math import ceil
from pathlib import Path
import sys
from types import SimpleNamespace

import bpy
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from object_core.objects import get_provider
from object_core.models import MeshPart
from blender_adapter.adapter import create_character
from blender_adapter.animation import add_locomotion, add_run
from scripts import render_human_review as sheets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--gait', choices=('walk', 'run'), default='walk')
    parser.add_argument('--sample', choices=('default', 'contrasting'), default='default')
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.output.suffix.lower() != '.blend':
        parser.error('--output must end in .blend')
    provider = get_provider('quadruped')
    values = {p.key:p.default for p in provider.parameters}
    if args.sample == 'contrasting':
        values.update(body_length_cm=95, shoulder_height_cm=40, body_width_cm=28,
                      head_length_cm=30, tail_length_cm=50)
    mesh = provider.mesh(values)
    part = mesh.parts[0]
    meters = MeshPart(part.name, tuple(tuple(c*.01 for c in v) for v in part.vertices), part.faces)
    scene = bpy.data.scenes.new('Canine three-cycle review')
    bpy.context.window.scene = scene
    material = sheets._configure_scene(SimpleNamespace(resolution_x=1200, resolution_y=500, samples=4), meters)
    placeholders = [o for o in scene.objects if o.type == 'MESH']
    duration = 1.2 if args.gait == 'walk' else .64
    scene.render.fps = 25
    scene.render.fps_base = 1
    scene.frame_start = 1
    # 25 fps represents both canonical cycle lengths in whole frames.
    for placeholder in placeholders:
        root = create_character(mesh, name='Canine '+placeholder.name.removeprefix('Human '),
                                scene=scene, skeleton=provider.skeleton(values),
                                skin_weights=provider.skin_weights(mesh, values))
        root['object_type'] = 'quadruped'
        for key,value in values.items():
            root[key] = value
        (add_locomotion if args.gait == 'walk' else add_run)(root, scene, duration, 1.)
        root.location = placeholder.location
        root.rotation_euler = placeholder.rotation_euler
        body = next(o for o in root.children if o.type == 'MESH')
        body.data.materials.clear()
        body.data.materials.append(material)
        for obj in root.children:
            if obj.type == 'ARMATURE':
                obj.hide_render = True
        data = placeholder.data
        bpy.data.objects.remove(placeholder, do_unlink=True)
        bpy.data.meshes.remove(data)
    scene.frame_end = ceil(duration*scene.render.fps*3)
    scene.frame_set(1)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene['review_gait'] = args.gait
    scene['review_cycles'] = 3
    scene['review_note'] = 'In-place playback; reference travel is not applied.'
    if hasattr(scene.render.image_settings, 'media_type'):
        scene.render.image_settings.media_type = 'VIDEO'
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.filepath = str(args.output.with_suffix('.mp4').resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    if args.render:
        bpy.ops.render.render(animation=True)
    print('CANINE_MOTION_REVIEW_OK', args.output)


if __name__ == '__main__':
    main()
