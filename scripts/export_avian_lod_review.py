# SPDX-License-Identifier: GPL-3.0-or-later
"""Export generated provider clips with a per-level, 49-sample skin oracle.

Run in Blender with -- DESTINATION [--provider avian|human|quadruped]
[--clip Idle|Walk|Run|Flight] [--sample default|contrasting]. Defaults retain the original Avian Flight fixture.
"""
from pathlib import Path
import argparse
from collections import Counter
import json
import sys
import struct
from math import isfinite
import bpy
from math import floor
from mathutils import Matrix
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from object_core.objects import get_provider
from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle, add_locomotion, add_run, add_flight
from blender_adapter.materials import prepare_materials
from blender_adapter.lod_skin_preview import preview_skin_lods
from blender_adapter.lod_export import export_skin_lod_bundle


def exported_surface_inventory(path):
    """Inspect our GLB output structurally; this is not a visual fidelity metric."""
    raw = path.read_bytes()
    magic, version, total = struct.unpack_from('<4sII', raw)
    if magic != b'glTF' or version != 2 or total != len(raw):
        raise ValueError('Invalid generated GLB header')
    length, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4E4F534A:
        raise ValueError('Missing generated GLB JSON')
    document = json.loads(raw[20:20 + length])
    binary_length, binary_kind = struct.unpack_from('<II', raw, 20 + length)
    binary = raw[28 + length:]
    if binary_kind != 0x004E4942 or len(binary) != binary_length:
        raise ValueError('Missing generated GLB buffer')
    result = []
    for mesh in document['meshes']:
        for primitive in mesh['primitives']:
            if primitive.get('mode', 4) != 4:
                raise ValueError('Expected triangle surface')
            attributes = primitive['attributes']
            position = document['accessors'][attributes['POSITION']]
            uv = document['accessors'][attributes['TEXCOORD_0']]
            if (uv['componentType'] != 5126 or uv['type'] != 'VEC2' or
                    uv['count'] != position['count'] or uv.get('sparse')):
                raise ValueError('Invalid exported UV accessor')
            view = document['bufferViews'][uv['bufferView']]
            offset = view.get('byteOffset', 0) + uv.get('byteOffset', 0)
            stride = view.get('byteStride', 8)
            end = offset + (uv['count'] - 1) * stride + 8
            if (view.get('buffer', 0) != 0 or stride < 8 or stride % 4 or offset % 4 or
                    uv['count'] <= 0 or uv.get('byteOffset', 0) < 0 or
                    end > view.get('byteOffset', 0) + view['byteLength'] or end > len(binary)):
                raise ValueError('Exported UV accessor lies outside its buffer view')
            coordinates = [struct.unpack_from('<2f', binary, offset + i * stride)
                           for i in range(uv['count'])]
            if not coordinates or not all(isfinite(x) for pair in coordinates for x in pair):
                raise ValueError('Exported UV coordinates must be finite and nonempty')
            indices = document['accessors'][primitive['indices']]
            if indices['count'] % 3:
                raise ValueError('Incomplete exported triangles')
            material = document['materials'][primitive['material']]
            result.append({'material': material['name'], 'triangles': indices['count'] // 3,
                'uv_vertices': uv['count'],
                'uv_min': [min(pair[axis] for pair in coordinates) for axis in (0, 1)],
                'uv_max': [max(pair[axis] for pair in coordinates) for axis in (0, 1)]})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--provider', choices=('avian', 'human', 'quadruped'), default='avian')
    parser.add_argument('--sample', choices=('default', 'contrasting'), default='default')
    parser.add_argument('--clip', choices=('Idle', 'Walk', 'Run', 'Flight'), default='Flight')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if (args.clip == 'Flight' and args.provider != 'avian') or (args.clip == 'Run' and args.provider == 'avian'):
        parser.error('Selected provider does not support this clip')
    import addon_utils
    addon_utils.enable('blender_adapter', default_set=True, persistent=False)
    destination = args.destination.resolve()
    provider = get_provider(args.provider)
    add_clip, duration = {'Idle': (add_idle, 4.0), 'Walk': (add_locomotion, 1.2),
                          'Run': (add_run, .72), 'Flight': (add_flight, 1.2)}[args.clip]
    values = {field.key: field.default for field in provider.parameters}
    if args.sample == 'contrasting':
        from scripts.anatomy_baseline import SAMPLES
        values.update(SAMPLES[args.provider])
    scene = bpy.data.scenes.new(f'{args.provider} LOD {args.clip} oracle')
    bpy.context.window.scene = scene
    scene.render.fps = 24
    scene.render.fps_base = 1
    mesh = provider.mesh(values)
    root = create_character(mesh, scene=scene, skeleton=provider.skeleton(values),
                            skin_weights=provider.skin_weights(mesh, values))
    root['object_type'] = args.provider
    for key, value in values.items():
        root[key] = value
    prepare_materials(root)
    add_clip(root, scene, duration=duration, strength=1)
    body = next(obj for obj in root.children if obj.type == 'MESH')
    rig = next(obj for obj in root.children if obj.type == 'ARMATURE')
    scene.frame_set(1)
    bpy.context.view_layer.update()
    preview = preview_skin_lods(body, scene, ratios=(.5,), max_distance=body.dimensions.length * .02)
    preview.apply()
    export_skin_lod_bundle(preview.collection, bpy.context, destination)
    # Record what exists; counts alone are not UV/material fidelity acceptance.
    surfaces = []
    for index, obj in enumerate((body,) + tuple(preview.objects)):
        obj.data.calc_loop_triangles()
        exported = exported_surface_inventory(destination / f'LOD{index}.glb')
        expected_materials = Counter(obj.material_slots[tri.material_index].material.name
                                     for tri in obj.data.loop_triangles)
        actual_materials = Counter()
        for item in exported:
            actual_materials[item['material']] += item['triangles']
        if expected_materials != actual_materials:
            raise ValueError('Exported material triangle counts differ from the LOD source')
        if sum(item['triangles'] for item in exported) != len(obj.data.loop_triangles):
            raise ValueError('Exported triangle count differs from the LOD source')
        surfaces.append({'level': index, 'vertices': len(obj.data.vertices),
            'triangles': len(obj.data.loop_triangles),
            'uv_layers': [layer.name for layer in obj.data.uv_layers],
            'exported_surfaces': exported,
            'materials': [slot.material.name if slot.material else None for slot in obj.material_slots],
            'material_triangles': {str(slot): sum(tri.material_index == slot for tri in obj.data.loop_triangles)
                                   for slot in range(len(obj.material_slots))}})
    (destination / 'surface-inventory.json').write_text(json.dumps({
        'provider': args.provider, 'sample': args.sample, 'parameters': values,
        'levels': surfaces, 'acceptance': 'inventory only; visual and UV fidelity remain open'}, indent=2))
    bone = next(bone for bone in rig.pose.bones if bone.parent is None)
    conversion = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
    samples = []
    for step in range(49):
        seconds = duration * step / 48
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
    (destination / 'expected.json').write_text(json.dumps({'fixture': f'{args.provider}-{args.sample}-{args.clip.lower()}',
        'parameters': values, 'sample': args.sample,
        'clip': args.clip, 'bone': bone.name, 'samples': samples, 'tolerance': 1e-5}))
    (destination / 'project.godot').write_text('[application]\nconfig/name="Generated provider LOD review"\n')


if __name__ == '__main__':
    main()
