# SPDX-License-Identifier: GPL-3.0-or-later
"""Convert portable provider animation samples into editable Blender actions."""

from math import ceil

from .animation_records import (
    has_animation_record,
    persist_generated_animation,
    update_animation_export_name,
)
from .workflow import provider_for


_GENERATED = 'asset_assistant_generated'
_GENERATED_RIG = 'asset_assistant_rig'
_RIG_ID = 'asset_assistant_rig_id'
_GENERATED_CLIP = 'asset_assistant_clip'
_EXPORT_NAME = 'asset_assistant_export_name'
_STRENGTH = 'asset_assistant_animation_strength'


def action_curves(action, slot=None):
    """Read only the assigned slot on layered actions, or legacy action curves."""
    if hasattr(action, 'fcurves') and not getattr(action, 'is_action_layered', False):
        return tuple(action.fcurves)
    if slot is None:
        return ()
    return tuple(curve for layer in action.layers for strip in layer.strips
                 if strip.type == 'KEYFRAME'
                 for bag in [strip.channelbag(slot)] if bag is not None
                 for curve in bag.fcurves)


def _rig(root):
    rigs = [obj for obj in root.children if obj.type == 'ARMATURE']
    if len(rigs) != 1:
        raise ValueError('Add one basic rig before generating animation.')
    return rigs[0]


def generated_actions(root):
    """Return generated actions owned by this rig, or none when no single rig exists."""
    import bpy
    rigs = [obj for obj in root.children if obj.type == 'ARMATURE']
    if len(rigs) != 1:
        return ()
    rig = rigs[0]
    rig_id = rig.get(_RIG_ID)
    if rig_id:
        return tuple(action for action in bpy.data.actions
                     if action.get(_GENERATED) and action.get(_RIG_ID) == rig_id)
    return tuple(action for action in bpy.data.actions
                 if action.get(_GENERATED) and action.get(_GENERATED_RIG) == rig.name)


def generated_action(root, clip_name):
    return next((action for action in generated_actions(root)
                 if action.get(_GENERATED_CLIP) == clip_name), None)


def clip_export_name(action):
    value = str(action.get(_EXPORT_NAME) or action.get(_GENERATED_CLIP) or action.name).strip()
    return value or str(action.get(_GENERATED_CLIP) or action.name)


def set_clip_export_name(root, clip_name, export_name):
    action = generated_action(root, clip_name)
    if action is None:
        raise ValueError('Generate the ' + clip_name + ' clip first.')
    export_name = str(export_name).strip()
    if not export_name:
        raise ValueError('Animation export name cannot be empty.')
    duplicate = next((other for other in generated_actions(root)
                      if other is not action and clip_export_name(other) == export_name), None)
    if duplicate is not None:
        raise ValueError('Animation export names must be unique for this character.')
    if has_animation_record(action):
        update_animation_export_name(action, export_name)
    action[_EXPORT_NAME] = export_name
    return action


def activate_generated_action(root, clip_name):
    import bpy

    rig = _rig(root)
    action = generated_action(root, clip_name)
    if action is None:
        raise ValueError('Generate the ' + clip_name + ' clip first.')
    data = rig.animation_data_create()
    if data.nla_tracks or data.drivers:
        raise ValueError('Existing NLA tracks or drivers are preserved; prepare them manually before switching clips.')
    if data.action and not (data.action.get(_GENERATED) and data.action in generated_actions(root)):
        raise ValueError('Existing artist animation preserved; generated clips cannot replace it.')

    data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()

    data.action = action
    if hasattr(action, 'slots') and len(action.slots):
        data.action_slot = action.slots[0]
    rig.data.pose_position = 'POSE'
    bpy.context.scene.frame_set(bpy.context.scene.frame_current,
                                subframe=bpy.context.scene.frame_subframe)
    bpy.context.view_layer.update()
    return action


def _add_clip(root, scene, clip, suffix, capability, strength):
    import bpy
    from mathutils import Vector, Quaternion, Matrix

    provider = provider_for(root)
    rig = _rig(root)
    data = rig.animation_data
    if generated_action(root, suffix) is not None:
        raise ValueError('Existing animation preserved. ' + suffix + ' already exists; select that clip instead of overwriting it.')
    if data and (data.nla_tracks or data.drivers):
        raise ValueError('Existing animation preserved. NLA tracks and drivers require manual preparation.')
    if data and data.action and not (data.action.get(_GENERATED) and data.action in generated_actions(root)):
        raise ValueError('Existing animation preserved. Use a fresh rig or keep the artist action active.')

    previous_action = data.action if data else None
    previous_slot = getattr(data, 'action_slot', None) if data else None
    previous_frame, previous_subframe = scene.frame_current, scene.frame_subframe
    if previous_action is not None:
        data.action = None
        for bone in rig.pose.bones:
            bone.matrix_basis.identity()
        scene.frame_set(previous_frame, subframe=previous_subframe)

    try:
        for bone in rig.pose.bones:
            if bone.constraints or any(abs(bone.matrix_basis[i][j] - Matrix.Identity(4)[i][j]) > 1e-6
                                       for i in range(4) for j in range(4)):
                raise ValueError('Start from an unconstrained rest pose; existing pose preserved.')
        translations = getattr(clip, 'translations', ())
        if any(track.bone not in rig.pose.bones for track in tuple(clip.tracks) + tuple(translations)):
            raise ValueError('This rig is missing bones required by the provider animation.')

        fps = scene.render.fps / scene.render.fps_base
        start = scene.frame_start
        end = start + clip.duration * fps
        action = bpy.data.actions.new(rig.name + '.' + suffix)
        action[_GENERATED] = True
        action[_GENERATED_RIG] = rig.name
        if rig.get(_RIG_ID):
            action[_RIG_ID] = rig[_RIG_ID]
        action[_GENERATED_CLIP] = suffix
        action[_EXPORT_NAME] = suffix
        action[_STRENGTH] = float(strength)
        modes = {bone.name: bone.rotation_mode for bone in rig.pose.bones}
        had_data = data is not None
        try:
            if hasattr(action, 'slots'):
                from bpy_extras.anim_utils import action_ensure_channelbag_for_slot
                slot = action.slots.new('OBJECT', rig.name)
                curves = action_ensure_channelbag_for_slot(action, slot).fcurves
            else:
                slot = None
                curves = action.fcurves

            tracks_by_bone = {track.bone: track for track in clip.tracks}
            for bone in rig.pose.bones:
                track = tracks_by_bone.get(bone.name)
                if track is None:
                    identity = Quaternion((1.0, 0.0, 0.0, 0.0))
                    samples = [(start, identity), (end, identity)]
                else:
                    axis = bone.bone.matrix_local.to_3x3().inverted() @ Vector(track.axis)
                    samples = [(start + seconds * fps, Quaternion(axis, angle)) for seconds, angle in track.keys]
                group = {'group_name' if slot is not None else 'action_group': bone.name}
                for component in range(4):
                    curve = curves.new(bone.path_from_id('rotation_quaternion'), index=component,
                                       **group)
                    curve.keyframe_points.add(len(samples))
                    for key, (frame, rotation) in zip(curve.keyframe_points, samples):
                        key.co = (frame, rotation[component])
                        key.interpolation = 'LINEAR'
                    curve.modifiers.new('CYCLES')
                    curve.update()

            scale = root.get('coordinate_scale', 0.01 / scene.unit_settings.scale_length)
            for track in translations:
                bone = rig.pose.bones[track.bone]
                inverse = bone.bone.matrix_local.to_3x3().inverted()
                samples = [(start + seconds * fps, inverse @ (Vector(offset) * scale))
                           for seconds, offset in track.keys]
                group = {'group_name' if slot is not None else 'action_group': bone.name}
                for component in range(3):
                    curve = curves.new(bone.path_from_id('location'), index=component, **group)
                    curve.keyframe_points.add(len(samples))
                    for key, (frame, offset) in zip(curve.keyframe_points, samples):
                        key.co = (frame, offset[component])
                        key.interpolation = 'LINEAR'
                    curve.modifiers.new('CYCLES')
                    curve.update()

            for bone in rig.pose.bones:
                bone.rotation_mode = 'QUATERNION'
            rig.animation_data_create().action = action
            if slot is not None:
                rig.animation_data.action_slot = slot
            action.use_fake_user = True
            rig.data.pose_position = 'POSE'
            persist_generated_animation(
                root,
                action,
                display_name=suffix,
                export_name=suffix,
                frame_start=start,
                frame_end=end,
                fps=fps,
                provider_key=provider.key,
                capability=capability,
            )
        except Exception:
            if rig.animation_data:
                rig.animation_data.action = previous_action
                if previous_action is not None and previous_slot is not None and hasattr(rig.animation_data, 'action_slot'):
                    rig.animation_data.action_slot = previous_slot
            if not had_data:
                rig.animation_data_clear()
            for name, mode in modes.items():
                rig.pose.bones[name].rotation_mode = mode
            bpy.data.actions.remove(action)
            raise
        return action, max(start, ceil(end) - 1)
    except Exception:
        if data and data.action is None and previous_action is not None:
            data.action = previous_action
            if previous_slot is not None and hasattr(data, 'action_slot'):
                data.action_slot = previous_slot
        raise
    finally:
        scene.frame_set(previous_frame, subframe=previous_subframe)


def add_idle(root, scene, duration=4.0, strength=1.0):
    provider = provider_for(root)
    if not provider.supports_idle:
        raise ValueError(provider.label + ' does not support idle animation.')
    return _add_clip(root, scene, provider.idle(duration, strength), 'Idle', 'idle', strength)


def locomotion_clip_name(provider):
    name = str(getattr(provider, 'locomotion_label', 'Walk')).strip()
    return name or 'Walk'


def add_locomotion(root, scene, duration=1.2, strength=1.0):
    provider = provider_for(root)
    if not getattr(provider, 'supports_locomotion', False):
        raise ValueError(provider.label + ' does not support locomotion animation.')
    return _add_clip(
        root,
        scene,
        _provider_motion(provider, root, 'locomotion', duration, strength),
        locomotion_clip_name(provider),
        'locomotion',
        strength,
    )


def add_flight(root, scene, duration=1.2, strength=1.0):
    provider = provider_for(root)
    if not getattr(provider, 'supports_flight', False):
        raise ValueError(provider.label + ' does not support flight animation.')
    return _add_clip(root, scene, provider.flight(duration, strength), 'Flight', 'flight', strength)


def add_run(root, scene, duration=0.72, strength=1.0):
    provider = provider_for(root)
    if not getattr(provider, 'supports_run', False):
        raise ValueError(provider.label + ' does not support run animation.')
    return _add_clip(root, scene, _provider_motion(provider, root, 'run', duration, strength), 'Run', 'run', strength)


def _provider_motion(provider, root, capability, duration, strength):
    method = getattr(provider, capability)
    if getattr(provider, 'animation_uses_parameters', False):
        from .workflow import _saved_values
        return method(duration, strength, values=_saved_values(provider, root))
    return method(duration, strength)
