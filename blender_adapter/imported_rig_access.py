# SPDX-License-Identifier: GPL-3.0-or-later
"""Expose enrolled imported rigs through clear Blender rig-editing affordances.

Imported files are first-class Asset Assistant working assets after normalization.
The Rig workspace therefore must not stop at generated-provider lookup: an imported
rig is already a valid Blender rig and should be selectable, poseable, and easy to
return from without requiring the artist to hunt for Blender's mode selector.
"""

import bpy

from .asset_structure import asset_rigs
from .workflow import is_external_asset


_ORIGINAL_WORKFLOW_DRAW = None


def _target(context):
    settings = getattr(getattr(context, "scene", None), "humanoid_settings", None)
    root = getattr(settings, "target", None) if settings is not None else None
    if root is None or context.scene.objects.get(root.name) != root:
        return None
    return root


def _base_rig(context):
    root = _target(context)
    if root is None:
        return None
    rigs = asset_rigs(root)
    return rigs[0] if len(rigs) == 1 else None


def _select_only(context, obj):
    for selected in tuple(context.selected_objects):
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj


class ASSET_ASSISTANT_OT_select_base_rig(bpy.types.Operator):
    bl_idname = "asset_assistant.select_base_rig"
    bl_label = "Select Rig"
    bl_description = "Select the current Asset Assistant base armature in Blender"

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and _base_rig(context) is not None

    def execute(self, context):
        rig = _base_rig(context)
        if rig is None:
            self.report({"ERROR"}, "The current asset does not have exactly one base rig.")
            return {"CANCELLED"}
        _select_only(context, rig)
        return {"FINISHED"}


class ASSET_ASSISTANT_OT_pose_base_rig(bpy.types.Operator):
    bl_idname = "asset_assistant.pose_base_rig"
    bl_label = "Enter Pose Mode"
    bl_description = "Select the current Asset Assistant base armature and enter Pose Mode"

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and _base_rig(context) is not None

    def execute(self, context):
        rig = _base_rig(context)
        if rig is None:
            self.report({"ERROR"}, "The current asset does not have exactly one base rig.")
            return {"CANCELLED"}
        _select_only(context, rig)
        bpy.ops.object.mode_set(mode="POSE")
        self.report({"INFO"}, "Pose Mode active. Adjust bones, then use Return to Object Mode in Asset Assistant.")
        return {"FINISHED"}


class ASSET_ASSISTANT_OT_exit_pose_mode(bpy.types.Operator):
    bl_idname = "asset_assistant.exit_pose_mode"
    bl_label = "Return to Object Mode"
    bl_description = "Leave Pose Mode and return to normal Object Mode editing"

    @classmethod
    def poll(cls, context):
        return context.mode == "POSE" and _base_rig(context) is not None

    def execute(self, context):
        if context.mode != "POSE":
            return {"CANCELLED"}
        bpy.ops.object.mode_set(mode="OBJECT")
        self.report({"INFO"}, "Returned to Object Mode.")
        return {"FINISHED"}


def _draw_imported_rigging(panel, context, root):
    layout = panel.layout
    settings = context.scene.humanoid_settings
    layout.prop(settings, "target")
    rigs = asset_rigs(root)
    if not rigs:
        card = layout.box()
        card.label(text="NO BASE RIG FOUND", icon="INFO")
        card.label(text="This imported asset is currently static.")
        card.label(text="Asset Assistant will not replace imported geometry with a generated rig.")
        return
    if len(rigs) > 1:
        card = layout.box()
        card.label(text="MULTIPLE BASE RIGS FOUND", icon="ERROR")
        card.label(text="Choose or clean the intended armature before rig editing.")
        return

    rig = rigs[0]
    card = layout.box()
    card.label(text="IMPORTED BASE RIG", icon="ARMATURE_DATA")
    card.label(text=rig.name)
    card.label(text="Existing bones, weights and animation data are preserved.")

    if context.mode == "POSE":
        mode = card.box()
        mode.label(text="POSE MODE ACTIVE", icon="POSE_HLT")
        mode.label(text="The visible rig controls are now editable bones.")
        mode.label(text="Move, rotate or scale bones to adjust the pose.")
        exit_row = mode.row()
        exit_row.scale_y = 1.4
        exit_row.operator("asset_assistant.exit_pose_mode", text="Return to Object Mode", icon="OBJECT_DATA")
    else:
        actions = card.row(align=True)
        actions.scale_y = 1.25
        actions.operator("asset_assistant.select_base_rig", text="Select Rig", icon="RESTRICT_SELECT_OFF")
        actions.operator("asset_assistant.pose_base_rig", text="Enter Pose Mode", icon="POSE_HLT")

    help_box = layout.box()
    help_box.label(text="EDIT IN BLENDER", icon="INFO")
    if context.mode == "POSE":
        help_box.label(text="R rotates • G moves • S scales selected bones.")
        help_box.label(text="Use Return to Object Mode above when finished posing.")
    else:
        help_box.label(text="Enter Pose Mode to adjust the imported armature directly.")
        help_box.label(text="Asset Assistant keeps the artist-authored rig and weights intact.")


def install(ui):
    """Route imported assets around generated-provider-only Rig UI."""
    global _ORIGINAL_WORKFLOW_DRAW
    if _ORIGINAL_WORKFLOW_DRAW is not None:
        return
    _ORIGINAL_WORKFLOW_DRAW = ui._WorkflowPanel.draw

    def draw(panel, context):
        if getattr(panel, "stage", None) == "RIGGING":
            root = _target(context)
            if root is not None and is_external_asset(root):
                return _draw_imported_rigging(panel, context, root)
        return _ORIGINAL_WORKFLOW_DRAW(panel, context)

    ui._WorkflowPanel.draw = draw


_CLASSES = (
    ASSET_ASSISTANT_OT_select_base_rig,
    ASSET_ASSISTANT_OT_pose_base_rig,
    ASSET_ASSISTANT_OT_exit_pose_mode,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


__all__ = ["install", "register", "unregister"]
