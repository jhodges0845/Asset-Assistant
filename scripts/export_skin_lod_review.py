# SPDX-License-Identifier: GPL-3.0-or-later
"""Export a small skinned LOD fixture and world-space bone playback oracle."""
from pathlib import Path
import json
import sys
import bpy
from mathutils import Quaternion, Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_adapter.animation import action_curves
from blender_adapter.lod_skin_preview import preview_skin_lods
from blender_adapter.lod_export import export_skin_lod_bundle


def main():
    destination = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    options = sys.argv[sys.argv.index('--') + 2:]
    four_bones = '--four-bones' in options
    two_bones = '--two-bones' in options or four_bones
    bpy.ops.object.armature_add()
    rig = bpy.context.object
    if two_bones:
        bpy.ops.object.mode_set(mode='EDIT')
        root_bone = rig.data.edit_bones[0]
        child = rig.data.edit_bones.new('Tip')
        child.head = root_bone.tail
        child.tail = child.head + Vector((0, 0, 1))
        child.parent = root_bone
        child.use_connect = True
        if four_bones:
            for name in ('Middle', 'End'):
                next_bone = rig.data.edit_bones.new(name)
                next_bone.head = child.tail
                next_bone.tail = next_bone.head + Vector((0, 0, 1))
                next_bone.parent = child
                next_bone.use_connect = True
                child = next_bone
        bpy.ops.object.mode_set(mode='OBJECT')
    parent = bpy.data.objects.new('Fixture root', None)
    bpy.context.scene.collection.objects.link(parent)
    parent.location = (2, -1, .5)
    parent.rotation_euler.z = .4
    if '--identity-parent' in sys.argv[sys.argv.index('--') + 2:]:
        parent.location = (0, 0, 0)
        parent.rotation_euler.z = 0
    rig.parent = parent
    rig['asset_assistant_rig_id'] = 'lod-godot-fixture'
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    source = bpy.context.object
    source.data.materials.append(bpy.data.materials.new('Fixture material'))
    group = source.vertex_groups.new(name=rig.data.bones[0].name)
    group.add(list(range(len(source.data.vertices))), 1, 'REPLACE')
    if two_bones:
        tip_group = source.vertex_groups.new(name='Tip')
        for vertex in source.data.vertices:
            weight = .25 + .5 * (vertex.co.z + 1) / 2
            group.add([vertex.index], 1 - weight, 'REPLACE')
            tip_group.add([vertex.index], weight, 'REPLACE')
    if four_bones:
        groups = [group, tip_group] + [source.vertex_groups.new(name=name) for name in ('Middle', 'End')]
        for vertex in source.data.vertices:
            mix = (vertex.co.z + 1) / 2
            weights = (.1 + .2 * mix, .3 - .1 * mix, .2 + .1 * mix, .4 - .2 * mix)
            for target, weight in zip(groups, weights):
                target.add([vertex.index], weight, 'REPLACE')
    source.modifiers.new('Skin', 'ARMATURE').object = rig
    bone = rig.pose.bones[0]
    bone.rotation_mode = 'QUATERNION'
    for frame, amount in ((1, 0), (12, .4), (24, 0)):
        bone.location.x = amount
        bone.rotation_quaternion = Quaternion((0, 0, 1), amount * 2)
        bone.keyframe_insert('location', frame=frame)
        bone.keyframe_insert('rotation_quaternion', frame=frame)
        if two_bones:
            tip_bone = rig.pose.bones['Tip']
            tip_bone.rotation_mode = 'QUATERNION'
            tip_bone.rotation_quaternion = Quaternion((1, 0, 0), -amount * 1.5)
            tip_bone.keyframe_insert('rotation_quaternion', frame=frame)
        if four_bones:
            for name, axis, factor in (('Middle', (0, 1, 0), .8), ('End', (1, 0, 0), -.6)):
                joint = rig.pose.bones[name]
                joint.rotation_mode = 'QUATERNION'
                joint.rotation_quaternion = Quaternion(axis, amount * factor)
                joint.keyframe_insert('rotation_quaternion', frame=frame)
    action = rig.animation_data.action
    action['asset_assistant_generated'] = True
    action['asset_assistant_rig_id'] = rig['asset_assistant_rig_id']
    action['asset_assistant_clip'] = 'ProbeMotion'
    for curve in action_curves(action, rig.animation_data.action_slot):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    scene = bpy.context.scene
    scene.frame_set(1)
    preview = preview_skin_lods(source, scene, ratios=(.5,), max_distance=.3)
    preview.apply()
    export_skin_lod_bundle(preview.collection, bpy.context, destination)
    samples = []
    fps = scene.render.fps / scene.render.fps_base
    for step in range(49):
        frame = 1 + step * 23 / 48
        scene.frame_set(int(frame), subframe=frame - int(frame))
        point = rig.matrix_world @ bone.head
        tip = rig.matrix_world @ bone.tail
        conversion = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
        basis = conversion @ (rig.matrix_world @ bone.matrix).to_3x3()
        positions = {}
        for index, obj in enumerate((source,) + tuple(preview.objects)):
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            points = [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]
            positions[str(index)] = [[p.x, p.z, -p.y] for p in points]
        samples.append({'positions': positions, 'seconds': (frame - 1) / fps,
                        'head': [point.x, point.z, -point.y],
                        'tail': [tip.x, tip.z, -tip.y],
                        'axes': [list(basis.col[index]) for index in range(3)]})
    (destination / 'expected.json').write_text(json.dumps({
        'bone': bone.name, 'bone_length': bone.length, 'fixture': 'four-bone-blend' if four_bones else ('two-bone-blend' if two_bones else 'one-bone'),
        'samples': samples, 'tolerance': 1e-5}))
    (destination / 'project.godot').write_text('[application]\nconfig/name="Skinned LOD probe"\n')


if __name__ == '__main__':
    main()
