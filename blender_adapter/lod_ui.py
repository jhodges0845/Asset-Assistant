# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit static LOD controls in the Export workspace."""
import bpy
from bpy.props import StringProperty
from .lod import preview_static_lods, recover_static_lod_preview


def _previews(scene):
    return [collection for collection in scene.collection.children_recursive
            if collection.get('asset_assistant_lod_state') == 'PREVIEW']


class ASSETASSISTANT_OT_lod_preview(bpy.types.Operator):
    bl_idname = 'asset_assistant.lod_preview'
    bl_label = 'Preview Static LODs'
    bl_description = 'Create separate copies at 50% and 25% of the active mesh triangle count'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        source = context.active_object
        if any(c.get('lod_source') == source for c in _previews(context.scene)):
            self.report({'ERROR'}, 'Apply or cancel the existing preview for this source first')
            return {'CANCELLED'}
        try:
            preview_static_lods(source, context.scene)
        except (ValueError, ReferenceError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Created separate 50% and 25% LOD previews; source preserved')
        return {'FINISHED'}


class ASSETASSISTANT_OT_lod_finish(bpy.types.Operator):
    bl_idname = 'asset_assistant.lod_finish'
    bl_label = 'Finish LOD Preview'
    bl_description = 'Apply the preview or discard its copies; cancelling discards edits to those copies'
    bl_options = {'REGISTER', 'UNDO'}
    collection_name: StringProperty()
    action: StringProperty(default='APPLY')

    def invoke(self, context, event):
        if self.action == 'CANCEL':
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if collection not in _previews(context.scene):
            self.report({'ERROR'}, 'Choose an active preview in this scene')
            return {'CANCELLED'}
        try:
            preview = recover_static_lod_preview(collection)
            if self.action == 'APPLY':
                preview.apply()
            elif self.action == 'CANCEL':
                preview.cancel()
            else:
                raise ValueError('Unknown LOD preview action')
        except (ValueError, ReferenceError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


def draw(next_renderer, panel, context, *args):
    next_renderer(panel, context, *args)
    box = panel.layout.box()
    box.label(text='Static LODs', icon='MESH_DATA')
    box.label(text='Separate copies: 50% and 25%')
    box.label(text='Select one unrigged static mesh.')
    row = box.row()
    row.enabled = context.active_object is not None and context.mode == 'OBJECT'
    row.operator('asset_assistant.lod_preview')
    for collection in _previews(context.scene):
        item = box.box()
        item.label(text=collection.name)
        for obj in collection.objects:
            if 'asset_assistant_lod_triangles' in obj:
                item.label(text='%s: %s triangles' % (obj.name, obj['asset_assistant_lod_triangles']))
        row = item.row(align=True)
        for action, label in (('APPLY', 'Apply'), ('CANCEL', 'Discard Preview')):
            op = row.operator('asset_assistant.lod_finish', text=label)
            op.collection_name = collection.name
            op.action = action
    box.label(text='Engine LOD export is not yet supported.')


def install(registry):
    registry.decorate('workspace.export', draw, owner=__name__)


_CLASSES = (ASSETASSISTANT_OT_lod_preview, ASSETASSISTANT_OT_lod_finish)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
