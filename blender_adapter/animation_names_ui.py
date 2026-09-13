# SPDX-License-Identifier: GPL-3.0-or-later
"""Artist-facing controls for animation clip names and lifecycle."""
import math
import bpy
from bpy.props import EnumProperty, StringProperty
from .animation import add_flight, add_idle, add_locomotion, add_run, clip_export_name, generated_action, set_clip_export_name
from .animation_lifecycle import exportable_actions, register_animation_action, remove_animation
from .animation_records import animation_record, has_animation_record
from .asset_structure import asset_rigs
from .core import AnimationSource
from .workflow import find_character, provider_for


def _character(context):
    settings=getattr(context.scene,'humanoid_settings',None) if context.scene else None
    root=settings.target if settings and settings.target else find_character(context.object)
    return root if root and context.scene.objects.get(root.name)==root else None

def _clip_label(action):
    if has_animation_record(action):
        try:
            r=animation_record(action); return r.display_name or r.export_name or action.name
        except ValueError: pass
    return str(action.get('asset_assistant_clip') or action.name)

def _clip_source(action):
    if has_animation_record(action):
        try:return animation_record(action).source.value.replace('_',' ').title()
        except ValueError:return 'Managed'
    return 'Generated (Legacy)' if action.get('asset_assistant_generated') else 'Unmanaged'

def _remove_button_text(action): return 'Delete Clip'
def _rig(root):
    rigs=asset_rigs(root)
    if len(rigs)!=1: raise ValueError('Animation editing requires exactly one base rig.')
    return rigs[0]
def _activate_action(root,action,scene):
    rig=_rig(root); rig.animation_data_create(); rig.animation_data.action=action
    start,end=action.frame_range; scene.frame_start=int(math.floor(start)); scene.frame_end=max(scene.frame_start,int(math.ceil(end))); scene.frame_set(scene.frame_start); return rig
def _is_active_action(root,action):
    try: rig=_rig(root)
    except ValueError:return False
    return rig.animation_data is not None and rig.animation_data.action==action
def _is_playing_action(root,action,context):
    screen=getattr(context,'screen',None); return bool(screen and getattr(screen,'is_animation_playing',False) and _is_active_action(root,action))
def _stop_playback(context):
    screen=getattr(context,'screen',None)
    if screen and getattr(screen,'is_animation_playing',False): bpy.ops.screen.animation_cancel(restore_frame=False)
def _prepare_action_edit(root,action,context):
    _stop_playback(context); rig=_activate_action(root,action,context.scene)
    if context.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); context.view_layer.objects.active=rig; bpy.ops.object.mode_set(mode='POSE'); return rig

def _remove_action(root,action,animation_id=''):
    if root is None or action is None: raise ValueError('Choose a valid asset and animation clip first.')
    if has_animation_record(action):
        record=animation_record(action)
        if animation_id and record.animation_id!=animation_id: raise ValueError('Animation identity changed; refresh the clip library before deleting it.')
        removed=remove_animation(root,record.animation_id); return 'Deleted animation from Blender: '+removed.display_name
    if not action.get('asset_assistant_generated') or action not in exportable_actions(root): raise ValueError('Only managed or Asset Assistant-owned animations can be deleted here.')
    rigs=asset_rigs(root)
    if len(rigs)==1 and rigs[0].animation_data is not None and rigs[0].animation_data.action==action: rigs[0].animation_data.action=None
    name=action.name; bpy.data.actions.remove(action); return 'Deleted animation from Blender: '+name

class ASSET_ASSISTANT_OT_rename_animation_clip(bpy.types.Operator):
    bl_idname='asset_assistant.rename_animation_clip'; bl_label='Rename Animation Clip'; bl_options={'REGISTER','UNDO'}
    clip_name:StringProperty(options={'HIDDEN'}); export_name:StringProperty(name='Export Name')
    def invoke(self,context,event):
        root=_character(context); action=generated_action(root,self.clip_name) if root else None
        if action is None:self.report({'ERROR'},'Generate this clip before renaming it.');return {'CANCELLED'}
        self.export_name=clip_export_name(action);return context.window_manager.invoke_props_dialog(self)
    def execute(self,context):
        try: action=set_clip_export_name(_character(context),self.clip_name,self.export_name)
        except ValueError as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene.humanoid_settings.validation_results.clear();self.report({'INFO'},self.clip_name+' will export as '+clip_export_name(action)+'.');return {'FINISHED'}

class ASSET_ASSISTANT_OT_preview_animation_clip(bpy.types.Operator):
    bl_idname='asset_assistant.preview_animation_clip';bl_label='Play / Pause Clip';action_name:StringProperty(options={'HIDDEN'})
    def execute(self,context):
        root=_character(context);action=bpy.data.actions.get(self.action_name)
        if root is None or action is None:return {'CANCELLED'}
        if _is_playing_action(root,action,context):_stop_playback(context);return {'FINISHED'}
        _stop_playback(context);_activate_action(root,action,context.scene);bpy.ops.screen.animation_play();return {'FINISHED'}

class ASSET_ASSISTANT_OT_edit_animation_clip(bpy.types.Operator):
    bl_idname='asset_assistant.edit_animation_clip';bl_label='Edit Animation';action_name:StringProperty(options={'HIDDEN'})
    def execute(self,context):
        root=_character(context);action=bpy.data.actions.get(self.action_name)
        if root is None or action is None:return {'CANCELLED'}
        try:_prepare_action_edit(root,action,context)
        except (ValueError,RuntimeError,AttributeError) as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class ASSET_ASSISTANT_OT_toggle_animation_autokey(bpy.types.Operator):
    bl_idname='asset_assistant.toggle_animation_autokey';bl_label='Toggle Auto Key'
    def execute(self,context):context.scene.tool_settings.use_keyframe_insert_auto=not context.scene.tool_settings.use_keyframe_insert_auto;return {'FINISHED'}

class ASSET_ASSISTANT_OT_new_animation_clip(bpy.types.Operator):
    bl_idname='asset_assistant.new_animation_clip';bl_label='Create Animation';bl_options={'REGISTER','UNDO'}
    template:EnumProperty(name='Start From',items=[('EMPTY','Empty','Start from scratch'),('IDLE','Idle','Generate provider idle'),('WALK','Walk','Generate provider locomotion'),('RUN','Run','Generate provider run'),('FLY','Fly','Generate provider flight')],default='EMPTY')
    name:StringProperty(name='Name',default='New Animation')
    def invoke(self,context,event):return context.window_manager.invoke_props_dialog(self)
    def execute(self,context):
        root=_character(context)
        if root is None:return {'CANCELLED'}
        try:
            if self.template=='IDLE': action,_=add_idle(root,context.scene)
            elif self.template=='WALK': action,_=add_locomotion(root,context.scene)
            elif self.template=='RUN': action,_=add_run(root,context.scene)
            elif self.template=='FLY': action,_=add_flight(root,context.scene)
            else:
                name=self.name.strip()
                if not name:raise ValueError('Animation name cannot be empty.')
                action=bpy.data.actions.new(name);_activate_action(root,action,context.scene)
                register_animation_action(root,action,source=AnimationSource.ARTIST,display_name=action.name,export_name=action.name,fps=context.scene.render.fps/max(context.scene.render.fps_base,.0001))
            _prepare_action_edit(root,action,context)
        except (ValueError,RuntimeError,AttributeError,TypeError) as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene.humanoid_settings.validation_results.clear();self.report({'INFO'},'Created '+_clip_label(action)+' and opened it for editing.');return {'FINISHED'}

class ASSET_ASSISTANT_OT_remove_animation_clip(bpy.types.Operator):
    bl_idname='asset_assistant.remove_animation_clip';bl_label='Delete Animation Clip';bl_options={'REGISTER','UNDO'}
    action_name:StringProperty(options={'HIDDEN'});animation_id:StringProperty(options={'HIDDEN'})
    def invoke(self,context,event):return context.window_manager.invoke_confirm(self,event) if bpy.data.actions.get(self.action_name) else {'CANCELLED'}
    def execute(self,context):
        try:message=_remove_action(_character(context),bpy.data.actions.get(self.action_name),self.animation_id)
        except (ValueError,RuntimeError,AttributeError) as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene.humanoid_settings.validation_results.clear();self.report({'INFO'},message);return {'FINISHED'}

class ASSET_ASSISTANT_PT_animation_names(bpy.types.Panel):
    bl_label='Clip Library';bl_idname='ASSET_ASSISTANT_PT_animation_names';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Animations';bl_parent_id='HUMANOID_PT_animations'
    @classmethod
    def poll(cls,context):
        root=_character(context) if context.scene else None;return root is not None and len(asset_rigs(root))==1
    def draw(self,context):
        layout=self.layout;root=_character(context);actions=sorted(exportable_actions(root),key=lambda a:_clip_label(a).lower())
        intro=layout.box();intro.label(text='Animation Clips',icon='ACTION');intro.label(text='Create from Empty or a supported motion preset.')
        row=intro.row(align=True);row.operator('asset_assistant.new_animation_clip',text='Create Animation',icon='ADD');row.operator('asset_assistant.toggle_animation_autokey',text='Auto Key: On' if context.scene.tool_settings.use_keyframe_insert_auto else 'Auto Key: Off',icon='REC')
        try:
            p=provider_for(root); supported=[]
            if getattr(p,'supports_idle',False):supported.append('Idle')
            if getattr(p,'supports_locomotion',False):supported.append(getattr(p,'locomotion_label','Walk'))
            if getattr(p,'supports_run',False):supported.append('Run')
            if getattr(p,'supports_flight',False):supported.append('Fly')
            if supported:intro.label(text='Generated presets: '+', '.join(supported))
        except (ValueError,TypeError,AttributeError):intro.label(text='Imported rigs: Empty is available; generated presets require a mapped provider rig.',icon='INFO')
        for action in actions:
            box=layout.box();title=box.row(align=True);title.label(text=_clip_label(action),icon='ACTION');title.label(text=_clip_source(action));box.label(text='Export Name: '+clip_export_name(action))
            controls=box.row(align=True);playing=_is_playing_action(root,action,context);play=controls.operator('asset_assistant.preview_animation_clip',text='Pause' if playing else 'Play',icon='PAUSE' if playing else 'PLAY');play.action_name=action.name
            edit=controls.operator('asset_assistant.edit_animation_clip',text='Edit',icon='POSE_HLT');edit.action_name=action.name
            remove=controls.operator('asset_assistant.remove_animation_clip',text='Delete',icon='TRASH');remove.action_name=action.name
            if has_animation_record(action):
                try:remove.animation_id=animation_record(action).animation_id
                except ValueError:remove.animation_id=''
        try:
            from . import animation_artist_ui
            animation_artist_ui.draw_edit_helpers(layout,context,root)
        except (ImportError,AttributeError):pass
        layout.label(text='Delete removes the Action from this Blender file. The original import is unchanged.')

_CLASSES=(ASSET_ASSISTANT_OT_rename_animation_clip,ASSET_ASSISTANT_OT_preview_animation_clip,ASSET_ASSISTANT_OT_edit_animation_clip,ASSET_ASSISTANT_OT_toggle_animation_autokey,ASSET_ASSISTANT_OT_new_animation_clip,ASSET_ASSISTANT_OT_remove_animation_clip,ASSET_ASSISTANT_PT_animation_names)
def register():
    for cls in _CLASSES:bpy.utils.register_class(cls)
def unregister():
    for cls in reversed(_CLASSES):bpy.utils.unregister_class(cls)
