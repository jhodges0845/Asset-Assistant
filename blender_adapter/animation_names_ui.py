# SPDX-License-Identifier: GPL-3.0-or-later
"""Artist-facing controls for animation clip names and lifecycle."""

import math

import bpy
from bpy.props import StringProperty

from .animation import clip_export_name, generated_action, set_clip_export_name
from .animation_lifecycle import exportable_actions, register_animation_action, remove_animation
from .animation_records import animation_record, has_animation_record
from .asset_structure import asset_rigs
from .core import AnimationSource
from .workflow import find_character


def _character(context):
    settings = getattr(context.scene, 'humanoid_settings', None) if context.scene else None
    root = settings.target if settings and settings.target else find_character(context.object)
    return root if root and context.scene.objects.get(root.name) == root else None


def _clip_label(action):
    if has_animation_record(action):
        try:
            record = animation_record(action)
            return record.display_name or record.export_name or action.name
        except ValueError:
            pass
    return str(action.get('asset_assistant_clip') or action.name)


def _clip_source(action):
    if has_animation_record(action):
        try:
            return animation_record(action).source.value.replace('_', ' ').title()
        except ValueError:
            return 'Managed'
    return 'Generated (Legacy)' if action.get('asset_assistant_generated') else 'Unmanaged'


def _remove_button_text(action):
    return 'Delete Clip'


def _rig(root):
    rigs = asset_rigs(root)
    if len(rigs) != 1:
        raise ValueError('Animation editing requires exactly one base rig.')
    return rigs[0]


def _activate_action(root, action, scene):
    rig = _rig(root)
    rig.animation_data_create()
    rig.animation_data.action = action
    start, end = action.frame_range
    scene.frame_start = int(math.floor(start))
    scene.frame_end = max(scene.frame_start, int(math.ceil(end)))
    scene.frame_set(scene.frame_start)
    return rig


def _is_active_action(root, action):
    try:
        rig = _rig(root)
    except ValueError:
        return False
    return rig.animation_data is not None and rig.animation_data.action == action


def _is_playing_action(root, action, context):
    screen = getattr(context, 'screen', None)
    return bool(screen and getattr(screen, 'is_animation_playing', False) and _is_active_action(root, action))


def _stop_playback(context):
    screen = getattr(context, 'screen', None)
    if screen and getattr(screen, 'is_animation_playing', False):
        bpy.ops.screen.animation_cancel(restore_frame=False)


def _prepare_action_edit(root, action, context):
    _stop_playback(context)
    rig = _activate_action(root, action, context.scene)
    if context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    return rig


def _remove_action(root, action, animation_id=''):
    """Delete a clip from both Asset Assistant and the current Blender file."""
    if root is None or action is None:
        raise ValueError('Choose a valid asset and animation clip first.')

    if has_animation_record(action):
        record = animation_record(action)
        if animation_id and record.animation_id != animation_id:
            raise ValueError('Animation identity changed; refresh the clip library before deleting it.')
        removed = remove_animation(root, record.animation_id)
        return 'Deleted animation from Blender: ' + removed.display_name

    if not action.get('asset_assistant_generated') or action not in exportable_actions(root):
        raise ValueError('Only managed or Asset Assistant-owned animations can be deleted here.')
    rigs = asset_rigs(root)
    if len(rigs) == 1 and rigs[0].animation_data is not None and rigs[0].animation_data.action == action:
        rigs[0].animation_data.action = None
    name = action.name
    bpy.data.actions.remove(action)
    return 'Deleted animation from Blender: ' + name


class ASSET_ASSISTANT_OT_rename_animation_clip(bpy.types.Operator):
    bl_idname = 'asset_assistant.rename_animation_clip'
    bl_label = 'Rename Animation Clip'
    bl_description = 'Choose the animation name written to game-engine exports'
    bl_options = {'REGISTER', 'UNDO'}

    clip_name: StringProperty(options={'HIDDEN'})
    export_name: StringProperty(name='Export Name')

    def invoke(self, context, event):
        root = _character(context)
        action = generated_action(root, self.clip_name) if root else None
        if action is None:
            self.report({'ERROR'}, 'Generate this clip before renaming it.')
            return {'CANCELLED'}
        self.export_name = clip_export_name(action)
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        root = _character(context)
        if root is None:
            self.report({'ERROR'}, 'Choose a generated character first.')
            return {'CANCELLED'}
        try:
            action = set_clip_export_name(root, self.clip_name, self.export_name)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        context.scene.humanoid_settings.validation_results.clear()
        self.report({'INFO'}, self.clip_name + ' will export as ' + clip_export_name(action) + '.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_preview_animation_clip(bpy.types.Operator):
    bl_idname = 'asset_assistant.preview_animation_clip'
    bl_label = 'Play / Pause Clip'
    bl_description = 'Play this clip, or pause it when it is already playing'

    action_name: StringProperty(options={'HIDDEN'})

    def execute(self, context):
        root = _character(context)
        action = bpy.data.actions.get(self.action_name)
        if root is None or action is None:
            self.report({'ERROR'}, 'The asset or animation Action no longer exists.')
            return {'CANCELLED'}
        try:
            if _is_playing_action(root, action, context):
                _stop_playback(context)
                self.report({'INFO'}, 'Paused ' + _clip_label(action) + '.')
                return {'FINISHED'}
            _stop_playback(context)
            _activate_action(root, action, context.scene)
            bpy.ops.screen.animation_play()
        except (ValueError, RuntimeError, AttributeError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Playing ' + _clip_label(action) + '.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_edit_animation_clip(bpy.types.Operator):
    bl_idname = 'asset_assistant.edit_animation_clip'
    bl_label = 'Edit Animation'
    bl_description = 'Make this Action active, select its rig and enter Pose Mode for keyframe editing'

    action_name: StringProperty(options={'HIDDEN'})

    def execute(self, context):
        root = _character(context)
        action = bpy.data.actions.get(self.action_name)
        if root is None or action is None:
            self.report({'ERROR'}, 'The asset or animation Action no longer exists.')
            return {'CANCELLED'}
        try:
            _prepare_action_edit(root, action, context)
        except (ValueError, RuntimeError, AttributeError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Editing ' + _clip_label(action) + '. Move bones and insert keyframes, or enable Auto Key.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_toggle_animation_autokey(bpy.types.Operator):
    bl_idname = 'asset_assistant.toggle_animation_autokey'
    bl_label = 'Toggle Auto Key'
    bl_description = 'Toggle Blender Auto Key so pose changes are recorded as keyframes'

    def execute(self, context):
        tools = context.scene.tool_settings
        tools.use_keyframe_insert_auto = not tools.use_keyframe_insert_auto
        self.report({'INFO'}, 'Auto Key enabled.' if tools.use_keyframe_insert_auto else 'Auto Key disabled.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_new_animation_clip(bpy.types.Operator):
    bl_idname = 'asset_assistant.new_animation_clip'
    bl_label = 'New Animation'
    bl_description = 'Create a new editable Blender Action for this asset'
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name='Name', default='New Animation')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        root = _character(context)
        name = self.name.strip()
        if root is None:
            self.report({'ERROR'}, 'Choose an asset first.')
            return {'CANCELLED'}
        if not name:
            self.report({'ERROR'}, 'Animation name cannot be empty.')
            return {'CANCELLED'}
        action = bpy.data.actions.new(name)
        try:
            _activate_action(root, action, context.scene)
            register_animation_action(
                root,
                action,
                source=AnimationSource.ARTIST,
                display_name=action.name,
                export_name=action.name,
                fps=context.scene.render.fps / max(context.scene.render.fps_base, 0.0001),
            )
        except (ValueError, RuntimeError, AttributeError) as error:
            bpy.data.actions.remove(action)
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        settings = getattr(context.scene, 'humanoid_settings', None)
        if settings is not None:
            settings.validation_results.clear()
        self.report({'INFO'}, 'Created ' + action.name + '. Use Edit to pose and keyframe the rig.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_remove_animation_clip(bpy.types.Operator):
    bl_idname = 'asset_assistant.remove_animation_clip'
    bl_label = 'Delete Animation Clip'
    bl_description = 'Permanently delete this animation Action from the current Blender file'
    bl_options = {'REGISTER', 'UNDO'}

    action_name: StringProperty(options={'HIDDEN'})
    animation_id: StringProperty(options={'HIDDEN'})

    def invoke(self, context, event):
        action = bpy.data.actions.get(self.action_name)
        if action is None:
            self.report({'ERROR'}, 'The animation Action no longer exists.')
            return {'CANCELLED'}
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        root = _character(context)
        action = bpy.data.actions.get(self.action_name)
        try:
            message = _remove_action(root, action, self.animation_id)
        except (ValueError, RuntimeError, AttributeError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}

        settings = getattr(context.scene, 'humanoid_settings', None)
        if settings is not None:
            settings.validation_results.clear()
        self.report({'INFO'}, message)
        return {'FINISHED'}


class ASSET_ASSISTANT_PT_animation_names(bpy.types.Panel):
    bl_label = 'Clip Library'
    bl_idname = 'ASSET_ASSISTANT_PT_animation_names'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animations'
    bl_parent_id = 'HUMANOID_PT_animations'

    @classmethod
    def poll(cls, context):
        root = _character(context) if context.scene else None
        return root is not None and len(asset_rigs(root)) == 1

    def draw(self, context):
        layout = self.layout
        root = _character(context)
        actions = sorted(exportable_actions(root), key=lambda action: _clip_label(action).lower())

        intro = layout.box()
        intro.label(text='Animation Clips', icon='ACTION')
        intro.label(text='Play, edit, create and manage the Blender Actions for this asset.')
        create_row = intro.row(align=True)
        create_row.operator('asset_assistant.new_animation_clip', text='New Animation', icon='ADD')
        autokey = create_row.operator(
            'asset_assistant.toggle_animation_autokey',
            text='Auto Key: On' if context.scene.tool_settings.use_keyframe_insert_auto else 'Auto Key: Off',
            icon='REC',
        )
        intro.label(text='Edit selects the rig and enters Pose Mode. Auto Key records pose changes.')

        if not actions:
            layout.label(text='No animation clips yet. Create one to start animating.', icon='INFO')

        for action in actions:
            box = layout.box()
            title = box.row(align=True)
            title.label(text=_clip_label(action), icon='ACTION')
            title.label(text=_clip_source(action))
            box.label(text='Export Name: ' + clip_export_name(action))

            controls = box.row(align=True)
            playing = _is_playing_action(root, action, context)
            play = controls.operator(
                'asset_assistant.preview_animation_clip',
                text='Pause' if playing else 'Play',
                icon='PAUSE' if playing else 'PLAY',
            )
            play.action_name = action.name
            edit = controls.operator('asset_assistant.edit_animation_clip', text='Edit', icon='POSE_HLT')
            edit.action_name = action.name
            if action.get('asset_assistant_generated'):
                rename = controls.operator('asset_assistant.rename_animation_clip', text='Rename')
                rename.clip_name = str(action.get('asset_assistant_clip') or action.name)

            remove = controls.operator(
                'asset_assistant.remove_animation_clip',
                text='Delete',
                icon='TRASH',
            )
            remove.action_name = action.name
            if has_animation_record(action):
                try:
                    remove.animation_id = animation_record(action).animation_id
                except ValueError:
                    remove.animation_id = ''

        layout.label(text='Delete removes the Action from this Blender file. The original import is unchanged.')


_CLASSES = (
    ASSET_ASSISTANT_OT_rename_animation_clip,
    ASSET_ASSISTANT_OT_preview_animation_clip,
    ASSET_ASSISTANT_OT_edit_animation_clip,
    ASSET_ASSISTANT_OT_toggle_animation_autokey,
    ASSET_ASSISTANT_OT_new_animation_clip,
    ASSET_ASSISTANT_OT_remove_animation_clip,
    ASSET_ASSISTANT_PT_animation_names,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
