# SPDX-License-Identifier: GPL-3.0-or-later
"""Non-destructive visual preview for imported LLM model-change requests."""

import json

import bpy

from .adapter import create_asset
from .core import plan_modification, request_from_json
from .modification import inspect_generated_asset

_PREVIEW_ROOT_KEY = "asset_assistant_model_preview_root"
_PREVIEW_SOURCE_KEY = "asset_assistant_model_preview_source"
_PREVIEW_HIDDEN_KEY = "asset_assistant_model_preview_hidden"
_PREVIEW_MARKER = "asset_assistant_model_preview"


def _walk(root):
    yield root
    for child in root.children_recursive:
        yield child


def _restore_source(scene):
    payload = scene.get(_PREVIEW_HIDDEN_KEY)
    if payload:
        try:
            states = json.loads(payload)
        except (TypeError, ValueError):
            states = []
        for row in states:
            obj = scene.objects.get(row.get("name", ""))
            if obj is None:
                continue
            obj.hide_viewport = bool(row.get("hide_viewport", False))
            try:
                obj.hide_set(bool(row.get("hide_set", False)))
            except RuntimeError:
                pass
    for key in (_PREVIEW_HIDDEN_KEY, _PREVIEW_SOURCE_KEY):
        if key in scene:
            del scene[key]


def clear_preview(scene):
    """Remove the temporary preview asset and restore the live source asset visibility."""
    preview_name = scene.get(_PREVIEW_ROOT_KEY)
    preview = bpy.data.objects.get(preview_name) if preview_name else None
    if preview is not None and preview.get(_PREVIEW_MARKER):
        collections = tuple(preview.users_collection)
        for obj in reversed(tuple(_walk(preview))):
            if obj != preview and obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        if preview.name in bpy.data.objects:
            bpy.data.objects.remove(preview, do_unlink=True)
        for collection in collections:
            if collection.users == 0:
                bpy.data.collections.remove(collection)
    if _PREVIEW_ROOT_KEY in scene:
        del scene[_PREVIEW_ROOT_KEY]
    _restore_source(scene)


def _hide_source(scene, root):
    states = []
    for obj in _walk(root):
        states.append({
            "name": obj.name,
            "hide_viewport": bool(obj.hide_viewport),
            "hide_set": bool(obj.hide_get()),
        })
        obj.hide_viewport = True
        obj.hide_set(True)
    scene[_PREVIEW_SOURCE_KEY] = root.name
    scene[_PREVIEW_HIDDEN_KEY] = json.dumps(states, sort_keys=True)


def _build_preview(context, root, request):
    snapshot = inspect_generated_asset(root)
    plan = plan_modification(snapshot, request)
    if plan.blockers:
        raise ValueError("Modify preview is blocked: " + "; ".join(plan.blockers))
    if not (plan.requested_parameter_changes or plan.requested_semantic_operations or plan.requested_animation_renames):
        raise ValueError("Imported request contains no changes to preview.")

    provider = context.scene.humanoid_settings and __import__(
        "blender_adapter.core_gateway", fromlist=["get_provider"]
    ).get_provider(snapshot.provider_key)
    values = snapshot.parameter_values()
    values.update(dict(plan.requested_parameter_changes))
    mesh = provider.mesh(values)
    semantic_operations = tuple(snapshot.semantic_operations) + tuple(plan.requested_semantic_operations)
    if semantic_operations:
        semantic_mesh = getattr(provider, "semantic_mesh", None)
        if not callable(semantic_mesh):
            raise ValueError("Provider cannot preview semantic geometry changes.")
        mesh = semantic_mesh(mesh, values, semantic_operations)

    materials = provider.materials(values) if snapshot.has_materials and getattr(provider, "supports_materials", False) else ()
    preview = create_asset(
        mesh,
        name=root.name + ".LLM Preview",
        scene=context.scene,
        materials=materials,
    )
    preview.matrix_world = root.matrix_world.copy()
    preview[_PREVIEW_MARKER] = True
    preview["object_type"] = snapshot.provider_key
    preview["asset_assistant_preview_source_asset_id"] = snapshot.asset_id
    for key, value in values.items():
        preview[key] = value
    return preview, plan


class ASSET_ASSISTANT_OT_model_preview_imported(bpy.types.Operator):
    bl_idname = "asset_assistant.model_preview_imported"
    bl_label = "Preview Model Changes"
    bl_description = "Build a temporary visual preview of the imported model changes without mutating the live asset"

    @classmethod
    def poll(cls, context):
        return (
            context.scene is not None
            and context.mode == "OBJECT"
            and bool(context.scene.get("asset_assistant_modify_imported_request"))
        )

    def execute(self, context):
        from . import modify_ui

        root = modify_ui._character(context)
        if root is None:
            self.report({"ERROR"}, "Choose a generated Asset Assistant asset first.")
            return {"CANCELLED"}
        clear_preview(context.scene)
        try:
            snapshot = inspect_generated_asset(root)
            request = request_from_json(context.scene[modify_ui._IMPORTED_REQUEST_KEY], snapshot)
            preview, plan = _build_preview(context, root, request)
            _hide_source(context.scene, root)
            context.scene[_PREVIEW_ROOT_KEY] = preview.name
        except (ValueError, TypeError, RuntimeError, AttributeError) as error:
            clear_preview(context.scene)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        lines = modify_ui._request_summary(plan)
        lines.append("Visual preview active. The live asset is hidden but unchanged.")
        if plan.requested_animation_renames:
            lines.append("Animation rename changes are metadata-only and are listed here but not visualized.")
        modify_ui._store_report(context.scene, "IMPORTED_PREVIEW", lines)
        self.report({"INFO"}, "Visual model preview created. The live asset remains unchanged.")
        return {"FINISHED"}


class ASSET_ASSISTANT_OT_model_cancel_preview(bpy.types.Operator):
    bl_idname = "asset_assistant.model_cancel_preview"
    bl_label = "Cancel Preview"
    bl_description = "Remove the temporary model preview and restore the live asset"

    @classmethod
    def poll(cls, context):
        return context.scene is not None and bool(context.scene.get(_PREVIEW_ROOT_KEY))

    def execute(self, context):
        from . import modify_ui

        clear_preview(context.scene)
        modify_ui._store_report(context.scene, "IMPORTED_READY", ["Visual preview closed. Imported model changes are still loaded."])
        self.report({"INFO"}, "Preview closed; live asset restored.")
        return {"FINISHED"}


class ASSET_ASSISTANT_OT_model_apply_previewed(bpy.types.Operator):
    bl_idname = "asset_assistant.model_apply_previewed"
    bl_label = "Apply Model Changes"
    bl_description = "Commit the imported request after visual preview, re-checking ownership and validation first"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.scene is not None
            and context.mode == "OBJECT"
            and bool(context.scene.get(_PREVIEW_ROOT_KEY))
            and bool(context.scene.get("asset_assistant_modify_imported_request"))
        )

    def execute(self, context):
        clear_preview(context.scene)
        result = bpy.ops.asset_assistant.modify_apply_imported()
        if "FINISHED" not in result:
            self.report({"ERROR"}, "Model changes could not be applied; the live asset was restored.")
            return {"CANCELLED"}
        self.report({"INFO"}, "Previewed model changes applied.")
        return {"FINISHED"}


_CLASSES = (
    ASSET_ASSISTANT_OT_model_preview_imported,
    ASSET_ASSISTANT_OT_model_cancel_preview,
    ASSET_ASSISTANT_OT_model_apply_previewed,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    scene = getattr(bpy.context, "scene", None)
    if scene is not None:
        clear_preview(scene)
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


__all__ = ["clear_preview", "register", "unregister"]
