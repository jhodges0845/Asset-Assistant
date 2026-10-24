# SPDX-License-Identifier: GPL-3.0-or-later
"""Preflight and import existing asset files without silently claiming ownership."""

from pathlib import Path
from uuid import uuid4

import bpy


_FILEPATH_KEY = "asset_assistant_file_preflight_path"
_STATUS_KEY = "asset_assistant_file_preflight_status"
_SUMMARY_KEY = "asset_assistant_file_preflight_summary"
_CANDIDATE_KEY = "asset_assistant_file_preflight_candidate"
_CANDIDATES_KEY = "asset_assistant_file_preflight_candidates"
_CURRENT_IMPORT_GROUP_KEY = "asset_assistant_current_import_group"
_IMPORT_GROUP_KEY = "asset_assistant_import_group"
_IMPORT_ROOT_KEY = "asset_assistant_import_root"
_IMPORT_SOURCE_KEY = "asset_assistant_import_source"

_SUPPORTED_EXTENSIONS = {".blend", ".glb", ".gltf", ".fbx"}
_FILTER_GLOB = "*.blend;*.glb;*.gltf;*.fbx"
_CANDIDATE_SEPARATOR = "\n"
_PREFLIGHT_KEYS = (
    _FILEPATH_KEY,
    _STATUS_KEY,
    _SUMMARY_KEY,
    _CANDIDATE_KEY,
    _CANDIDATES_KEY,
)


def _blend_preflight(filepath):
    with bpy.data.libraries.load(filepath, link=False) as (data_from, _data_to):
        collections = tuple(name for name in data_from.collections if name)
        scenes = tuple(name for name in data_from.scenes if name)
        objects = tuple(name for name in data_from.objects if name)
        meshes = tuple(name for name in data_from.meshes if name)
        armatures = tuple(name for name in data_from.armatures if name)
        actions = tuple(name for name in data_from.actions if name)
        cameras = tuple(name for name in data_from.cameras if name)
        lights = tuple(name for name in data_from.lights if name)

    project_signals = len(scenes) > 1 or bool(cameras) or bool(lights)
    if len(collections) == 1 and not project_signals:
        status = "ASSET_CANDIDATE"
        candidate = collections[0]
        headline = "One reusable collection candidate found."
    elif len(collections) > 1:
        status = "MULTIPLE_CANDIDATES"
        candidate = ""
        headline = f"{len(collections)} collection candidates found; choose the asset you want."
    elif meshes or armatures:
        status = "ASSET_CANDIDATE"
        candidate = ""
        headline = "Reusable object data found without a collection wrapper."
    else:
        status = "PROJECT_LIKELY" if project_signals else "NO_ASSET_FOUND"
        candidate = ""
        headline = "No clear reusable asset candidate was found."

    notes = [
        headline,
        f"{len(objects)} objects  •  {len(meshes)} meshes  •  {len(armatures)} rigs  •  {len(actions)} actions",
    ]
    if collections:
        preview = ", ".join(collections[:4])
        if len(collections) > 4:
            preview += ", …"
        notes.append("Collections: " + preview)
    if project_signals:
        notes.append("Scene/camera/light content suggests this file also contains project-level content.")
    notes.append("Nothing has been appended to the current Blender scene yet.")
    return {"status": status, "candidate": candidate, "candidates": collections, "notes": tuple(notes)}


def preflight_asset_file(filepath):
    path = Path(filepath)
    if not path.exists():
        raise ValueError("Asset file does not exist: " + str(path))
    extension = path.suffix.lower()
    if extension not in _SUPPORTED_EXTENSIONS:
        raise ValueError("Supported asset files are .blend, .glb, .gltf, and .fbx.")
    if extension == ".blend":
        report = _blend_preflight(str(path))
    else:
        report = {
            "status": "EXTERNAL_ASSET", "candidate": path.stem, "candidates": (),
            "notes": (
                extension[1:].upper() + " exchange asset detected.",
                "Mesh, rig, material, and animation structure will be inspected after import.",
                "Import does not add Asset Assistant ownership metadata.",
            ),
        }
    report["filepath"] = str(path)
    report["extension"] = extension
    return report


def _store_report(scene, report):
    scene[_FILEPATH_KEY] = report["filepath"]
    scene[_STATUS_KEY] = report["status"]
    scene[_CANDIDATE_KEY] = report.get("candidate", "")
    scene[_CANDIDATES_KEY] = _CANDIDATE_SEPARATOR.join(report.get("candidates", ()))
    scene[_SUMMARY_KEY] = "\n".join(report["notes"])


def clear_file_preflight_state(scene):
    """Clear transaction-only file inspection state after an import completes."""
    for key in _PREFLIGHT_KEYS:
        if key in scene:
            del scene[key]


def _stored_candidates(scene):
    raw = str(scene.get(_CANDIDATES_KEY, ""))
    return tuple(name for name in raw.split(_CANDIDATE_SEPARATOR) if name)


def _clear_selection(context):
    for obj in tuple(context.selected_objects):
        obj.select_set(False)


def _choose_import_root(objects):
    roots = [obj for obj in objects if getattr(obj, "parent", None) not in objects]
    candidates = roots or list(objects)
    if not candidates:
        return None
    armatures = [obj for obj in candidates if getattr(obj, "type", None) == "ARMATURE"]
    meshes = [obj for obj in candidates if getattr(obj, "type", None) == "MESH"]
    return armatures[0] if len(armatures) == 1 else (meshes[0] if meshes else candidates[0])


def _mark_import_boundary(objects, source):
    """Record a non-owning boundary for one imported file."""
    group = uuid4().hex
    root = _choose_import_root(objects)
    for obj in objects:
        obj[_IMPORT_GROUP_KEY] = group
        obj[_IMPORT_SOURCE_KEY] = source
        if obj == root:
            obj[_IMPORT_ROOT_KEY] = True
    return root


def _import_group(obj):
    if obj is None:
        return ""
    return str(obj.get(_IMPORT_GROUP_KEY, ""))


def _activate_imported_object(context, objects, source=""):
    active = _mark_import_boundary(objects, source) if source else _choose_import_root(objects)
    if active is None:
        return None
    _clear_selection(context)
    active.select_set(True)
    context.view_layer.objects.active = active
    return active


def _remove_import_group(group):
    """Remove only objects belonging to one prior imported-file boundary."""
    if not group:
        return 0
    objects = [obj for obj in tuple(bpy.data.objects) if _import_group(obj) == group]
    if not objects:
        return 0
    collections = {
        collection
        for obj in objects
        for collection in tuple(getattr(obj, "users_collection", ()))
    }
    data_blocks = [
        (getattr(obj, "type", None), getattr(obj, "data", None))
        for obj in objects
        if getattr(obj, "data", None) is not None
    ]
    for obj in reversed(objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for object_type, data in data_blocks:
        if data is None or getattr(data, "users", 0):
            continue
        if object_type == "MESH" and data.name in bpy.data.meshes:
            bpy.data.meshes.remove(data)
        elif object_type == "ARMATURE" and data.name in bpy.data.armatures:
            bpy.data.armatures.remove(data)
    for collection in collections:
        if collection.name in bpy.data.collections and not collection.objects and not collection.children:
            bpy.data.collections.remove(collection)
    return len(objects)


def _previous_import_group(scene, context):
    remembered = str(scene.get(_CURRENT_IMPORT_GROUP_KEY, ""))
    if remembered:
        return remembered
    settings = getattr(scene, "humanoid_settings", None)
    target = getattr(settings, "target", None) if settings is not None else None
    return _import_group(target)


def _finalize_import_replacement(scene, active, previous_group, remove_group=_remove_import_group):
    """Commit a successful import, replacing only the previous imported boundary."""
    new_group = _import_group(active)
    if not new_group:
        raise ValueError("Imported asset is missing its stable import boundary.")
    if previous_group and previous_group != new_group:
        remove_group(previous_group)
    scene[_CURRENT_IMPORT_GROUP_KEY] = new_group
    clear_file_preflight_state(scene)
    return new_group


# Datablocks created by supported exchange importers, removed only on failure.
_IMPORT_DATA_KINDS = (
    "scenes", "objects", "collections", "meshes", "armatures", "materials",
    "textures", "images", "actions", "cameras", "lights", "node_groups",
)


def _import_external(filepath, extension, context):
    before = {kind: set(getattr(bpy.data, kind)) for kind in _IMPORT_DATA_KINDS}
    scene = context.window.scene
    view_layer = context.window.view_layer
    selected = tuple(context.selected_objects)
    active = view_layer.objects.active
    try:
        if extension in {".glb", ".gltf"}:
            result = bpy.ops.import_scene.gltf(filepath=filepath)
        elif extension == ".fbx":
            if hasattr(bpy.ops.wm, "fbx_import"):
                result = bpy.ops.wm.fbx_import(filepath=filepath)
            else:
                result = bpy.ops.import_scene.fbx(filepath=filepath)
        else:
            raise ValueError("Unsupported external asset format: " + extension)
        if "FINISHED" not in result:
            raise RuntimeError("Blender did not finish importing the selected asset.")
        imported = tuple(obj for obj in bpy.data.objects if obj not in before["objects"])
        if not imported:
            raise RuntimeError("The file imported without creating any Blender objects.")
        context.window.scene = scene
        context.window.view_layer = view_layer
        if any(obj.name not in view_layer.objects for obj in imported):
            raise ValueError(
                "This file contains objects outside the current scene/view layer. "
                "Export one scene as a separate asset and import it again. "
                "The attempted import has been removed."
            )
        return _activate_imported_object(context, imported, source=extension[1:].upper())
    except Exception:
        context.window.scene = scene
        context.window.view_layer = view_layer
        created = [item for kind in _IMPORT_DATA_KINDS
                   for item in getattr(bpy.data, kind) if item not in before[kind]]
        if created:
            bpy.data.batch_remove(ids=created)
        _clear_selection(context)
        for obj in selected:
            obj.select_set(True)
        view_layer.objects.active = active
        raise


def _import_blend_collection(filepath, collection_name, context):
    if not collection_name:
        raise ValueError("Choose a .blend collection asset candidate first.")
    with bpy.data.libraries.load(filepath, link=False) as (_data_from, data_to):
        data_to.collections = [collection_name]
    collection = data_to.collections[0] if data_to.collections else None
    if collection is None:
        raise RuntimeError("Blender could not append the selected collection.")
    context.scene.collection.children.link(collection)
    objects = tuple(collection.all_objects)
    if not objects:
        raise RuntimeError("The selected collection does not contain any Blender objects.")
    return _activate_imported_object(context, objects, source="BLEND")


def choose_blend_candidate(scene, collection_name):
    candidates = _stored_candidates(scene)
    if collection_name not in candidates:
        raise ValueError("Choose one of the inspected collection candidates.")
    scene[_CANDIDATE_KEY] = collection_name
    scene[_STATUS_KEY] = "ASSET_CANDIDATE"
    summary = str(scene.get(_SUMMARY_KEY, "")).rstrip()
    selected_line = "Selected collection: " + collection_name
    scene[_SUMMARY_KEY] = summary + ("\n" if summary else "") + selected_line
    return collection_name


def import_preflight_asset(scene, context):
    filepath = str(scene.get(_FILEPATH_KEY, ""))
    status = str(scene.get(_STATUS_KEY, ""))
    candidate = str(scene.get(_CANDIDATE_KEY, ""))
    if not filepath or not status:
        raise ValueError("Inspect an asset file first.")
    extension = Path(filepath).suffix.lower()
    if extension == ".blend":
        if status != "ASSET_CANDIDATE" or not candidate:
            raise ValueError("Choose a specific collection asset before importing.")
        candidates = _stored_candidates(scene)
        if candidates and candidate not in candidates:
            raise ValueError("The selected collection is no longer part of this file preflight.")
        return _import_blend_collection(filepath, candidate, context)
    if status != "EXTERNAL_ASSET":
        raise ValueError("This file is not ready to import as an asset.")
    return _import_external(filepath, extension, context)


def _sync_imported_asset_context(context, inspection):
    settings = getattr(getattr(context, "scene", None), "humanoid_settings", None)
    if settings is None:
        return None
    root = inspection.get("root") if inspection else None
    target = root if inspection and inspection.get("status") == "READY" else None
    try:
        settings.target = target
    except (TypeError, ValueError, AttributeError):
        try:
            settings.target = None
        except (TypeError, ValueError, AttributeError):
            return None
        return None
    return target


def draw_file_preflight_report(layout, scene):
    status = scene.get(_STATUS_KEY)
    if not status:
        return
    labels = {
        "ASSET_CANDIDATE": ("ASSET CANDIDATE", "CHECKMARK"),
        "EXTERNAL_ASSET": ("EXTERNAL ASSET", "CHECKMARK"),
        "MULTIPLE_CANDIDATES": ("MULTIPLE ASSETS FOUND", "INFO"),
        "PROJECT_LIKELY": ("LIKELY BLENDER PROJECT", "INFO"),
        "NO_ASSET_FOUND": ("NO CLEAR ASSET FOUND", "ERROR"),
    }
    title, icon = labels.get(status, ("FILE INSPECTION", "INFO"))
    box = layout.box()
    box.label(text=title, icon=icon)
    filepath = scene.get(_FILEPATH_KEY, "")
    if filepath:
        box.label(text=Path(filepath).name)
    for line in str(scene.get(_SUMMARY_KEY, "")).splitlines():
        box.label(text=line)
    candidates = _stored_candidates(scene)
    if status == "MULTIPLE_CANDIDATES" and candidates:
        box.separator(factor=0.35)
        box.label(text="CHOOSE AN ASSET", icon="OUTLINER_COLLECTION")
        for name in candidates:
            row = box.row(); row.scale_y = 1.1
            op = row.operator("asset_assistant.choose_blend_asset_candidate", text=name, icon="OUTLINER_COLLECTION")
            op.collection_name = name
        box.label(text="Selecting a collection does not import it yet.")
        return
    candidate = str(scene.get(_CANDIDATE_KEY, ""))
    can_import = status in {"ASSET_CANDIDATE", "EXTERNAL_ASSET"} and (status == "EXTERNAL_ASSET" or bool(candidate))
    row = box.row(); row.scale_y = 1.25; row.enabled = can_import
    row.operator("asset_assistant.import_preflight_asset", text="Import This Asset", icon="IMPORT")
    if not can_import:
        box.label(text="Choose a specific asset candidate before importing.")


class ASSET_ASSISTANT_OT_preflight_asset_file(bpy.types.Operator):
    bl_idname = "asset_assistant.preflight_asset_file"
    bl_label = "Inspect Asset File"
    bl_description = "Inspect a .blend, GLB, glTF, or FBX file before bringing it into this scene"
    filepath: bpy.props.StringProperty(name="File Path", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default=_FILTER_GLOB, options={"HIDDEN"}, maxlen=255)

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            report = preflight_asset_file(self.filepath)
        except (ValueError, RuntimeError, OSError) as error:
            self.report({"ERROR"}, str(error)); return {"CANCELLED"}
        _store_report(context.scene, report)
        self.report({"INFO"}, "File inspected. Nothing was imported yet.")
        return {"FINISHED"}


class ASSET_ASSISTANT_OT_choose_blend_asset_candidate(bpy.types.Operator):
    bl_idname = "asset_assistant.choose_blend_asset_candidate"
    bl_label = "Choose Blend Asset"
    bl_description = "Choose this collection as the asset to import; nothing is imported yet"
    collection_name: bpy.props.StringProperty(name="Collection")

    def execute(self, context):
        try:
            choose_blend_candidate(context.scene, self.collection_name)
        except ValueError as error:
            self.report({"ERROR"}, str(error)); return {"CANCELLED"}
        self.report({"INFO"}, "Asset candidate selected. Import when ready.")
        return {"FINISHED"}


class ASSET_ASSISTANT_OT_import_preflight_asset(bpy.types.Operator):
    bl_idname = "asset_assistant.import_preflight_asset"
    bl_label = "Import This Asset"
    bl_description = "Import the inspected candidate without adding Asset Assistant ownership metadata"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.mode == "OBJECT"

    def execute(self, context):
        previous_group = _previous_import_group(context.scene, context)
        active = None
        try:
            active = import_preflight_asset(context.scene, context)
            if active is None:
                raise RuntimeError("The import finished without selecting an imported asset root.")
            from .asset_inspection_ui import inspect_selected_asset, store_inspection_report
            inspection = inspect_selected_asset(active)
            store_inspection_report(context.scene, inspection)
            _finalize_import_replacement(context.scene, active, previous_group)
            _sync_imported_asset_context(context, inspection)
        except (ValueError, RuntimeError, OSError, AttributeError, TypeError) as error:
            if active is not None:
                new_group = _import_group(active)
                if new_group and new_group != previous_group:
                    _remove_import_group(new_group)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Asset imported. Inspect and enroll it when ready.")
        return {"FINISHED"}


_CLASSES = (
    ASSET_ASSISTANT_OT_preflight_asset_file,
    ASSET_ASSISTANT_OT_choose_blend_asset_candidate,
    ASSET_ASSISTANT_OT_import_preflight_asset,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


__all__ = [
    "preflight_asset_file",
    "choose_blend_candidate",
    "import_preflight_asset",
    "clear_file_preflight_state",
    "draw_file_preflight_report",
    "register",
    "unregister",
]
