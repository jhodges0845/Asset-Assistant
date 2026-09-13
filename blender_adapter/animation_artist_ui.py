# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender-native helpers that shorten common pose/keyframe editing operations."""

import bpy
from bpy.props import EnumProperty, IntProperty

from .animation_names_ui import _character, _rig


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


def _action_curves(action):
    if action is None:
        return ()
    if hasattr(action, 'fcurves') and not getattr(action, 'is_action_layered', False):
        return tuple(action.fcurves)
    curves = []
    for layer in getattr(action, 'layers', ()):
        for strip in getattr(layer, 'strips', ()):
            if strip.type != 'KEYFRAME':
                continue
            for bag in getattr(strip, 'channelbags', ()):
                curves.extend(bag.fcurves)
    return tuple(curves)


def _key_frames(action):
    frames = set()
    for curve in _action_curves(action):
        frames.update(round(point.co.x) for point in curve.keyframe_points)
    return tuple(sorted(frames))


def _pose_bones(rig):
    selected = tuple(bone for bone in rig.pose.bones if bone.bone.select)
    return selected or tuple(rig.pose.bones)


def _insert_bone_transform_keys(bone):
    bone.keyframe_insert('location', group=bone.name)
    if bone.rotation_mode == 'QUATERNION':
        bone.keyframe_insert('rotation_quaternion', group=bone.name)
    elif bone.rotation_mode == 'AXIS_ANGLE':
        bone.keyframe_insert('rotation_axis_angle', group=bone.name)
    else:
        bone.keyframe_insert('rotation_euler', group=bone.name)
    bone.keyframe_insert('scale', group=bone.name)


class ASSET_ASSISTANT_OT_animation_key_jump(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_key_jump'
    bl_label = 'Jump Keyframe'
    bl_description = 'Move the playhead to the previous or next keyed frame in the active animation'
    direction: IntProperty(default=1, min=-1, max=1)

    def execute(self, context):
        _, action = _active_action(context)
        frames = _key_frames(action)
        current = context.scene.frame_current
        candidates = [frame for frame in frames if frame > current] if self.direction > 0 else [frame for frame in frames if frame < current]
        if not candidates:
            self.report({'INFO'}, 'No more keyframes in that direction.')
            return {'CANCELLED'}
        context.scene.frame_set(min(candidates) if self.direction > 0 else max(candidates))
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_insert_pose_key(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_insert_pose_key'
    bl_label = 'Add Pose Key'
    bl_description = 'Insert location, rotation and scale keys for selected pose bones; uses the whole rig when no bones are selected'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig, action = _active_action(context)
        if rig is None or action is None:
            self.report({'ERROR'}, 'Edit an animation clip first.')
            return {'CANCELLED'}
        for bone in _pose_bones(rig):
            _insert_bone_transform_keys(bone)
        self.report({'INFO'}, 'Pose key added at frame ' + str(context.scene.frame_current) + '.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_delete_pose_key(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_delete_pose_key'
    bl_label = 'Delete Pose Key'
    bl_description = 'Delete transform keys at the current frame for selected pose bones; uses the whole rig when none are selected'
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
    bl_description = 'Copy the currently selected Blender pose bones to the pose clipboard'

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
    bl_description = 'Paste a copied pose onto the current frame; Mirror Paste swaps left and right bone names when Blender can match them'
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
    bl_description = 'Return selected pose bones to their untransformed pose; uses the whole rig when none are selected'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig, _ = _active_action(context)
        if rig is None or context.mode != 'POSE':
            self.report({'ERROR'}, 'Enter animation Edit/Pose Mode first.')
            return {'CANCELLED'}
        for bone in _pose_bones(rig):
            bone.location = (0.0, 0.0, 0.0)
            bone.scale = (1.0, 1.0, 1.0)
            if bone.rotation_mode == 'QUATERNION':
                bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            elif bone.rotation_mode == 'AXIS_ANGLE':
                bone.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
            else:
                bone.rotation_euler = (0.0, 0.0, 0.0)
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_view(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_view'
    bl_label = 'Animation View'
    bl_description = 'Snap the 3D viewport to a useful animation viewing angle and frame the rig'
    view: EnumProperty(items=(
        ('FRONT', 'Front', 'View the character from the front'),
        ('BACK', 'Back', 'View the character from the back'),
        ('LEFT', 'Left', 'View the character from the left side'),
        ('RIGHT', 'Right', 'View the character from the right side'),
        ('TOP', 'Top', 'View the character from above'),
        ('PERSP', 'Perspective', 'Return to a natural perspective view'),
    ))

    def execute(self, context):
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, 'Use this control from the 3D Viewport.')
            return {'CANCELLED'}
        try:
            if self.view == 'PERSP':
                context.area.spaces.active.region_3d.view_perspective = 'PERSP'
            else:
                bpy.ops.view3d.view_axis(type=self.view, align_active=False)
            bpy.ops.view3d.view_selected(use_all_regions=False)
        except (RuntimeError, AttributeError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_hold_pose(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_hold_pose'
    bl_label = 'Hold Pose'
    bl_description = 'Repeat the current pose on a later frame to create a hold without manually re-keying every bone'
    bl_options = {'REGISTER', 'UNDO'}

    frames: IntProperty(name='Hold For Frames', default=6, min=1, max=240)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        rig, action = _active_action(context)
        if rig is None or action is None or context.mode != 'POSE':
            self.report({'ERROR'}, 'Edit an animation clip in Pose Mode first.')
            return {'CANCELLED'}
        scene = context.scene
        start = scene.frame_current
        bones = _pose_bones(rig)
        snapshots = {
            bone.name: (bone.location.copy(), bone.rotation_mode,
                        bone.rotation_quaternion.copy(), bone.rotation_euler.copy(), tuple(bone.rotation_axis_angle), bone.scale.copy())
            for bone in bones
        }
        scene.frame_set(start + self.frames)
        for bone in bones:
            location, mode, quat, euler, axis_angle, scale = snapshots[bone.name]
            bone.location = location
            bone.scale = scale
            if mode == 'QUATERNION':
                bone.rotation_quaternion = quat
            elif mode == 'AXIS_ANGLE':
                bone.rotation_axis_angle = axis_angle
            else:
                bone.rotation_euler = euler
            _insert_bone_transform_keys(bone)
        self.report({'INFO'}, 'Held pose through frame ' + str(start + self.frames) + '.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_shift_keys(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_shift_keys'
    bl_label = 'Shift Keys'
    bl_description = 'Move all keys at or after the current frame earlier or later without changing their spacing'
    bl_options = {'REGISTER', 'UNDO'}

    offset: IntProperty(name='Frames', default=2, min=-240, max=240)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        _, action = _active_action(context)
        if action is None:
            self.report({'ERROR'}, 'Edit an animation clip first.')
            return {'CANCELLED'}
        if self.offset == 0:
            return {'CANCELLED'}
        current = context.scene.frame_current
        changed = 0
        for curve in _action_curves(action):
            for point in curve.keyframe_points:
                if point.co.x + 1e-6 < current:
                    continue
                point.co.x += self.offset
                point.handle_left.x += self.offset
                point.handle_right.x += self.offset
                changed += 1
            curve.update()
        if not changed:
            self.report({'INFO'}, 'No keys at or after the current frame.')
            return {'CANCELLED'}
        self.report({'INFO'}, 'Shifted ' + str(changed) + ' keys by ' + str(self.offset) + ' frames.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_animation_loop_clip(bpy.types.Operator):
    bl_idname = 'asset_assistant.animation_loop_clip'
    bl_label = 'Loop Clip'
    bl_description = 'Add Blender Cycles modifiers to the active Action so its motion repeats before and after the keyed range'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _, action = _active_action(context)
        if action is None:
            self.report({'ERROR'}, 'Edit an animation clip first.')
            return {'CANCELLED'}
        changed = 0
        for curve in _action_curves(action):
            if any(mod.type == 'CYCLES' for mod in curve.modifiers):
                continue
            curve.modifiers.new('CYCLES')
            changed += 1
        if not changed:
            self.report({'INFO'}, 'This clip is already looping on all animated channels.')
        else:
            self.report({'INFO'}, 'Loop enabled on ' + str(changed) + ' animation channels.')
        return {'FINISHED'}


def draw_edit_helpers(layout, context, root):
    rig, action = _active_action(context)
    if rig is None or action is None:
        return
    box = layout.box()
    box.label(text='EDIT ANIMATION: ' + action.name, icon='POSE_HLT')
    box.label(text='Frame ' + str(context.scene.frame_current) + ' • Blender Pose Mode + Actions')

    views = box.row(align=True)
    for view, label in (('FRONT', 'Front'), ('LEFT', 'Left'), ('RIGHT', 'Right'), ('BACK', 'Back')):
        op = views.operator('asset_assistant.animation_view', text=label)
        op.view = view
    views = box.row(align=True)
    top = views.operator('asset_assistant.animation_view', text='Top')
    top.view = 'TOP'
    perspective = views.operator('asset_assistant.animation_view', text='Perspective')
    perspective.view = 'PERSP'

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

    timing = box.box()
    timing.label(text='TIMING HELPERS', icon='TIME')
    row = timing.row(align=True)
    row.operator('asset_assistant.animation_hold_pose', text='Hold Pose')
    row.operator('asset_assistant.animation_shift_keys', text='Shift Keys')
    row.operator('asset_assistant.animation_loop_clip', text='Loop Clip')
    timing.label(text='Hold repeats this pose; Shift moves keys from the playhead forward.')
    box.label(text='Select bones to limit pose/key operations; no selection uses the whole rig.')


_CLASSES = (
    ASSET_ASSISTANT_OT_animation_key_jump,
    ASSET_ASSISTANT_OT_animation_insert_pose_key,
    ASSET_ASSISTANT_OT_animation_delete_pose_key,
    ASSET_ASSISTANT_OT_animation_copy_pose,
    ASSET_ASSISTANT_OT_animation_paste_pose,
    ASSET_ASSISTANT_OT_animation_reset_pose,
    ASSET_ASSISTANT_OT_animation_view,
    ASSET_ASSISTANT_OT_animation_hold_pose,
    ASSET_ASSISTANT_OT_animation_shift_keys,
    ASSET_ASSISTANT_OT_animation_loop_clip,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
