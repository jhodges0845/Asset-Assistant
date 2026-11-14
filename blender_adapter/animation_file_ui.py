# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit inspect/apply/discard controls for standalone clips."""
import json
from hashlib import sha256
from pathlib import Path
import bpy
from bpy.props import StringProperty, IntProperty, FloatProperty
from bpy_extras.io_utils import ImportHelper
from .asset_structure import asset_rigs
from .animation_file_compatibility import inspect_animation_file, transfer_animation_file

_PENDING = 'asset_assistant_clip_file_preview'
_ROOT = 'asset_assistant_clip_file_root'
_RIG = 'asset_assistant_clip_file_rig'


def clear_preview(scene):
    for key in (_PENDING, _ROOT, _RIG):
        scene.pop(key, None)


def _root(context):
    from .animation_adoption_ui import _character
    return _character(context)


class ASSET_ASSISTANT_OT_inspect_clip_file(bpy.types.Operator, ImportHelper):
    bl_idname = 'asset_assistant.inspect_clip_file'
    bl_label = 'Inspect Animation File'
    bl_description = 'Inspect compatible FBX/GLB clips without adding them to the asset'
    filter_glob: StringProperty(default='*.fbx;*.glb', options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        root = _root(context)
        return context.mode == 'OBJECT' and root is not None and len(asset_rigs(root)) == 1

    def execute(self, context):
        clear_preview(context.scene)
        try:
            root = _root(context)
            rigs = asset_rigs(root)
            if len(rigs) != 1:
                raise ValueError('Choose one target rig')
            path = Path(self.filepath).resolve()
            if path.suffix.lower() not in ('.fbx', '.glb'):
                raise ValueError('Choose an FBX or GLB file')
            digest = sha256(path.read_bytes()).hexdigest()
            reports = inspect_animation_file(path, rigs[0], context)
            if sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('File changed during inspection; inspect again')
            context.scene[_PENDING] = json.dumps({'path': str(path), 'sha256': digest, 'clips': reports})
            context.scene[_ROOT], context.scene[_RIG] = root, rigs[0]
        except (ValueError, RuntimeError, OSError, TypeError) as error:
            clear_preview(context.scene)
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Review the clips, then explicitly import one into the library.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_apply_clip_file(bpy.types.Operator):
    bl_idname = 'asset_assistant.apply_clip_file'
    bl_label = 'Import Selected Clip'
    bl_options = {'REGISTER', 'UNDO'}
    clip_index: IntProperty(default=0, min=0, options={'HIDDEN'})
    export_name: StringProperty(name='Clip Name')
    fps: FloatProperty(name='Source FPS', default=24, min=1, max=240)

    def invoke(self, context, event):
        self.fps = context.scene.render.fps / context.scene.render.fps_base
        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        try:
            scene = context.scene
            root = _root(context)
            if root is None or root != scene.get(_ROOT) or asset_rigs(root) != (scene.get(_RIG),):
                raise ValueError('Target changed; inspect the animation file again')
            pending = json.loads(scene.get(_PENDING, '{}'))
            if not 0 <= self.clip_index < len(pending.get('clips', ())):
                raise ValueError('Inspect and select a clip first')
            transfer_animation_file(pending['path'], root, context,
                                    expected_sha256=pending['sha256'],
                                    clips={self.clip_index: self.export_name}, fps=self.fps)
        except (ValueError, RuntimeError, OSError, TypeError, KeyError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        clear_preview(scene)
        self.report({'INFO'}, 'Clip added to the library; existing playback is unchanged.')
        return {'FINISHED'}


class ASSET_ASSISTANT_OT_discard_clip_file(bpy.types.Operator):
    bl_idname = 'asset_assistant.discard_clip_file'
    bl_label = 'Discard File Preview'
    def execute(self, context):
        clear_preview(context.scene)
        return {'FINISHED'}


def draw_file_import(layout, context):
    box = layout.box()
    box.label(text='ANIMATION FILE', icon='IMPORT')
    box.operator('asset_assistant.inspect_clip_file')
    try:
        pending = json.loads(context.scene.get(_PENDING, '{}'))
    except (ValueError, TypeError):
        pending = {}
    if pending:
        box.label(text=Path(pending['path']).name)
        for index, clip in enumerate(pending['clips']):
            row = box.row()
            row.label(text=clip['name'])
            op = row.operator('asset_assistant.apply_clip_file', text='Import')
            op.clip_index = index
            op.export_name = clip['name']
        box.operator('asset_assistant.discard_clip_file')


_CLASSES = (ASSET_ASSISTANT_OT_inspect_clip_file, ASSET_ASSISTANT_OT_apply_clip_file,
            ASSET_ASSISTANT_OT_discard_clip_file)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
