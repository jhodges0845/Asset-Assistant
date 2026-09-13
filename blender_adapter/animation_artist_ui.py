# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender-native helpers that shorten common pose/keyframe editing operations."""

import bpy
from bpy.props import IntProperty, StringProperty

from .animation_names_ui import _character, _prepare_action_edit, _rig


def _active_action(context):
    root = _character(context)
    if root is None:
        return None, None
    try:
        rig = _rig(root)
    except ValueError:
        return None, None
    action = rig.animation_data.action if rig.animation_data else None
    return rig, action


def _key_frames(action):
    frames = set()
    if action is None:
        return ()
    if hasattr(action, 'fcurves') and not getattr(action, 'is_action_layered', False):
        curves = action.fcurves
    else:
        curves = tuple(curve for layer in action.layers for strip in layer.strips
                       if strip.type == 'KEYFRAME' for bag in strip.channelbags
                       for curve in bag.fcurves)
    for curve in curves:
        frames.update(round(point.co.x) for point in curve.keyframe_points)
    return tuple(sorted(frames))


def _pose_bones(rig):
    selected = tuple(b for b in rig.pose.bones if b.bone.select)
    return selected or tuple(rig.pose.bones)


class ASSET_ASSISTANT_OT_animation_key_jump(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_key_jump'
    bl_label = 'Jump Keyframe'
    direction: IntProperty(default=1, min=-1, max=1)

    def execute(self, context):
        _, action = _active_action(context)
        frames = _key_frames(action)
        current = context.scene.frame_current
        candidates = [f for f in frames if f > current] if self.direction > 0 else [f for f in frames if f < current]
        if not candidates:
            self.report({'INFO'}, 'No more keyframes in that direction.')
            return {'CANCELLED'}
        context.scene.frame_set(min(candidates) if self.direction > 0 else max(candidates))
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_insert_pose_key(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_insert_pose_key'
    bl_label = 'Add Pose Key'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig, action = _active_action(context)
        if rig is None or action is None:
            self.report({'ERROR'}, 'Edit an animation clip first.')
            return {'CANCELLED'}
        for bone in _pose_bones(rig):
            bone.keyframe_insert('location', group=bone.name)
            if bone.rotation_mode == 'QUATERNION':
                bone.keyframe_insert('rotation_quaternion', group=bone.name)
            elif bone.rotation_mode == 'AXIS_ANGLE':
                bone.keyframe_insert('rotation_axis_angle', group=bone.name)
            else:
                bone.keyframe_insert('rotation_euler', group=bone.name)
            bone.keyframe_insert('scale', group=bone.name)
        self.report({'INFO'}, 'Pose key added at frame ' + str(context.scene.frame_current) + '.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_delete_pose_key(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_delete_pose_key'
    bl_label = 'Delete Pose Key'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig, action = _active_action(context)
        if rig is None or action is None:
            self.report({'ERROR'}, 'Edit an animation clip first.')
            return {'CANCELLED'}
        for bone in _pose_bones(rig):
            for path in ('location', 'rotation_quaternion', 'rotation_euler', 'rotation_axis_angle', 'scale'):
                try:
                    bone.keyframe_delete(path)
                except (TypeError, RuntimeError):
                    pass
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_copy_pose(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_copy_pose'
    bl_label = 'Copy Pose'

    def execute(self, context):
        rig, _ = _active_action(context)
        if rig is None or context.mode != 'POSE':
            self.report({'ERROR'}, 'Enter animation Edit/Pose Mode first.')
            return {'CANCELLED'}
        bpy.ops.pose.copy()
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_paste_pose(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_paste_pose'
    bl_label = 'Paste Pose'
    flipped: IntProperty(default=0, min=0, max=1)
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig, _ = _active_action(context)
        if rig is None or context.mode != 'POSE':
            self.report({'ERROR'}, 'Enter animation Edit/Pose Mode first.')
            return {'CANCELLED'}
        bpy.ops.pose.paste(flipped=bool(self.flipped))
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_reset_pose(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_reset_pose'
    bl_label = 'Reset Selected'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig, _ = _active_action(context)
        if rig is None or context.mode != 'POSE':
            self.report({'ERROR'}, 'Enter animation Edit/Pose Mode first.')
            return {'CANCELLED'}
        bones = _pose_bones(rig)
        for bone in bones:
            bone.location = (0.0, 0.0, 0.0)
            bone.scale = (1.0, 1.0, 1.0)
            if bone.rotation_mode == 'QUATERNION': bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            elif bone.rotation_mode == 'AXIS_ANGLE': bone.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
            else: bone.rotation_euler = (0.0, 0.0, 0.0)
        return {'FINISHED'}


def draw_edit_helpers(layout, context, root):
    rig, action = _active_action(context)
    if rig is None or action is None:
        return
    box = layout.box()
    box.label(text='EDIT ANIMATION: ' + action.name, icon='POSE_HLT')
    box.label(text='Frame ' + str(context.scene.frame_current) + ' • Blender Pose Mode + Actions')
    nav = box.row(align=True)
    prev = nav.operator('asset_assistant.animation_key_jump', text='Prev Key', icon='PREV_KEYFRAME'); prev.direction = -1
    nav.operator('asset_assistant.animation_insert_pose_key', text='Add Key', icon='KEY_HLT')
    nxt = nav.operator('asset_assistant.animation_key_jump', text='Next Key', icon='NEXT_KEYFRAME'); nxt.direction = 1
    nav = box.row(align=True)
    nav.operator('asset_assistant.animation_delete_pose_key', text='Delete Key', icon='KEY_DEHLT')
    nav.operator('asset_assistant.animation_copy_pose', text='Copy Pose', icon='COPYDOWN')
    nav.operator('asset_assistant.animation_paste_pose', text='Paste Pose', icon='PASTEDOWN')
    pose = box.row(align=True)
    mirror = pose.operator('asset_assistant.animation_paste_pose', text='Mirror Paste', icon='MOD_MIRROR'); mirror.flipped = 1
    pose.operator('asset_assistant.animation_reset_pose', text='Reset Selected', icon='LOOP_BACK')
    box.label(text='Select bones to limit pose/key operations; no selection uses the whole rig.')


_CLASSES = (
    ASSET_ASSISTANT_OT_animation_key_jump,
    ASSET_ASSISTANT_OT_animation_insert_pose_key,
    ASSET_ASSISTANT_OT_animation_delete_pose_key,
    ASSET_ASSISTANT_OT_animation_copy_pose,
    ASSET_ASSISTANT_OT_animation_paste_pose,
    ASSET_ASSISTANT_OT_animation_reset_pose,
)


def register():
    for cls in _CLASSES: bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES): bpy.utils.unregister_class(cls)
