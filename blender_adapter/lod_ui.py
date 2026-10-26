# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit static LOD controls in the Export workspace."""
import bpy
from bpy.props import StringProperty, IntProperty, FloatVectorProperty, BoolProperty, FloatProperty
from .lod import preview_static_lods, recover_static_lod_preview


def _previews(scene):
    return [collection for collection in scene.collection.children_recursive
            if collection.get('asset_assistant_lod_state') == 'PREVIEW'
            and not collection.get('lod_skin_preview')]


def _skin_previews(scene):
    return [c for c in scene.collection.children_recursive
            if c.get('asset_assistant_lod_state') == 'PREVIEW' and c.get('lod_skin_preview')]


def _groups(scene):
    return [c for c in scene.collection.children_recursive if c.get('lod_set_state') == 'PREVIEW']


def _group_for(scene, collection):
    for record in _groups(scene):
        if any(record.get(key) == collection for key in record.keys() if key.startswith('member_')):
            return record
    return None


class ASSETASSISTANT_OT_lod_preview(bpy.types.Operator):
    bl_idname = 'asset_assistant.lod_preview'
    bl_label = 'Preview Static LODs'
    bl_description = 'Create separate reduced copies using decreasing triangle budgets'
    bl_options = {'REGISTER', 'UNDO'}
    use_selection: BoolProperty(name='All Selected Meshes', default=False,
                                description='Create one group from the explicit selection; budgets apply per mesh')
    level_count: IntProperty(name='Levels', default=2, min=1, max=4)
    ratios: FloatVectorProperty(
        name='Triangle Ratios', size=4, default=(.5, .25, .125, .0625),
        min=.001, max=.999,
        description='Fraction of source triangles retained; each level must decrease')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, 'use_selection')
        self.layout.prop(self, 'level_count')
        for index in range(self.level_count):
            self.layout.prop(self, 'ratios', index=index, text='LOD %d ratio' % (index + 1))
        self.layout.label(text='0.5 retains half the source triangles.')
        self.layout.label(text='Each level must have a smaller budget.')

    def execute(self, context):
        source = context.active_object
        sources = tuple(context.selected_objects) if self.use_selection else (source,)
        if any(c.get('lod_source') in sources for c in _previews(context.scene)):
            self.report({'ERROR'}, 'Apply or cancel the existing preview for this source first')
            return {'CANCELLED'}
        try:
            ratios = tuple(self.ratios[:self.level_count])
            if self.use_selection:
                from .lod_sets import preview_static_lod_set
                preview_static_lod_set(sources, context.scene, ratios)
            else:
                preview_static_lods(source, context.scene, ratios)
        except (ValueError, ReferenceError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Created separate LOD previews; source preserved')
        return {'FINISHED'}


class ASSETASSISTANT_OT_skin_lod_preview(bpy.types.Operator):
    bl_idname = 'asset_assistant.skin_lod_preview'
    bl_label = 'Preview Skinned LOD'
    bl_description = 'Build an experimental reduced copy bound to the existing rig'
    bl_options = {'REGISTER', 'UNDO'}
    ratio: FloatProperty(name='Triangle Ratio', default=.5, min=.001, max=.999)
    max_distance: FloatProperty(name='Max Transfer Distance', default=.02, min=0,
        description='Maximum rest-surface distance in world-space Blender units')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, 'ratio')
        self.layout.prop(self, 'max_distance')
        self.layout.label(text='Distance is in Blender world units.')
        self.layout.label(text='Review motion before applying.')

    def execute(self, context):
        from .lod_skin_preview import preview_skin_lods
        source = context.active_object
        if any(c.get('lod_source') == source for c in _previews(context.scene) + _skin_previews(context.scene)):
            self.report({'ERROR'}, 'Apply or discard the existing preview first')
            return {'CANCELLED'}
        try:
            preview_skin_lods(source, context.scene, ratios=(self.ratio,), max_distance=self.max_distance)
        except (ValueError, ReferenceError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Skinned preview created; review motion before Apply')
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
        if collection not in _previews(context.scene) + _groups(context.scene) + _skin_previews(context.scene):
            self.report({'ERROR'}, 'Choose an active preview in this scene')
            return {'CANCELLED'}
        try:
            if collection in _skin_previews(context.scene):
                from .lod_skin_preview import recover_skin_lod_preview
                preview = recover_skin_lod_preview(collection)
            elif collection in _groups(context.scene):
                from .lod_sets import recover_static_lod_set
                preview = recover_static_lod_set(collection)
            else:
                if _group_for(context.scene, collection) is not None:
                    raise ValueError('Apply or discard the complete LOD group')
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
        from .lod_quality import inspect_static_lod, inspect_posed_skin_lod
        collection = bpy.data.collections.get(self.collection_name)
        if collection not in _previews(context.scene) + _skin_previews(context.scene):
            self.report({'ERROR'}, 'Choose an active preview in this scene')
            return {'CANCELLED'}
        try:
            skinned = bool(collection.get('lod_skin_preview'))
            if skinned:
                from .lod_skin_preview import recover_skin_lod_preview
                preview = recover_skin_lod_preview(collection)
            else:
                preview = recover_static_lod_preview(collection)
            level = next((obj for obj in preview.objects if obj.name == self.object_name), None)
            if level is None:
                raise ValueError('Choose a level belonging to this preview')
            result = (inspect_posed_skin_lod(preview.source, level, context.evaluated_depsgraph_get())
                      if skinned else inspect_static_lod(preview.source, level))
        except (ValueError, ReferenceError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Sampled deviation: max %.6g, RMS %.6g Blender units (%d samples)' %
                    (result['max_distance'], result['rms_distance'], result['sample_count']))
        return {'FINISHED'}


class ASSETASSISTANT_OT_lod_export(bpy.types.Operator):
    bl_idname = 'asset_assistant.lod_export_bundle'
    bl_label = 'Export Static LOD Bundle'
    bl_description = 'Write separate GLBs and a manifest; engine LOD switching must be configured separately'
    collection_name: StringProperty(options={'HIDDEN'})
    directory: StringProperty(name='Parent Directory', subtype='DIR_PATH')
    bundle_name: StringProperty(name='New Bundle Folder', default='LOD_bundle')
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from pathlib import Path
        from .lod_export import export_static_lod_bundle
        name = self.bundle_name.strip()
        if not name or name in ('.', '..') or any(c in name for c in '/\\:'):
            self.report({'ERROR'}, 'Choose a simple new folder name')
            return {'CANCELLED'}
        collection = bpy.data.collections.get(self.collection_name)
        if collection is None:
            self.report({'ERROR'}, 'LOD collection no longer exists')
            return {'CANCELLED'}
        if not self.directory:
            self.report({'ERROR'}, 'Choose an existing parent directory')
            return {'CANCELLED'}
        try:
            result = export_static_lod_bundle(collection, context, Path(bpy.path.abspath(self.directory)) / name)
        except (ValueError, OSError, ReferenceError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Exported %d GLB levels; configure engine LOD switching separately' % len(result['levels']))
        return {'FINISHED'}


def draw(next_renderer, panel, context, *args):
    next_renderer(panel, context, *args)
    box = panel.layout.box()
    box.label(text='Static LODs', icon='MESH_DATA')
    box.label(text='Choose 1-4 decreasing triangle budgets.')
    box.label(text='Active mesh or all selected static meshes.')
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
        if _group_for(context.scene, collection) is not None:
            item.label(text='Resolve with its LOD group below.')
            continue
        row = item.row(align=True)
        for action, label in (('APPLY', 'Apply'), ('CANCEL', 'Discard Preview')):
            op = row.operator('asset_assistant.lod_finish', text=label)
            op.collection_name = collection.name
            op.action = action
    for record in _groups(context.scene):
        item = box.box()
        item.label(text=record.name)
        item.label(text='%s source meshes' % record.get('lod_set_count', '?'))
        row = item.row(align=True)
        for action, label in (('APPLY', 'Apply Group'), ('CANCEL', 'Discard Group')):
            op = row.operator('asset_assistant.lod_finish', text=label)
            op.collection_name = record.name
            op.action = action
    applied = [c for c in context.scene.collection.children_recursive
               if (c.get('asset_assistant_lod_state') == 'APPLIED' and not c.get('lod_skin_preview'))
               or c.get('lod_set_state') == 'APPLIED']
    grouped = {c.get(key) for c in applied if c.get('lod_set_state') == 'APPLIED'
               for key in c.keys() if key.startswith('member_')}
    for collection in applied:
        if collection in grouped:
            continue
        item = box.box()
        item.label(text=collection.name)
        op = item.operator('asset_assistant.lod_export_bundle')
        op.collection_name = collection.name
    skin = panel.layout.box()
    skin.label(text='Skinned LOD (Experimental)', icon='ARMATURE_DATA')
    row = skin.row()
    row.enabled = context.active_object is not None and context.mode == 'OBJECT'
    row.operator('asset_assistant.skin_lod_preview')
    skin.label(text='Select the skinned mesh, not the rig.')
    for collection in _skin_previews(context.scene):
        item = skin.box()
        item.label(text=collection.name)
        item.label(text='Inspect animation before Apply.')
        for obj in collection.objects:
            op = item.operator('asset_assistant.lod_inspect', text='Measure Pose: ' + obj.name)
            op.collection_name = collection.name
            op.object_name = obj.name
        row = item.row(align=True)
        for action, label in (('APPLY', 'Apply'), ('CANCEL', 'Discard Preview')):
            op = row.operator('asset_assistant.lod_finish', text=label)
            op.collection_name = collection.name
            op.action = action
    skin.label(text='Engine LOD export is not yet supported.')


def install(registry):
    registry.decorate('workspace.export', draw, owner=__name__)


_CLASSES = (ASSETASSISTANT_OT_lod_export, ASSETASSISTANT_OT_skin_lod_preview, ASSETASSISTANT_OT_lod_preview, ASSETASSISTANT_OT_lod_finish, ASSETASSISTANT_OT_lod_inspect)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
