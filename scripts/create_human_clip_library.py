# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a fresh editable Human with Idle, Walk and Run; never upgrades saved art.

Run in a fresh Blender background process with -- --output new-library.blend.
"""
import argparse
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from object_core.objects import get_provider
from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle, add_locomotion, add_run, activate_generated_action
from blender_adapter.materials import prepare_materials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output = args.output.resolve()
    if output.suffix.lower() != '.blend' or output.exists():
        parser.error('--output must be a new .blend path')
    provider = get_provider('human')
    values = {p.key:p.default for p in provider.parameters}
    mesh = provider.mesh(values)
    scene = bpy.data.scenes.new('Human clip library')
    bpy.context.window.scene = scene
    scene.render.fps = 25
    scene.render.fps_base = 1
    scene.frame_start = 1
    root = create_character(mesh, name='Human', scene=scene,
                            skeleton=provider.skeleton(values),
                            skin_weights=provider.skin_weights(mesh, values))
    root['object_type'] = provider.key
    for key,value in values.items():
        root[key] = value
    prepare_materials(root)
    for generate,duration in ((add_idle,4.),(add_locomotion,1.2),(add_run,.72)):
        generate(root,scene,duration,1.)
    activate_generated_action(root,'Walk')
    scene.frame_end = 31
    scene.frame_set(1)
    rig = next(o for o in root.children if o.type == 'ARMATURE')
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    print('HUMAN_CLIP_LIBRARY_OK', output)


if __name__ == '__main__':
    main()
