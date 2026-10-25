# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit static LOD controls in the Export workspace."""
import bpy
from bpy.props import StringProperty, IntProperty, FloatVectorProperty
from .lod import preview_static_lods, recover_static_lod_preview


def _previews(scene):
    return [collection for collection in scene.collection.children_recursive
            if collection.get('asset_assistant_lod_state') == 'PREVIEW']


class ASSETASSISTANT_OT_lod_preview(bpy.types.Operator):
    bl_idname = 'asset_assistant.lod_preview'
    bl_label = 'Preview Static LODs'
    bl_description = 'Create separate reduced copies using decreasing triangle budgets'
    bl_options = {'REGISTER', 'UNDO'}
    level_count: IntProperty(name='Levels', default=2, min=1, max=4)
    ratios: FloatVectorProperty(
        name='Triangle Ratios', size=4, default=(.5, .25, .125, .0625),
        min=.001, max=.999,
        description='Fraction of source triangles retained; each level must decrease')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, 'level_count')
        for index in range(self.level_count):
            self.layout.prop(self, 'ratios', index=index, text='LOD %d ratio' % (index + 1))
        self.layout.label(text='0.5 retains half the source triangles.')
        self.layout.label(text='Each level must have a smaller budget.')

    def execute(self, context):
        source = context.active_object
        if any(c.get('lod_source') == source for c in _previews(context.scene)):
            self.report({'ERROR'}, 'Apply or cancel the existing preview for this source first')
            return {'CANCELLED'}
        try:
            preview_static_lods(source, context.scene, tuple(self.ratios[:self.level_count]))
        except (ValueError, ReferenceError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Created separate LOD previews; source preserved')
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



class ASSETASSISTANT_OT_lod_inspect(bpy.types.Operator):
    bl_idname = 'asset_assistant.lod_inspect'
    bl_label = 'Measure Surface Deviation'
    bl_description = 'Sample vertices and triangle centers in both directions; not a visual quality guarantee'
    collection_name: StringProperty()
    object_name: StringProperty()

    def execute(self, context):
        from .lod_quality import inspect_static_lod
        collection = bpy.data.collections.get(self.collection_name)
        if collection not in _previews(context.scene):
            self.report({'ERROR'}, 'Choose an active preview in this scene')
            return {'CANCELLED'}
        try:
            preview = recover_static_lod_preview(collection)
            level = next((obj for obj in preview.objects if obj.name == self.object_name), None)
            if level is None:
                raise ValueError('Choose a level belonging to this preview')
            result = inspect_static_lod(preview.source, level)
        except (ValueError, ReferenceError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Sampled deviation: max %.6g, RMS %.6g Blender units (%d samples)' %
                    (result['max_distance'], result['rms_distance'], result['sample_count']))
        return {'FINISHED'}


def draw(next_renderer, panel, context, *args):
    next_renderer(panel, context, *args)
    box = panel.layout.box()
    box.label(text='Static LODs', icon='MESH_DATA')
    box.label(text='Choose 1-4 decreasing triangle budgets.')
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
                op = item.operator('asset_assistant.lod_inspect', text='Measure Surface Deviation')
                op.collection_name = collection.name
                op.object_name = obj.name
        row = item.row(align=True)
        for action, label in (('APPLY', 'Apply'), ('CANCEL', 'Discard Preview')):
            op = row.operator('asset_assistant.lod_finish', text=label)
            op.collection_name = collection.name
            op.action = action
    box.label(text='Engine LOD export is not yet supported.')


def install(registry):
    registry.decorate('workspace.export', draw, owner=__name__)


_CLASSES = (ASSETASSISTANT_OT_lod_preview, ASSETASSISTANT_OT_lod_finish, ASSETASSISTANT_OT_lod_inspect)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
