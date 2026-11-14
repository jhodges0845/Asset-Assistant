# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only admission checks for transferring clips without retargeting."""
from math import isfinite

from .animation import action_curves
from .animation_records import rig_signature


def validate_clip_compatibility(source, target, action, slot=None):
    """Require matching local rest frames and supported, resolvable bone channels.

    This deliberately rejects object/root motion and procedural dependencies.
    It never assigns an Action or edits either rig. File import and explicit
    registration must remain a separate transaction after this check succeeds.
    """
    if source is None or target is None or source.type != 'ARMATURE' or target.type != 'ARMATURE':
        raise ValueError('Choose source and target armatures')
    if rig_signature(source) != rig_signature(target):
        raise ValueError('Skeleton names or hierarchy differ; retargeting is required')
    for rig in (source, target):
        if rig.constraints or (rig.animation_data and rig.animation_data.drivers):
            raise ValueError('Rig constraints or drivers require manual preparation')
        if any(bone.constraints for bone in rig.pose.bones):
            raise ValueError('Bone constraints require manual preparation')
    for bone in source.data.bones:
        other = target.data.bones[bone.name]
        values = [(a, b) for row, other_row in zip(bone.matrix_local, other.matrix_local)
                  for a, b in zip(row, other_row)]
        values.append((bone.length, other.length))
        if any(not isfinite(a) or not isfinite(b) or abs(a-b) > 1e-5 for a, b in values):
            raise ValueError('Bone rest transforms differ; retargeting is required: ' + bone.name)
        if (bone.inherit_scale != other.inherit_scale or
                bone.use_inherit_rotation != other.use_inherit_rotation or
                bone.use_local_location != other.use_local_location):
            raise ValueError('Bone transform inheritance differs: ' + bone.name)
    if action is None:
        raise ValueError('Choose an animation Action')
    if len(getattr(action, 'slots', ())) > 1:
        raise ValueError('Multi-slot Actions require manual preparation')
    curves = action_curves(action, slot)
    if not curves:
        raise ValueError('Action has no animation curves in the selected slot')
    allowed = {}
    for bone in source.pose.bones:
        for prop, size in (('location', 3), ('rotation_euler', 3),
                           ('rotation_quaternion', 4), ('rotation_axis_angle', 4), ('scale', 3)):
            allowed[bone.path_from_id(prop)] = (bone, prop, size)
    for curve in curves:
        channel = allowed.get(curve.data_path)
        if channel is None or not 0 <= curve.array_index < channel[2]:
            raise ValueError('Only supported bone transform channels can be transferred: ' + curve.data_path)
        bone, prop, _ = channel
        if prop.startswith('rotation_'):
            expected = ('rotation_quaternion' if bone.rotation_mode == 'QUATERNION' else
                        'rotation_axis_angle' if bone.rotation_mode == 'AXIS_ANGLE' else 'rotation_euler')
            if prop != expected or bone.rotation_mode != target.pose.bones[bone.name].rotation_mode:
                raise ValueError('Bone rotation modes differ or channel is inactive: ' + bone.name)
        if curve.modifiers or curve.driver:
            raise ValueError('Procedural animation channels require manual preparation')
        if not curve.keyframe_points or curve.sampled_points:
            raise ValueError('Only keyed animation curves can be transferred')
        if any(not isfinite(value) for key in curve.keyframe_points
               for point in (key.co, key.handle_left, key.handle_right) for value in point):
            raise ValueError('Animation contains non-finite keys')
        target.path_resolve(curve.data_path)
    return tuple(curves)


def inspect_animation_file(filepath, target, context):
    """Inspect compatible clips, removing all temporary imported data on exit.

    This is a preview only: no Action is transferred, assigned or registered.
    """
    from pathlib import Path
    import bpy
    from .asset_file_import_ui import _import_external, _IMPORT_DATA_KINDS
    path = Path(filepath).resolve()
    if not path.is_file() or path.suffix.lower() not in ('.fbx', '.glb', '.gltf'):
        raise ValueError('Choose an existing FBX, GLB or glTF animation file')
    if context.mode != 'OBJECT':
        raise ValueError('Animation file inspection requires Object Mode')
    before = {kind: set(getattr(bpy.data, kind)) for kind in _IMPORT_DATA_KINDS}
    selected = tuple(context.selected_objects)
    active = context.view_layer.objects.active
    scene = context.scene
    timing = (scene.frame_start, scene.frame_end, scene.frame_current, scene.frame_subframe,
              scene.render.fps, scene.render.fps_base)
    try:
        _import_external(str(path), path.suffix.lower(), context)
        rigs = [obj for obj in set(bpy.data.objects) - before['objects'] if obj.type == 'ARMATURE']
        if len(rigs) != 1:
            raise ValueError('Animation file must contain exactly one source rig')
        source = rigs[0]
        pairs = []
        animation = source.animation_data
        if animation:
            if animation.action:
                pairs.append((animation.action, animation.action_slot))
            for track in animation.nla_tracks:
                for strip in track.strips:
                    if strip.action and (strip.action, strip.action_slot) not in pairs:
                        pairs.append((strip.action, strip.action_slot))
        if not pairs:
            raise ValueError('Animation file contains no rig clips')
        reports = []
        for action, slot in pairs:
            if action in before['actions']:
                raise ValueError('Importer reused an existing Action')
            curves = validate_clip_compatibility(source, target, action, slot)
            reports.append({'name': action.name, 'frames': tuple(action.frame_range),
                            'channels': len(curves)})
        return tuple(reports)
    finally:
        created = [item for kind, original in before.items()
                   for item in set(getattr(bpy.data, kind)) - original]
        if created:
            bpy.data.batch_remove(ids=created)
        scene.frame_start, scene.frame_end = timing[:2]
        scene.render.fps, scene.render.fps_base = timing[4:]
        scene.frame_set(timing[2], subframe=timing[3])
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in selected:
            obj.select_set(True)
        context.view_layer.objects.active = active
