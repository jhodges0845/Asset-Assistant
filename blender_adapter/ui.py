# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender generation, preparation, validation and file export workflow."""

import textwrap
from math import ceil
import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty

from .adapter import create_character
from .core import OBJECT_TYPES, get_provider, ValidationIssue
from .workflow import add_basic_rig, find_character, is_generated, provider_for
from .animation import add_idle, add_locomotion, activate_generated_action, generated_action
from .targets import get_adapter, is_ready
from .materials import prepare_materials


def _clear_report(settings, context):
    settings.validation_results.clear()
    settings.last_export = ""


def _character_poll(settings, obj):
    return is_generated(obj)


def _character(context):
    root = context.scene.humanoid_settings.target or find_character(context.object)
    return root if root and context.scene.objects.get(root.name) == root else None


def _supports_operation(context, capability):
    if context.scene is None or context.mode != 'OBJECT':
        return False
    root = _character(context)
    if root is None:
        return False
    try:
        return bool(getattr(provider_for(root), capability))
    except (ValueError, TypeError, AttributeError):
        return False


def _select(context, obj):
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj


def _animation_choice(settings):
    return ('Idle', 'supports_idle') if settings.animation_clip == 'IDLE' else ('Walk', 'supports_locomotion')


class HUMANOID_PG_result(bpy.types.PropertyGroup):
    code: StringProperty()
    status: StringProperty()
    message: StringProperty()


class HUMANOID_PG_settings(bpy.types.PropertyGroup):
    # Retained for saved files/scripts; visible navigation uses sidebar categories.
    workflow_tab: EnumProperty(name="Stage", default="MODEL", items=[
        ("MODEL", "Model", "Create a model"),
        ("RIGGING", "Rigging", "Rig an existing character"),
        ("ANIMATION", "Animation", "Animation workflow status"),
        ("VALIDATION", "Validation", "Check the selected character"),
        ("EXPORT", "Export", "Prepare and export a file for the selected application"),
    ])
    output_target: EnumProperty(name="Export To", default="GODOT", update=_clear_report, items=[
        ("GODOT", "Godot (.glb)", "Meshes, materials, rig and animation in GLB"),
        ("UNITY", "Unity (.fbx)", "Meshes, materials, rig and animation in FBX"),
        ("UNREAL", "Unreal Engine (.fbx)", "Meshes, materials, rig and animation in FBX"),
        ("CURA", "Cura (.stl)", "Current pose as a closed solid in millimetres"),
    ])
    last_export: StringProperty()
    target: PointerProperty(name="Object", type=bpy.types.Object, poll=_character_poll, update=_clear_report)
    object_type: EnumProperty(name="Object Type", default="humanoid", items=[
        (p.key, p.label, "Generate " + p.label) for p in OBJECT_TYPES.values()
    ])
    asset_use: EnumProperty(name="Validate For", default="RIGGED", update=_clear_report, items=[
        ("STATIC", "Static Asset", "No skeleton or animation required"),
        ("RIGGED", "Rigged Asset", "Require a skeleton and weights"),
        ("ANIMATED", "Animated Asset", "Also require a keyed animation clip"),
    ])
    require_textures: BoolProperty(name="Image Textures Expected", default=False, update=_clear_report,
                                   description="Require image textures and UV maps; leave off for material-only assets")
    validation_results: CollectionProperty(type=HUMANOID_PG_result)
    animation_clip: EnumProperty(name="Clip", default="IDLE", items=[
        ("IDLE", "Idle", "Generate or select the idle action"),
        ("WALK", "Walk", "Generate or select the in-place walk action"),
    ])
    idle_duration: FloatProperty(name="Cycle (seconds)", default=4, min=1, max=20)
    idle_strength: FloatProperty(name="Motion Strength", default=1, min=0.1, max=2)
    walk_duration: FloatProperty(name="Cycle (seconds)", default=1.2, min=0.5, max=4)
    walk_strength: FloatProperty(name="Motion Strength", default=1, min=0.1, max=2)
    idle_set_range: BoolProperty(name="Set Playback Range", default=True)


def _field_name(provider, field):
    # The blockout fixture uses unprefixed controls; product providers are namespaced.
    return field.key if provider.key == 'humanoid' else provider.key + '_' + field.key


for _provider in OBJECT_TYPES.values():
    for _field in _provider.parameters:
        _property = (EnumProperty(name=_field.label, default=_field.default,
                                 items=[(key, label, label) for key, label in _field.choices])
                     if _field.choices else FloatProperty(name=_field.label, default=_field.default,
                                                         min=_field.minimum, max=_field.maximum))
        HUMANOID_PG_settings.__annotations__[_field_name(_provider, _field)] = _property


class HUMANOID_OT_generate(bpy.types.Operator):
    bl_idname = "humanoid.generate_blockout"
    bl_label = "Generate Model"
    bl_description = "Create a new editable blockout at the 3D cursor"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.mode == "OBJECT"

    def execute(self, context):
        settings = context.scene.humanoid_settings
        try:
            provider = get_provider(settings.object_type)
            values = {field.key: getattr(settings, _field_name(provider, field)) for field in provider.parameters}
            root = create_character(provider.mesh(values), name=provider.label, scene=context.scene)
        except (ValueError, TypeError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        root["object_type"] = settings.object_type
        for key, value in values.items():
            root[key] = value
        root.location = context.scene.cursor.location
        settings.target = root
        settings.asset_use = 'RIGGED' if provider.supports_rig else 'STATIC'
        _select(context, root)
        for obj in root.children:
            obj.select_set(True)
        self.report({"INFO"}, "Model created. " + ('Open Animate > Rig & Pose to add its skeleton.' if provider.supports_rig else 'Open Validation to check this static asset.'))
        return {"FINISHED"}


class HUMANOID_OT_rig(bpy.types.Operator):
    bl_idname = "humanoid.add_basic_rig"
    bl_label = "Add Basic Rig"
    bl_description = "Rig this character using its saved generation dimensions"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _supports_operation(context, 'supports_rig') and not any(
            obj.type == 'ARMATURE' for obj in _character(context).children)

    def execute(self, context):
        try:
            rig = add_basic_rig(_character(context), context)
        except (ValueError, TypeError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        context.scene.humanoid_settings.validation_results.clear()
        _select(context, rig)
        self.report({"INFO"}, "Rig added to the existing model.")
        return {"FINISHED"}


class HUMANOID_OT_pose(bpy.types.Operator):
    bl_idname = "humanoid.enter_pose_mode"
    bl_label = "Enter Pose Mode"

    @classmethod
    def poll(cls, context):
        root = _character(context) if context.scene else None
        return context.mode == "OBJECT" and root is not None and any(o.type == 'ARMATURE' for o in root.children)

    def execute(self, context):
        rig = next(o for o in _character(context).children if o.type == "ARMATURE")
        _select(context, rig)
        bpy.ops.object.mode_set(mode="POSE")
        return {"FINISHED"}


class HUMANOID_OT_idle(bpy.types.Operator):
    """Legacy idle operator retained for saved scripts and older workflows."""
    bl_idname = "humanoid.generate_idle"
    bl_label = "Generate Idle"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _supports_operation(context, 'supports_idle') and sum(
            obj.type == 'ARMATURE' for obj in _character(context).children) == 1

    def execute(self, context):
        settings = context.scene.humanoid_settings
        try:
            action, end = add_idle(_character(context), context.scene, settings.idle_duration, settings.idle_strength)
        except (ValueError, TypeError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if settings.idle_set_range:
            context.scene.frame_end = end
            context.scene.use_preview_range = False
        context.scene.frame_set(context.scene.frame_start)
        settings.validation_results.clear()
        self.report({"INFO"}, "Idle created. Press Play to preview.")
        return {"FINISHED"}


class HUMANOID_OT_animation_clip(bpy.types.Operator):
    bl_idname = 'humanoid.select_animation_clip'
    bl_label = 'Generate / Select Clip'
    bl_description = 'Generate the selected clip once, then switch between generated actions without overwriting edits'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.scene is None or context.mode != 'OBJECT' or _character(context) is None:
            return False
        settings = context.scene.humanoid_settings
        _, capability = _animation_choice(settings)
        return _supports_operation(context, capability) and sum(
            obj.type == 'ARMATURE' for obj in _character(context).children) == 1

    def execute(self, context):
        settings = context.scene.humanoid_settings
        root = _character(context)
        clip_name, _ = _animation_choice(settings)
        existing = generated_action(root, clip_name)
        try:
            if existing is not None:
                action = activate_generated_action(root, clip_name)
                end = max(context.scene.frame_start, ceil(action.frame_range[1]) - 1)
                message = clip_name + ' selected. Existing keys were preserved.'
            elif clip_name == 'Idle':
                action, end = add_idle(root, context.scene, settings.idle_duration, settings.idle_strength)
                message = 'Idle created. Press Play to preview.'
            else:
                action, end = add_locomotion(root, context.scene, settings.walk_duration, settings.walk_strength)
                message = 'Walk created. Press Play to preview.'
        except (ValueError, TypeError, RuntimeError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        if settings.idle_set_range:
            context.scene.frame_end = end
            context.scene.use_preview_range = False
        context.scene.frame_set(context.scene.frame_start)
        settings.validation_results.clear()
        self.report({'INFO'}, message)
        return {'FINISHED'}


class HUMANOID_OT_preview(bpy.types.Operator):
    bl_idname = 'humanoid.preview_idle'
    bl_label = 'Preview Motion Pose'
    bl_description = 'Show the middle of the active clip with the rig in Pose Position'

    @classmethod
    def poll(cls, context):
        root = _character(context) if context.scene else None
        return root is not None and any(o.type == 'ARMATURE' and o.animation_data and
                                       o.animation_data.action for o in root.children)

    def execute(self, context):
        rig = next(o for o in _character(context).children if o.type == 'ARMATURE' and
                   o.animation_data and o.animation_data.action)
        rig.data.pose_position = 'POSE'
        start, end = rig.animation_data.action.frame_range
        frame = (start + end) / 2
        context.scene.frame_set(int(frame), subframe=frame - int(frame))
        return {'FINISHED'}


class HUMANOID_OT_validate(bpy.types.Operator):
    bl_idname = "humanoid.validate_character"
    bl_label = "Run Validation"
    bl_description = "Inspect the current character without changing its meshes or materials"

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.mode == "OBJECT" and _character(context) is not None

    def execute(self, context):
        settings = context.scene.humanoid_settings
        settings.validation_results.clear()
        results = _export_issues(context)
        for issue in results:
            row = settings.validation_results.add()
            row.code, row.status, row.message = issue.code, issue.status, issue.message
        self.report({"INFO"}, "Validation snapshot updated; review the results below.")
        return {"FINISHED"}


def _output_adapter(context):
    settings = context.scene.humanoid_settings
    return get_adapter(settings.output_target, asset_use=settings.asset_use,
                       require_textures=settings.require_textures if settings.output_target != 'CURA' else False)


def _export_issues(context):
    try:
        return _output_adapter(context).prepare(_character(context), context)
    except (ValueError, TypeError, RuntimeError, AttributeError) as error:
        return (ValidationIssue('preparation', 'ERROR', str(error)),)


class HUMANOID_OT_prepare_materials(bpy.types.Operator):
    bl_idname = 'humanoid.prepare_materials'
    bl_label = 'Add Missing Materials'
    bl_description = 'Assign a neutral exportable material only to faces without one; keep existing materials'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.mode == 'OBJECT' and _character(context) is not None

    def execute(self, context):
        prepare_materials(_character(context))
        context.scene.humanoid_settings.validation_results.clear()
        self.report({'INFO'}, 'Missing material assignments filled. Existing materials preserved.')
        return {'FINISHED'}


class HUMANOID_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = 'humanoid.export_asset'
    bl_label = 'Export Asset'
    bl_description = 'Export the selected model after checking all requirements again'
    filename_ext = ''
    filter_glob: StringProperty(default='*.glb', options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        if context.scene is None or context.mode != 'OBJECT' or _character(context) is None:
            return False
        settings = context.scene.humanoid_settings
        if settings.output_target == 'CURA':
            # Cura preparation may need Blender's voxel-remesh operator. Operators
            # must not run from another operator's poll callback, so use the most
            # recent explicit Validation result to enable the button. execute()
            # still performs full validation again before writing any file.
            return is_ready(settings.validation_results)
        # Other targets are read-only during validation and can be checked live.
        return is_ready(_export_issues(context))

    def invoke(self, context, event):
        adapter = _output_adapter(context)
        self.filter_glob = ';'.join('*' + extension for extension in adapter.extensions)
        self.filepath = _character(context).name + adapter.default_extension
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        result = _output_adapter(context).export(_character(context), context, bpy.path.abspath(self.filepath))
        settings = context.scene.humanoid_settings
        settings.validation_results.clear()
        for issue in result.issues:
            row = settings.validation_results.add()
            row.code, row.status, row.message = issue.code, issue.status, issue.message
        if not result.success:
            settings.last_export = ''
            message = next((issue.message for issue in result.issues if issue.status in ('ERROR', 'WARN')), 'Export failed.')
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
        settings.last_export = result.filepath
        self.report({'INFO'}, 'Exported: ' + result.filepath)
        return {'FINISHED'}


def _needs_attention(context, stage):
    codes = {
        'MODEL': {'geometry', 'target_geometry', 'cura_solid', 'export_transform', 'export_units', 'export_modifier'},
        'RIGGING': {'rig', 'target_rig'},
        'ANIMATION': {'animation', 'target_animation', 'export_nla', 'fbx_animation_range', 'export_constraints'},
    }.get(stage)
    return any(issue.status in ('ERROR', 'WARN') and (codes is None or issue.code in codes)
               for issue in _export_issues(context))


def _draw_validation_results(layout, rows, width):
    """Present an existing validation snapshot in severity order without changing it."""
    groups = (
        ("ERROR", "Errors", "ERROR"),
        ("WARN", "Warnings", "INFO"),
        ("PASS", "Passed Checks", "CHECKMARK"),
        ("INFO", "Information", "INFO"),
    )
    for status, label, icon in groups:
        matches = [row for row in rows if row.status == status]
        if not matches:
            continue
        section = layout.box()
        section.label(text=f"{label} ({len(matches)})", icon=icon)
        for result in matches:
            card = section.box()
            card.label(text=result.code.replace("_", " ").title(), icon=icon)
            for line in textwrap.wrap(result.message, width):
                card.label(text=line)


class _WorkflowPanel:
    """Shared stage layout; each registered panel owns a fixed sidebar category."""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    stage = "MODEL"

    def draw_header(self, context):
        attention = _needs_attention(context, self.stage)
        self.layout.label(text='', icon='ERROR' if attention else 'CHECKMARK')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.humanoid_settings
        if context.mode != "OBJECT":
            layout.operator("object.mode_set", text="Return to Object Mode").mode = "OBJECT"
        stage = self.stage
        if stage == "MODEL":
            layout.prop(settings, "object_type")
            for field in get_provider(settings.object_type).parameters:
                layout.prop(settings, _field_name(get_provider(settings.object_type), field))
            layout.operator("humanoid.generate_blockout", icon="OUTLINER_OB_MESH")
            layout.label(text="Creates a new model each time.")
            return
        layout.prop(settings, "target")
        root = _character(context)
        if root is None:
            layout.label(text="Create or choose a character first.")
            return
        has_rig = any(obj.type == "ARMATURE" for obj in root.children)
        try:
            provider = provider_for(root)
        except ValueError as error:
            layout.label(text=str(error))
            return
        if stage == 'RIGGING' and not getattr(provider, 'supports_rig', False):
            layout.label(text=provider.label + ' is a static object.')
            layout.label(text='Use Validation for static asset checks.')
            return
        if stage == 'ANIMATION' and not (getattr(provider, 'supports_idle', False) or
                                         getattr(provider, 'supports_locomotion', False)):
            layout.label(text=provider.label + ' has no generated animation clips.')
            layout.label(text='Use Validation for static or rigged checks.')
            return
        if stage == "RIGGING":
            if has_rig:
                layout.label(text="Rig found; existing rig preserved.")
                layout.operator("humanoid.enter_pose_mode")
                layout.label(text="In Pose Mode: R rotates a bone.")
                layout.label(text="Alt-R clears its rotation.")
            else:
                layout.operator("humanoid.add_basic_rig", icon="ARMATURE_DATA")
                layout.label(text="Uses saved generation dimensions.")
            layout.label(text=("Weighted mesh; joints deform with the rig."
                               if getattr(provider, 'uses_skin_weights', False)
                               else "Rigid parts; no smooth joints yet."))
        elif stage == "ANIMATION":
            if not has_rig:
                layout.label(text="Add a rig before animating.")
            else:
                workspace = layout.box()
                workspace.label(text="Generated Clip", icon="ACTION")
                workspace.prop(settings, 'animation_clip', text="Clip")
                clip_name, capability = _animation_choice(settings)
                supported = bool(getattr(provider, capability, False))
                if not supported:
                    workspace.label(text=provider.label + ' does not support ' + clip_name.lower() + '.', icon="INFO")
                    return

                tuning = workspace.box()
                tuning.label(text="Tune Motion", icon="PREFERENCES")
                if settings.animation_clip == 'IDLE':
                    tuning.prop(settings, "idle_duration")
                    tuning.prop(settings, "idle_strength")
                else:
                    tuning.prop(settings, 'walk_duration')
                    tuning.prop(settings, 'walk_strength')
                tuning.prop(settings, "idle_set_range")

                existing = generated_action(root, clip_name)
                action = workspace.row()
                action.scale_y = 1.25
                action.operator('humanoid.select_animation_clip',
                                text=('Select ' + clip_name if existing else 'Generate ' + clip_name),
                                icon="CHECKMARK" if existing else "ADD")
                workspace.label(text=('Existing generated keys are preserved.' if existing
                                      else 'Creates a separate editable action.'))

                preview = workspace.box()
                preview.label(text="Preview", icon="PLAY")
                controls = preview.row(align=True)
                controls.operator("humanoid.preview_idle", text="Motion Pose", icon="POSE_HLT")
                controls.operator("screen.animation_play", text="Play / Pause", icon="PLAY")
                preview.label(text='All generated clips are exported together.')
                preview.label(text="Artist actions, NLA and drivers are never overwritten.")
        else:
            layout.prop(settings, "output_target")
            if settings.output_target == 'CURA':
                layout.label(text='STL: current pose, millimetres, one solid.')
            else:
                layout.prop(settings, "asset_use")
                layout.prop(settings, "require_textures")
                if stage == 'VALIDATION':
                    layout.operator("humanoid.prepare_materials", icon="MATERIAL")
            if stage == 'VALIDATION':
                layout.operator("humanoid.validate_character", icon="CHECKMARK")
            if stage == 'EXPORT' and settings.output_target == 'CURA':
                # Match the operator poll: Cura's explicit validation is the UI
                # gate, and the export operation performs the expensive repair
                # validation again before any STL is written.
                rows = settings.validation_results
            else:
                rows = _export_issues(context) if stage == 'EXPORT' else settings.validation_results
            if stage == 'EXPORT':
                ready = is_ready(rows)
                confidence = layout.box()
                confidence.label(text='Ready to export.' if ready else 'Needs attention before export.',
                                 icon='CHECKMARK' if ready else 'ERROR')
                if not ready:
                    errors = sum(row.status == "ERROR" for row in rows)
                    warnings = sum(row.status == "WARN" for row in rows)
                    confidence.label(text=f"{errors} errors, {warnings} warnings")
                    confidence.label(text="Review the Validate stage, then rerun validation.")
                action = confidence.row()
                action.scale_y = 1.25
                action.enabled = ready
                action.operator('humanoid.export_asset', text='Export Asset', icon='EXPORT')
                if settings.last_export:
                    confidence.label(text='Saved: ' + settings.last_export, icon='CHECKMARK')
                return

            if rows:
                errors = sum(row.status == "ERROR" for row in rows)
                warnings = sum(row.status == "WARN" for row in rows)
                passes = sum(row.status == "PASS" for row in rows)
                summary = layout.box()
                summary.label(text="Validation Snapshot", icon="CHECKMARK" if errors == 0 else "ERROR")
                summary.label(text=f"{errors} errors  â€¢  {warnings} warnings  â€¢  {passes} passed")
                summary.label(text="Snapshot: rerun after editing.")
                width = max(24, int(context.region.width / 7) - 6)
                _draw_validation_results(layout, rows, width)


class HUMANOID_PT_panel(_WorkflowPanel, bpy.types.Panel):
    bl_label = "Object Generator"
    bl_idname = "HUMANOID_PT_panel"
    bl_category = "Generator"
    stage = "MODEL"


class HUMANOID_PT_rigging(_WorkflowPanel, bpy.types.Panel):
    bl_label = "Rigging"
    bl_idname = "HUMANOID_PT_rigging"
    bl_category = "Rigging"
    stage = "RIGGING"


class HUMANOID_PT_animations(_WorkflowPanel, bpy.types.Panel):
    bl_label = "Animations"
    bl_idname = "HUMANOID_PT_animations"
    bl_category = "Animations"
    stage = "ANIMATION"


class HUMANOID_PT_validation(_WorkflowPanel, bpy.types.Panel):
    bl_label = "Validation"
    bl_idname = "HUMANOID_PT_validation"
    bl_category = "Validation"
    stage = "VALIDATION"


class HUMANOID_PT_export(_WorkflowPanel, bpy.types.Panel):
    bl_label = "Export"
    bl_idname = "HUMANOID_PT_export"
    bl_category = "Export"
    stage = "EXPORT"


_CLASSES = (HUMANOID_PG_result, HUMANOID_PG_settings, HUMANOID_OT_generate,
            HUMANOID_OT_rig, HUMANOID_OT_pose, HUMANOID_OT_idle, HUMANOID_OT_animation_clip,
            HUMANOID_OT_preview, HUMANOID_OT_validate, HUMANOID_OT_prepare_materials, HUMANOID_OT_export,
            HUMANOID_PT_panel, HUMANOID_PT_rigging, HUMANOID_PT_animations,
            HUMANOID_PT_validation, HUMANOID_PT_export)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.humanoid_settings = PointerProperty(type=HUMANOID_PG_settings)


def unregister():
    del bpy.types.Scene.humanoid_settings
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
