# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable JSON round-trip for LLM-authored animations."""

import hashlib
import json
import math
from pathlib import Path

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from .animation_lifecycle import register_animation_action
from .animation_names_ui import _character, _rig
from .core import AnimationSource

_CONTEXT_SCHEMA = 'asset_assistant.animation_context.v1'
_ANIMATION_SCHEMA = 'asset_assistant.animation.v1'
_PENDING_PATH = 'asset_assistant_animation_json_pending_path'
_PENDING_SUMMARY = 'asset_assistant_animation_json_pending_summary'


def _vec(values):
    return [float(value) for value in values]


def _matrix_rows(matrix):
    return [[float(value) for value in row] for row in matrix]


def _rig_signature(rig):
    parts = []
    for bone in rig.data.bones:
        parts.append(bone.name + '>' + (bone.parent.name if bone.parent else ''))
    return hashlib.sha256('\n'.join(sorted(parts)).encode('utf-8')).hexdigest()


def _active_action(rig):
    return rig.animation_data.action if rig.animation_data else None


def _action_key_frames(action):
    if action is None:
        return ()
    frames = set()
    curves = ()
    if hasattr(action, 'fcurves') and not getattr(action, 'is_action_layered', False):
        curves = tuple(action.fcurves)
    else:
        curves = tuple(
            curve
            for layer in getattr(action, 'layers', ())
            for strip in getattr(layer, 'strips', ())
            if strip.type == 'KEYFRAME'
            for bag in getattr(strip, 'channelbags', ())
            for curve in bag.fcurves
        )
    for curve in curves:
        for point in curve.keyframe_points:
            frames.add(float(point.co.x))
    return tuple(sorted(frames))


def _pose_payload(bone):
    payload = {
        'location': _vec(bone.location),
        'scale': _vec(bone.scale),
        'rotation_mode': bone.rotation_mode,
    }
    if bone.rotation_mode == 'QUATERNION':
        payload['rotation_quaternion'] = _vec(bone.rotation_quaternion)
    elif bone.rotation_mode == 'AXIS_ANGLE':
        payload['rotation_axis_angle'] = _vec(bone.rotation_axis_angle)
    else:
        payload['rotation_euler'] = _vec(bone.rotation_euler)
    return payload


def build_context_payload(root, rig, scene):
    fps = scene.render.fps / max(scene.render.fps_base, 0.0001)
    action = _active_action(rig)
    payload = {
        'schema': _CONTEXT_SCHEMA,
        'instructions': {
            'return_schema': _ANIMATION_SCHEMA,
            'coordinate_space': 'Blender pose-bone local transforms relative to the exported rest pose',
            'rule': 'Create a new animation; do not rename bones or invent missing bones.',
        },
        'asset': {
            'name': root.name,
            'type': str(root.get('object_type') or root.get('asset_assistant_external_capability') or 'unknown'),
            'source': str(root.get('asset_assistant_source') or 'unknown'),
        },
        'rig': {
            'name': rig.name,
            'signature': _rig_signature(rig),
            'bones': [],
        },
        'scene': {
            'fps': fps,
            'unit_system': scene.unit_settings.system,
            'scale_length': float(scene.unit_settings.scale_length),
            'up_axis': 'Z',
        },
        'reference_animation': None,
    }
    for bone in rig.data.bones:
        payload['rig']['bones'].append({
            'name': bone.name,
            'parent': bone.parent.name if bone.parent else None,
            'head_local': _vec(bone.head_local),
            'tail_local': _vec(bone.tail_local),
            'matrix_local': _matrix_rows(bone.matrix_local),
            'use_deform': bool(bone.use_deform),
        })
    if action is not None:
        frames = _action_key_frames(action)
        current = scene.frame_current
        samples = []
        try:
            for frame in frames:
                whole = int(math.floor(frame))
                scene.frame_set(whole, subframe=frame - whole)
                samples.append({
                    'frame': frame,
                    'bones': {bone.name: _pose_payload(bone) for bone in rig.pose.bones},
                })
        finally:
            scene.frame_set(current)
        payload['reference_animation'] = {
            'name': action.name,
            'frame_start': float(action.frame_range[0]),
            'frame_end': float(action.frame_range[1]),
            'key_pose_samples': samples,
        }
    return payload


def _finite_number(value, label):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(label + ' must be finite.')
    if abs(value) > 100000:
        raise ValueError(label + ' is outside the supported safety range.')
    return value


def validate_animation_payload(payload, rig):
    if not isinstance(payload, dict) or payload.get('schema') != _ANIMATION_SCHEMA:
        raise ValueError('Expected schema ' + _ANIMATION_SCHEMA + '.')
    target = payload.get('target') or {}
    signature = str(target.get('rig_signature') or '')
    if signature and signature != _rig_signature(rig):
        raise ValueError('Animation JSON targets a different rig; retargeting is not performed automatically.')
    clip = payload.get('clip')
    if not isinstance(clip, dict):
        raise ValueError('Animation JSON needs a clip object.')
    name = str(clip.get('name') or '').strip()
    if not name:
        raise ValueError('clip.name cannot be empty.')
    fps = _finite_number(clip.get('fps', 24.0), 'clip.fps')
    if fps <= 0 or fps > 240:
        raise ValueError('clip.fps must be greater than 0 and no more than 240.')
    keyframes = payload.get('keyframes')
    if not isinstance(keyframes, list) or not keyframes:
        raise ValueError('Animation JSON needs at least one keyframe.')
    known = set(rig.pose.bones.keys())
    normalized = []
    for index, row in enumerate(keyframes):
        if not isinstance(row, dict):
            raise ValueError('Each keyframe must be an object.')
        frame = _finite_number(row.get('frame'), 'keyframes[%d].frame' % index)
        bones = row.get('bones')
        if not isinstance(bones, dict) or not bones:
            raise ValueError('Each keyframe needs a bones object.')
        normalized_bones = {}
        for bone_name, transforms in bones.items():
            if bone_name not in known:
                raise ValueError('Animation references missing bone: ' + bone_name)
            if not isinstance(transforms, dict):
                raise ValueError('Bone transforms must be objects: ' + bone_name)
            clean = {}
            for key, size in (('location', 3), ('scale', 3), ('rotation_quaternion', 4), ('rotation_euler', 3), ('rotation_axis_angle', 4)):
                if key not in transforms:
                    continue
                values = transforms[key]
                if not isinstance(values, (list, tuple)) or len(values) != size:
                    raise ValueError(bone_name + '.' + key + ' must have ' + str(size) + ' values.')
                clean[key] = [_finite_number(value, bone_name + '.' + key) for value in values]
            if not clean:
                raise ValueError('No supported transforms supplied for bone ' + bone_name + '.')
            normalized_bones[bone_name] = clean
        normalized.append({'frame': frame, 'bones': normalized_bones})
    normalized.sort(key=lambda row: row['frame'])
    return {
        'name': name,
        'fps': fps,
        'looping': bool(clip.get('looping', False)),
        'keyframes': normalized,
        'notes': str(payload.get('notes') or ''),
    }


def create_action_from_payload(root, rig, scene, normalized):
    previous_action = _active_action(rig)
    previous_frame = scene.frame_current
    action = bpy.data.actions.new(normalized['name'])
    try:
        rig.animation_data_create().action = action
        for row in normalized['keyframes']:
            frame = row['frame']
            whole = int(math.floor(frame))
            scene.frame_set(whole, subframe=frame - whole)
            for bone_name, transforms in row['bones'].items():
                bone = rig.pose.bones[bone_name]
                if 'location' in transforms:
                    bone.location = transforms['location']
                    bone.keyframe_insert('location', group=bone.name)
                if 'scale' in transforms:
                    bone.scale = transforms['scale']
                    bone.keyframe_insert('scale', group=bone.name)
                if 'rotation_quaternion' in transforms:
                    bone.rotation_mode = 'QUATERNION'
                    bone.rotation_quaternion = transforms['rotation_quaternion']
                    bone.keyframe_insert('rotation_quaternion', group=bone.name)
                elif 'rotation_axis_angle' in transforms:
                    bone.rotation_mode = 'AXIS_ANGLE'
                    bone.rotation_axis_angle = transforms['rotation_axis_angle']
                    bone.keyframe_insert('rotation_axis_angle', group=bone.name)
                elif 'rotation_euler' in transforms:
                    if bone.rotation_mode in {'QUATERNION', 'AXIS_ANGLE'}:
                        bone.rotation_mode = 'XYZ'
                    bone.rotation_euler = transforms['rotation_euler']
                    bone.keyframe_insert('rotation_euler', group=bone.name)
        if normalized['looping']:
            curves = action.fcurves if hasattr(action, 'fcurves') else ()
            for curve in curves:
                if not any(mod.type == 'CYCLES' for mod in curve.modifiers):
                    curve.modifiers.new('CYCLES')
        register_animation_action(
            root,
            action,
            source=AnimationSource.ARTIST,
            display_name=action.name,
            export_name=action.name,
            fps=normalized['fps'],
        )
        scene.frame_start = int(math.floor(normalized['keyframes'][0]['frame']))
        scene.frame_end = int(math.ceil(normalized['keyframes'][-1]['frame']))
        scene.frame_set(scene.frame_start)
        return action
    except Exception:
        if rig.animation_data:
            rig.animation_data.action = previous_action
        bpy.data.actions.remove(action)
        scene.frame_set(previous_frame)
        raise


class ASSET_ASSISTANT_OT_export_animation_context(bpy.types.Operator, ExportHelper):
    bl_idname = 'asset_assistant.export_animation_context_json'
    bl_label = 'Export Animation Context JSON'
    bl_description = 'Export model, rig, rest-pose and optional active-animation data for an LLM to author a new animation'
    filename_ext = '.json'
    filter_glob: StringProperty(default='*.json', options={'HIDDEN'})

    def invoke(self, context, event):
        root = _character(context)
        if root is None:
            return {'CANCELLED'}
        self.filepath = root.name + '_animation_context.json'
        return super().invoke(context, event)

    def execute(self, context):
        root = _character(context)
        try:
            rig = _rig(root)
            payload = build_context_payload(root, rig, context.scene)
            Path(self.filepath).write_text(json.dumps(payload, indent=2), encoding='utf-8')
        except (ValueError, OSError, TypeError, RuntimeError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Animation context JSON exported for LLM authoring.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_import_animation_json(bpy.types.Operator, ImportHelper):
    bl_idname = 'asset_assistant.import_animation_json'
    bl_label = 'Import Animation JSON'
    bl_description = 'Load and validate an LLM-authored animation JSON without changing the rig yet'
    filename_ext = '.json'
    filter_glob: StringProperty(default='*.json', options={'HIDDEN'})

    def execute(self, context):
        root = _character(context)
        try:
            rig = _rig(root)
            payload = json.loads(Path(self.filepath).read_text(encoding='utf-8'))
            normalized = validate_animation_payload(payload, rig)
        except (ValueError, OSError, json.JSONDecodeError, TypeError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        context.scene[_PENDING_PATH] = str(self.filepath)
        context.scene[_PENDING_SUMMARY] = (
            normalized['name'] + ' • ' + str(len(normalized['keyframes'])) + ' keyed poses • ' + str(normalized['fps']) + ' fps'
        )
        self.report({'INFO'}, 'Animation JSON validated. Review the summary, then create the Action.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_apply_animation_json(bpy.types.Operator):
    bl_idname = 'asset_assistant.apply_animation_json'
    bl_label = 'Create Loaded Animation'
    bl_description = 'Create a new Blender Action from the validated LLM-authored animation JSON'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        path = context.scene.get(_PENDING_PATH)
        root = _character(context)
        if not path or root is None:
            self.report({'ERROR'}, 'Import and validate an Animation JSON file first.')
            return {'CANCELLED'}
        try:
            rig = _rig(root)
            payload = json.loads(Path(path).read_text(encoding='utf-8'))
            normalized = validate_animation_payload(payload, rig)
            action = create_action_from_payload(root, rig, context.scene, normalized)
        except (ValueError, OSError, json.JSONDecodeError, TypeError, RuntimeError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        context.scene.pop(_PENDING_PATH, None)
        context.scene.pop(_PENDING_SUMMARY, None)
        self.report({'INFO'}, 'Created new animation Action: ' + action.name)
        return {'FINISHED'}


def draw_json_roundtrip(layout, context, root):
    if root is None:
        return
    box = layout.box()
    box.label(text='LLM ANIMATION JSON', icon='FILE_SCRIPT')
    box.label(text='Export rig/context, let an LLM author motion, then import it as a new clip.')
    row = box.row(align=True)
    row.operator('asset_assistant.export_animation_context_json', text='Export Context JSON', icon='EXPORT')
    row.operator('asset_assistant.import_animation_json', text='Import Animation JSON', icon='IMPORT')
    summary = context.scene.get(_PENDING_SUMMARY)
    if summary:
        box.label(text='Validated: ' + summary, icon='CHECKMARK')
        apply_row = box.row(); apply_row.scale_y = 1.2
        apply_row.operator('asset_assistant.apply_animation_json', text='Create Loaded Animation', icon='ACTION')
    box.label(text='Imports create a new Action; the source clip is not overwritten.')


def install(animation_names_ui, animation_artist_ui=None):
    """Append the JSON workflow to Clip Library and apply Blender 5.2 pose-selection compatibility."""
    if animation_artist_ui is not None:
        def pose_bones_52(rig):
            selected = tuple(getattr(bpy.context, 'selected_pose_bones', None) or ())
            return selected or tuple(rig.pose.bones)
        animation_artist_ui._pose_bones = pose_bones_52

    panel = animation_names_ui.ASSET_ASSISTANT_PT_animation_names
    original = panel.draw
    if getattr(original, '_asset_assistant_json_roundtrip', False):
        return

    def draw_with_json(self, context):
        original(self, context)
        draw_json_roundtrip(self.layout, context, _character(context))

    draw_with_json._asset_assistant_json_roundtrip = True
    panel.draw = draw_with_json


_CLASSES = (
    ASSET_ASSISTANT_OT_export_animation_context,
    ASSET_ASSISTANT_OT_import_animation_json,
    ASSET_ASSISTANT_OT_apply_animation_json,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
