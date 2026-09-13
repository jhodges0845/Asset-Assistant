# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn explicit file imports into first-class Asset Assistant working assets.

Import-group metadata remains useful for transaction/replacement provenance, but it
is not the user-facing runtime model. A file explicitly imported through Asset
Assistant gets one canonical Blender collection/root, one current target, stable rig
identity, and imported animation records so downstream workspaces do not need to
understand importer-specific hierarchies.
"""

from uuid import uuid4

import bpy

from .animation_lifecycle import register_animation_action
from .animation_records import has_animation_record
from .asset_structure import asset_rigs
from .core import AnimationSource, RootMotionIntent


_ASSET_ID_KEY = "asset_assistant_asset_id"
_EXTERNAL_ASSET_KEY = "asset_assistant_external_asset"
_EXTERNAL_CAPABILITY_KEY = "asset_assistant_external_capability"
_RIG_ID_KEY = "asset_assistant_rig_id"

_ORIGINAL_EXECUTE = None


def _asset_collection_name(root):
    name = str(getattr(root, "name", "") or "Imported Asset").strip()
    return name or "Imported Asset"


def _remove_empty_import_collections(collections):
    """Remove importer-created collection shells only after their objects moved out."""
    pending = set(collections)
    changed = True
    while changed:
        changed = False
        for collection in tuple(pending):
            if collection not in bpy.data.collections.values():
                pending.discard(collection)
                continue
            if len(collection.objects) or len(collection.children):
                continue
            bpy.data.collections.remove(collection)
            pending.discard(collection)
            changed = True


def _organize_import_collection(root, objects):
    """Put one imported working asset in one Blender collection without changing parenting."""
    scene = bpy.context.scene
    collection = bpy.data.collections.new(_asset_collection_name(root))
    scene.collection.children.link(collection)

    imported_objects = (root,) + tuple(objects)
    previous_collections = set()
    for obj in imported_objects:
        current = tuple(getattr(obj, "users_collection", ()))
        previous_collections.update(current)
        if collection not in current:
            collection.objects.link(obj)
        for old in current:
            if old is collection:
                continue
            old.objects.unlink(obj)

    previous_collections.discard(collection)
    _remove_empty_import_collections(previous_collections)
    return collection


def normalized_import_root(objects, source, import_ui):
    """Create one canonical Blender root/collection without disturbing internal relations."""
    objects = tuple(objects)
    if not objects:
        return None

    group = uuid4().hex
    root = bpy.data.objects.new("Imported Asset", None)
    bpy.context.scene.collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root[import_ui._IMPORT_GROUP_KEY] = group
    root[import_ui._IMPORT_SOURCE_KEY] = source
    root[import_ui._IMPORT_ROOT_KEY] = True

    members = set(objects)
    top_level = tuple(obj for obj in objects if getattr(obj, "parent", None) not in members)
    for obj in objects:
        obj[import_ui._IMPORT_GROUP_KEY] = group
        obj[import_ui._IMPORT_SOURCE_KEY] = source
        if import_ui._IMPORT_ROOT_KEY in obj:
            del obj[import_ui._IMPORT_ROOT_KEY]

    # Reparent only importer-level roots. Existing armature/mesh parenting remains
    # untouched, and matrix_world is restored so the imported asset does not move.
    for obj in top_level:
        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world

    _organize_import_collection(root, objects)
    return root


def _rig_actions(rig):
    animation_data = getattr(rig, "animation_data", None)
    if animation_data is None:
        return ()
    result = []
    active = getattr(animation_data, "action", None)
    if active is not None:
        result.append(active)
    for track in tuple(getattr(animation_data, "nla_tracks", ())):
        for strip in tuple(getattr(track, "strips", ())):
            action = getattr(strip, "action", None)
            if action is not None and action not in result:
                result.append(action)
    return tuple(result)


def enroll_imported_working_asset(context, inspection):
    """Make an explicit file import immediately usable across Asset Assistant."""
    if not inspection:
        return None
    root = inspection.get("root")
    metrics = inspection.get("metrics") or {}
    if root is None or not metrics.get("meshes"):
        return None
    if int(metrics.get("armatures", 0)) > 1:
        raise ValueError("Imported working assets currently support at most one base armature.")

    root[_EXTERNAL_ASSET_KEY] = True
    root["asset_assistant_source"] = "IMPORTED"
    if not root.get(_ASSET_ID_KEY):
        root[_ASSET_ID_KEY] = uuid4().hex

    unit_settings = getattr(context.scene, "unit_settings", None)
    meters_per_unit = float(getattr(unit_settings, "scale_length", 1.0) or 1.0)
    if meters_per_unit <= 0:
        meters_per_unit = 1.0
    if not isinstance(root.get("coordinate_scale"), (int, float)) or root.get("coordinate_scale") <= 0:
        root["coordinate_scale"] = 0.01 / meters_per_unit

    rigs = asset_rigs(root)
    registered = 0
    if len(rigs) == 1:
        rig = rigs[0]
        if not str(rig.get(_RIG_ID_KEY) or "").strip():
            rig[_RIG_ID_KEY] = uuid4().hex
        fps = float(context.scene.render.fps) / max(float(context.scene.render.fps_base), 1e-9)
        source_reference = str(root.get("asset_assistant_import_source") or "import")
        for action in _rig_actions(rig):
            if has_animation_record(action) or action.get("asset_assistant_generated"):
                continue
            register_animation_action(
                root,
                action,
                source=AnimationSource.IMPORTED,
                display_name=action.name,
                export_name=action.name,
                fps=fps,
                looping=False,
                root_motion=RootMotionIntent.NONE,
                source_reference=source_reference,
            )
            registered += 1

    animation_count = max(int(metrics.get("animations", 0)), registered)
    capability = "ANIMATED" if animation_count else ("RIGGED" if rigs else "STATIC")
    root[_EXTERNAL_CAPABILITY_KEY] = capability

    settings = getattr(context.scene, "humanoid_settings", None)
    if settings is not None:
        settings.target = root
        settings.asset_use = capability
        settings.validation_results.clear()

    return root


def install(import_ui):
    """Install canonical import normalization before Blender registers operators."""
    global _ORIGINAL_EXECUTE

    def mark_import_boundary(objects, source):
        return normalized_import_root(objects, source, import_ui)

    import_ui._mark_import_boundary = mark_import_boundary

    if _ORIGINAL_EXECUTE is not None:
        return
    _ORIGINAL_EXECUTE = import_ui.ASSET_ASSISTANT_OT_import_preflight_asset.execute

    def execute(operator, context):
        previous_group = import_ui._previous_import_group(context.scene, context)
        active = None
        try:
            active = import_ui.import_preflight_asset(context.scene, context)
            if active is None:
                raise RuntimeError("The import finished without creating an Asset Assistant working asset.")
            from .asset_inspection_ui import clear_inspection_report, inspect_selected_asset

            inspection = inspect_selected_asset(active)
            if not inspection.get("can_adopt") and inspection.get("status") not in {"READY", "EXTERNAL_READY"}:
                raise ValueError("Imported file could not be normalized into a usable Asset Assistant asset.")
            root = enroll_imported_working_asset(context, inspection)
            if root is None:
                raise ValueError("Imported file does not contain usable mesh geometry.")
            import_ui._finalize_import_replacement(context.scene, root, previous_group)
            clear_inspection_report(context.scene)
            import_ui._clear_selection(context)
            root.select_set(True)
            context.view_layer.objects.active = root
        except (ValueError, RuntimeError, OSError, AttributeError, TypeError) as error:
            if active is not None:
                new_group = import_ui._import_group(active)
                if new_group and new_group != previous_group:
                    import_ui._remove_import_group(new_group)
            operator.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        operator.report({"INFO"}, "Imported file is ready as the current Asset Assistant working asset.")
        return {"FINISHED"}

    import_ui.ASSET_ASSISTANT_OT_import_preflight_asset.execute = execute
    import_ui.ASSET_ASSISTANT_OT_import_preflight_asset.bl_description = (
        "Import the inspected file and normalize it into the current editable Asset Assistant working asset"
    )


__all__ = ["enroll_imported_working_asset", "install", "normalized_import_root"]
