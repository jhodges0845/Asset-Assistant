# SPDX-License-Identifier: GPL-3.0-or-later
"""Export a generated Avian Flight LOD bundle and per-level skin oracle."""
from pathlib import Path
import json
import sys
import bpy
from math import floor
from mathutils import Matrix
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from object_core.objects import get_provider
from blender_adapter.adapter import create_character
from blender_adapter.animation import add_flight
from blender_adapter.materials import prepare_materials
from blender_adapter.lod_skin_preview import preview_skin_lods
from blender_adapter.lod_export import export_skin_lod_bundle


def main():
    destination = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    provider = get_provider('avian')
    values = {field.key: field.default for field in provider.parameters}
    scene = bpy.data.scenes.new('Avian LOD Flight oracle')
    bpy.context.window.scene = scene
    scene.render.fps = 24
    scene.render.fps_base = 1
    mesh = provider.mesh(values)
    root = create_character(mesh, scene=scene, skeleton=provider.skeleton(values),
                            skin_weights=provider.skin_weights(mesh, values))
    root['object_type'] = 'avian'
    for key, value in values.items():
        root[key] = value
    prepare_materials(root)
    add_flight(root, scene, duration=1.2, strength=1)
    body = next(obj for obj in root.children if obj.type == 'MESH')
    rig = next(obj for obj in root.children if obj.type == 'ARMATURE')
    scene.frame_set(1)
    bpy.context.view_layer.update()
    preview = preview_skin_lods(body, scene, ratios=(.5,), max_distance=body.dimensions.length * .02)
    preview.apply()
    export_skin_lod_bundle(preview.collection, bpy.context, destination)
    bone = next(bone for bone in rig.pose.bones if bone.parent is None)
    conversion = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
    samples = []
    for step in range(49):
        seconds = 1.2 * step / 48
        frame = 1 + seconds * 24
        scene.frame_set(floor(frame), subframe=frame - floor(frame))
        point = rig.matrix_world @ bone.head
        basis = conversion @ (rig.matrix_world @ bone.matrix).to_3x3()
        positions = {}
        for index, obj in enumerate((body,) + tuple(preview.objects)):
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            points = [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
            positions[str(index)] = [[p.x, p.z, -p.y] for p in points]
        samples.append({'seconds': seconds, 'positions': positions,
                        'head': [point.x, point.z, -point.y],
                        'axes': [list(basis.col[index]) for index in range(3)]})
    (destination / 'expected.json').write_text(json.dumps({'fixture': 'avian-default-flight',
        'clip': 'Flight', 'bone': bone.name, 'samples': samples, 'tolerance': 1e-5}))
    (destination / 'project.godot').write_text('[application]\nconfig/name="Avian LOD Flight review"\n')


if __name__ == '__main__':
    main()
