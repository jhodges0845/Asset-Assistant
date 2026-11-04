# SPDX-License-Identifier: GPL-3.0-or-later
"""Render paired imported LOD levels; diagnostic overrides do not modify bundles.

blender --background --factory-startup --python scripts/render_lod_review.py --
BUNDLE --output DIRECTORY [--clip Run --phase .25]
"""
import argparse
from hashlib import sha256
import json
from math import floor, isfinite, radians
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import render_human_review as sheets


def import_snapshot(path, clip, phase):
    before = set(bpy.data.objects)
    actions_before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = set(bpy.data.objects) - before
    rigs = [obj for obj in imported if obj.type == 'ARMATURE']
    bodies = [obj for obj in imported if obj.type == 'MESH' and
              any(mod.type == 'ARMATURE' for mod in obj.modifiers)]
    if len(rigs) != 1 or len(bodies) != 1:
        raise ValueError('Review requires one skinned mesh and rig per level')
    rig, body = rigs[0], bodies[0]
    for track in rig.animation_data.nla_tracks if rig.animation_data else ():
        track.mute = True
    if clip:
        actions = [action for action in set(bpy.data.actions) - actions_before
                   if action.name == clip or action.name.startswith(clip + '.')]
        if len(actions) != 1:
            raise ValueError('Expected exactly one imported clip: ' + clip)
        action = actions[0]
        rig.animation_data_create().action = action
        rig.animation_data.action_slot = action.slots[0]
        frame = action.frame_range[0] + (action.frame_range[1] - action.frame_range[0]) * phase
    else:
        rig.animation_data_clear()
        for bone in rig.pose.bones:
            bone.matrix_basis.identity()
        frame = 1
    bpy.context.scene.frame_set(floor(frame), subframe=frame - floor(frame))
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(graph)
    mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=graph)
    mesh.transform(evaluated.matrix_world)
    mesh.calc_loop_triangles()
    if not mesh.uv_layers.active:
        raise ValueError('Imported LOD has no UV layer for checker review')
    metadata = {'frame': frame, 'vertices': len(mesh.vertices), 'triangles': len(mesh.loop_triangles),
                'uv_layers': [layer.name for layer in mesh.uv_layers],
                'materials': [material.name if material else None for material in mesh.materials]}
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    return mesh, metadata


def checker_material(material):
    sheets._configure_clay_material(material)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    uv = nodes.new('ShaderNodeTexCoord')
    checker = nodes.new('ShaderNodeTexChecker')
    checker.inputs['Scale'].default_value = 24
    checker.inputs['Color1'].default_value = (.04, .12, .3, 1)
    checker.inputs['Color2'].default_value = (.9, .65, .16, 1)
    links.new(uv.outputs['UV'], checker.inputs['Vector'])
    links.new(checker.outputs['Color'], nodes.get('Principled BSDF').inputs['Base Color'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--clip', choices=('Idle', 'Walk', 'Run', 'Flight'))
    parser.add_argument('--phase', type=float, default=.25)
    parser.add_argument('--samples', type=int, default=16)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not isfinite(args.phase) or not 0 <= args.phase <= 1 or args.samples < 1:
        parser.error('Phase must be finite in [0,1] and samples positive')
    if args.output.exists():
        parser.error('Choose a new output directory')
    manifest = json.loads((args.bundle / 'lod-manifest.json').read_text())
    if [level['index'] for level in manifest['levels']] != [0, 1]:
        parser.error('Review requires LOD0 and LOD1')
    sheets._clear_scene()
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.render.fps_base = 1
    levels = []
    for level in manifest['levels']:
        path = (args.bundle / level['file']).resolve()
        if path.parent != args.bundle.resolve():
            raise ValueError('LOD file must belong to the bundle directory')
        mesh, metadata = import_snapshot(path, args.clip, args.phase)
        if metadata['triangles'] != level['triangles']:
            raise ValueError('Imported triangle count differs from bundle manifest')
        metadata.update(file=path.name, sha256=sha256(path.read_bytes()).hexdigest())
        levels.append((mesh, metadata))
    material = sheets._make_material()
    objects = []
    angles = (180, 90, 135)
    for row, (mesh, metadata) in enumerate(levels):
        mesh.materials.clear()
        mesh.materials.append(material)
        for polygon in mesh.polygons:
            polygon.material_index = 0
        for column, angle in enumerate(angles):
            obj = bpy.data.objects.new(f'LOD{row} view {column}', mesh)
            scene.collection.objects.link(obj)
            obj.rotation_euler.z = radians(angle)
            objects.append(obj)
    bpy.context.view_layer.update()
    # A common box and common offsets for both levels avoid normalizing away changes.
    bounds = []
    for column in range(3):
        points = [obj.matrix_world @ Vector(corner) for obj in (objects[column], objects[column + 3])
                  for corner in obj.bound_box]
        low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
        high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
        bounds.append((low, high))
    height = max(high.z - low.z for low, high in bounds)
    gap = height * .25
    widths = [high.x - low.x for low, high in bounds]
    total_width = sum(widths) + gap * 4
    total_height = height * 2 + gap * 3
    cursor = -total_width / 2 + gap
    labels = []
    for column, (low, high) in enumerate(bounds):
        x = cursor + widths[column] / 2
        for row in range(2):
            obj = objects[row * 3 + column]
            obj.location = (x - (low.x + high.x) / 2, 0, (1 - row) * (height + gap) - low.z)
            text = f"LOD{row} / {levels[row][1]['triangles']} tris / {('front', 'side', 'three-quarter')[column]}"
            labels.append(sheets._add_label(text, (x, low.y - gap, obj.location.z + low.z - gap * .35), total_width * .012))
        cursor += widths[column] + gap
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1800
    scene.render.resolution_y = max(700, round(1800 * total_height / total_width))
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('LOD Review World')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.05, .06, .08, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .7
    camera_data = bpy.data.cameras.new('LOD Review Camera')
    camera_data.type = 'ORTHO'
    camera_data.sensor_fit = 'HORIZONTAL'
    camera_data.ortho_scale = total_width * 1.05
    camera_data.clip_start = .01
    camera_data.clip_end = 1000
    camera = bpy.data.objects.new('LOD Review Camera', camera_data)
    scene.collection.objects.link(camera)
    center_z = (height * 2 + gap) / 2 - gap * .2
    camera.location = (0, -max(10, total_width * 3), center_z)
    sheets._look_at(camera, (0, 0, center_z))
    scene.camera = camera
    sheets._add_lighting(center_z, total_width, height * 2, min(low.y for low, high in bounds))
    # The wide paired layout otherwise overpowers the small Avian body.
    for light in (obj for obj in scene.objects if obj.type == 'LIGHT'):
        light.data.energy *= .25
    label_material = bpy.data.materials.new('Review labels')
    label_material.use_nodes = True
    sheets._configure_silhouette_material(label_material)
    for label in labels:
        label.data.materials.append(label_material)
    bpy.context.view_layer.update()
    sheets._validate_camera_frame(camera, objects + labels, scene)
    args.output.mkdir(parents=True)
    for mode in ('clay', 'checker', 'silhouette'):
        if mode == 'checker':
            checker_material(material)
        else:
            sheets._configure_material(material, mode)
        scene.render.filepath = str((args.output / (mode + '.png')).resolve())
        bpy.ops.render.render(write_still=True)
    (args.output / 'review.json').write_text(json.dumps({
        'bundle': str(args.bundle.resolve()), 'clip': args.clip or 'rest', 'phase': args.phase,
        'levels': [metadata for mesh, metadata in levels], 'views_degrees': angles,
        'scope': 'Imported GLB LOD0 versus LOD1, diagnostic material overrides; sampled visual review only.'}, indent=2))


if __name__ == '__main__':
    main()
