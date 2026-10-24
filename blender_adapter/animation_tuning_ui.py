# SPDX-License-Identifier: GPL-3.0-or-later
"""Artist-facing external inspection/refinement workflow for generated animations."""

import json
import os

import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty

from .animation import generated_actions
from .animation_tuning import animation_inspection_json, apply_animation_json, preview_animation_json


_REQUEST_KEY = "asset_assistant_animation_modify_request"
_PREVIEW_KEY = "asset_assistant_animation_modify_preview"


def _root(context, ui):
    root = ui._character(context)
    if root is None:
        raise ValueError("Choose an Asset Assistant character first")
    if not generated_actions(root):
        raise ValueError("Generate at least one animation before exporting animation inspection")
    return root


class ASSET_ASSISTANT_OT_export_animation_inspection(bpy.types.Operator, ExportHelper):
    bl_idname = "asset_assistant.export_animation_inspection"
    bl_label = "Export Animation Inspection"
    bl_description = "Export generated animation state for external refinement"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        try:
            from . import ui
            root = _root(context, ui)
            path = self.filepath
            if not path.lower().endswith(".json"):
                path += ".json"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(animation_inspection_json(root))
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Animation inspection exported: " + os.path.basename(path))
        return {"FINISHED"}


class ASSET_ASSISTANT_OT_import_animation_changes(bpy.types.Operator, ImportHelper):
    bl_idname = "asset_assistant.import_animation_changes"
    bl_label = "Import Animation Changes"
    bl_description = "Load a returned animation refinement request for preview"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        try:
            from . import ui
            root = _root(context, ui)
            with open(self.filepath, "r", encoding="utf-8") as handle:
                payload = handle.read()
            plan = preview_animation_json(root, payload)
            context.scene[_REQUEST_KEY] = payload
            context.scene[_PREVIEW_KEY] = _summary(plan)
        except (OSError, ValueError, TypeError, RuntimeError, json.JSONDecodeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Animation changes loaded and ready to preview")
        return {"FINISHED"}


def _summary(plan):
    changes = [key for key, changed in plan["changes"].items() if changed]
    if not changes:
        return plan["clip_id"] + ": no effective changes"
    effect = " (regenerates keys)" if any(plan["changes"].get(k) for k in ('duration_seconds','strength')) else " (keeps keyframes)"
    return plan["clip_id"] + ": " + ", ".join(changes) + effect


class ASSET_ASSISTANT_OT_preview_animation_changes(bpy.types.Operator):
    bl_idname = "asset_assistant.preview_animation_changes"
    bl_label = "Preview Animation Changes"
    bl_description = "Validate the loaded animation refinement without changing keyframes"

    @classmethod
    def poll(cls, context):
        return bool(context.scene and context.scene.get(_REQUEST_KEY))

    def execute(self, context):
        try:
            from . import ui
            root = _root(context, ui)
            plan = preview_animation_json(root, context.scene[_REQUEST_KEY])
            context.scene[_PREVIEW_KEY] = _summary(plan)
        except (ValueError, TypeError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, context.scene[_PREVIEW_KEY])
        return {"FINISHED"}


class ASSET_ASSISTANT_OT_apply_animation_changes(bpy.types.Operator):
    bl_idname = "asset_assistant.apply_animation_changes"
    bl_label = "Apply / Save Animation Changes"
    bl_description = "Apply the reviewed request; timing or strength changes regenerate keys, while rename-only changes preserve them"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene and context.scene.get(_REQUEST_KEY)) and context.mode == "OBJECT"

    def execute(self, context):
        try:
            from . import ui
            root = _root(context, ui)
            record = apply_animation_json(root, context.scene, context.scene[_REQUEST_KEY])
            context.scene[_PREVIEW_KEY] = "Applied: " + record.display_name
            del context.scene[_REQUEST_KEY]
            settings = getattr(context.scene, "humanoid_settings", None)
            if settings is not None:
                settings.validation_results.clear()
        except (ValueError, TypeError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Animation changes applied; use Play / Pause to review them")
        return {"FINISHED"}


_CLASSES = (
    ASSET_ASSISTANT_OT_export_animation_inspection,
    ASSET_ASSISTANT_OT_import_animation_changes,
    ASSET_ASSISTANT_OT_preview_animation_changes,
    ASSET_ASSISTANT_OT_apply_animation_changes,
)


def prepare(ui):
    """Append external refinement controls to the existing Animations panel."""
    original_draw = ui.HUMANOID_PT_animations.draw

    def draw(self, context):
        original_draw(self, context)
        layout = self.layout
        box = layout.box()
        box.label(text="External Animation Refinement")
        box.label(text="Export -> refine -> import -> preview -> apply")
        box.operator(ASSET_ASSISTANT_OT_export_animation_inspection.bl_idname)
        box.operator(ASSET_ASSISTANT_OT_import_animation_changes.bl_idname)
        if context.scene.get(_REQUEST_KEY):
            box.operator(ASSET_ASSISTANT_OT_preview_animation_changes.bl_idname)
            box.operator(ASSET_ASSISTANT_OT_apply_animation_changes.bl_idname)
        preview = str(context.scene.get(_PREVIEW_KEY) or "").strip()
        if preview:
            box.label(text=preview)
        box.label(text="Save Editable Checkpoint (.blend) after approval.")

    ui.HUMANOID_PT_animations.draw = draw


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


__all__ = ["prepare", "register", "unregister"]
