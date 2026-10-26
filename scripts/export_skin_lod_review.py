# SPDX-License-Identifier: GPL-3.0-or-later
"""Export a small skinned LOD fixture and world-space bone playback oracle."""
from pathlib import Path
import json
import sys
import bpy
from mathutils import Quaternion
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_adapter.animation import action_curves
from blender_adapter.lod_skin_preview import preview_skin_lods
from blender_adapter.lod_export import export_skin_lod_bundle


def main():
    destination = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    bpy.ops.object.armature_add()
    rig = bpy.context.object
    parent = bpy.data.objects.new('Fixture root', None)
    bpy.context.scene.collection.objects.link(parent)
    parent.location = (2, -1, .5)
    parent.rotation_euler.z = .4
    rig.parent = parent
    rig['asset_assistant_rig_id'] = 'lod-godot-fixture'
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    source = bpy.context.object
    source.data.materials.append(bpy.data.materials.new('Fixture material'))
    group = source.vertex_groups.new(name=rig.data.bones[0].name)
    group.add(list(range(len(source.data.vertices))), 1, 'REPLACE')
    source.modifiers.new('Skin', 'ARMATURE').object = rig
    bone = rig.pose.bones[0]
    bone.rotation_mode = 'QUATERNION'
    for frame, amount in ((1, 0), (12, .4), (24, 0)):
        bone.location.x = amount
        bone.rotation_quaternion = Quaternion((0, 0, 1), amount * 2)
        bone.keyframe_insert('location', frame=frame)
        bone.keyframe_insert('rotation_quaternion', frame=frame)
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
        samples.append({'seconds': (frame - 1) / fps,
                        'head': [point.x, point.z, -point.y],
                        'tail': [tip.x, tip.z, -tip.y]})
    (destination / 'expected.json').write_text(json.dumps({
        'bone': bone.name, 'bone_length': bone.length,
        'samples': samples, 'tolerance': 1e-5}))
    (destination / 'project.godot').write_text('[application]\nconfig/name="Skinned LOD probe"\n')


if __name__ == '__main__':
    main()
