# SPDX-License-Identifier: GPL-3.0-or-later
"""Artist-facing adoption of existing Blender Actions into Asset Assistant."""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty

from .animation_lifecycle import register_animation_action
from .animation_records import has_animation_record
from .asset_structure import asset_rigs
from .core import AnimationSource, RootMotionIntent
from .workflow import find_character


def _character(context):
    settings = getattr(context.scene, "humanoid_settings", None) if context.scene else None
    root = settings.target if settings and settings.target else find_character(context.object)
    return root if root and context.scene.objects.get(root.name) == root else None


def unmanaged_actions():
    return tuple(action for action in bpy.data.actions
                 if not has_animation_record(action) and not action.get("asset_assistant_generated"))


def has_unmanaged_actions():
    return bool(unmanaged_actions())


def _candidate_actions(self, context):
    items = [(action.name, action.name, "Register this existing Blender Action without changing its curves")
             for action in unmanaged_actions()]
    return tuple(sorted(items, key=lambda item: item[0].lower())) or (("", "No unmanaged Actions", "Create or import an Action first"),)


class ASSET_ASSISTANT_OT_adopt_animation_action(bpy.types.Operator):
    bl_idname = "asset_assistant.adopt_animation_action"
    bl_label = "Use Existing Blender Action"
    bl_description = "Add an existing unmanaged Blender Action to this asset's clip library"
    bl_options = {"REGISTER", "UNDO"}

    action_name: EnumProperty(name="Action", items=_candidate_actions)
    source: EnumProperty(name="Source", items=(
        (AnimationSource.IMPORTED.value, "Imported", "Action arrived from an external asset/file"),
        (AnimationSource.ARTIST.value, "Artist Authored", "Action was authored or edited by the artist in Blender"),
    ), default=AnimationSource.IMPORTED.value)
    display_name: StringProperty(name="Display Name")
    export_name: StringProperty(name="Export Name")
    fps: FloatProperty(name="FPS", default=24.0, min=1.0, max=240.0)
    looping: BoolProperty(name="Looping", default=False)
    root_motion: EnumProperty(name="Root Motion", items=(
        (RootMotionIntent.NONE.value, "None", "No root-motion contract"),
        (RootMotionIntent.IN_PLACE.value, "In Place", "Locomotion remains in place"),
        (RootMotionIntent.ROOT.value, "Root", "Action intentionally carries root motion"),
    ), default=RootMotionIntent.NONE.value)
    source_reference: StringProperty(name="Source Reference", description="Optional filename, package, or artist reference")

    @classmethod
    def poll(cls, context):
        root = _character(context) if context.scene else None
        return context.mode == "OBJECT" and root is not None and len(asset_rigs(root)) == 1 and has_unmanaged_actions()

    def invoke(self, context, event):
        candidates = list(unmanaged_actions())
        if not candidates:
            self.report({"ERROR"}, "No unmanaged Blender Actions are available.")
            return {"CANCELLED"}
        action = candidates[0]
        self.action_name = action.name
        self.display_name = action.name
        self.export_name = action.name
        self.fps = float(context.scene.render.fps) / max(float(context.scene.render.fps_base), 1e-9)
        return context.window_manager.invoke_props_dialog(self, width=480)

    def execute(self, context):
        root = _character(context)
        action = bpy.data.actions.get(self.action_name)
        if root is None or action is None:
            self.report({"ERROR"}, "Choose a valid character and unmanaged Blender Action.")
            return {"CANCELLED"}
        try:
            record = register_animation_action(
                root,
                action,
                source=AnimationSource(self.source),
                display_name=self.display_name or action.name,
                export_name=self.export_name or action.name,
                fps=self.fps,
                looping=self.looping,
                root_motion=RootMotionIntent(self.root_motion),
                source_reference=self.source_reference.strip() or None,
            )
        except (TypeError, ValueError, RuntimeError, AttributeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        settings = getattr(context.scene, "humanoid_settings", None)
        if settings is not None:
            settings.validation_results.clear()
        self.report({"INFO"}, "Added existing Blender Action: " + record.export_name)
        return {"FINISHED"}


_CLASSES = (ASSET_ASSISTANT_OT_adopt_animation_action,)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


__all__ = [
    "ASSET_ASSISTANT_OT_adopt_animation_action",
    "has_unmanaged_actions",
    "unmanaged_actions",
    "register",
    "unregister",
]
