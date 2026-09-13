# SPDX-License-Identifier: GPL-3.0-or-later
"""Register and manage Blender Actions without silently claiming artist curves."""

from uuid import uuid4

from .asset_structure import asset_rigs
from .core import AnimationRecord, AnimationSource, RootMotionIntent
from .animation_records import (
    animation_record,
    clear_animation_record,
    has_animation_record,
    inspect_animation_record,
    persist_animation_record,
    rig_signature,
)

_EXPORT_NAME = "asset_assistant_export_name"
_RIG_ID = "asset_assistant_rig_id"


def _rig(root):
    rigs = asset_rigs(root)
    if len(rigs) != 1:
        raise ValueError("animation lifecycle requires exactly one Asset Assistant rig")
    return rigs[0]


def _source(value):
    try:
        source = value if isinstance(value, AnimationSource) else AnimationSource(value)
    except (TypeError, ValueError):
        raise ValueError("animation source must be imported or artist") from None
    if source == AnimationSource.GENERATED:
        raise ValueError("generated Actions must use the provider animation workflow")
    return source


def _root_motion(value):
    try:
        return value if isinstance(value, RootMotionIntent) else RootMotionIntent(value)
    except (TypeError, ValueError):
        raise ValueError("unknown root motion intent") from None


def _assigned_objects(action):
    import bpy
    return tuple(obj for obj in bpy.data.objects
                 if obj.animation_data is not None and obj.animation_data.action == action)


def _validate_candidate(root, action):
    if action is None:
        raise ValueError("choose a Blender Action first")
    if has_animation_record(action):
        raise ValueError("Action is already managed by Asset Assistant")
    if action.get("asset_assistant_generated"):
        raise ValueError("generated Actions already use the generated animation lifecycle")
    rig = _rig(root)
    assigned = _assigned_objects(action)
    if any(obj != rig for obj in assigned):
        raise ValueError("Action is assigned to another Blender object and will not be adopted")
    return rig


def _unique_export_name(root, export_name, *, ignored_action=None):
    export_name = str(export_name).strip()
    if not export_name:
        raise ValueError("animation export name cannot be empty")
    for action in managed_actions(root):
        if action == ignored_action:
            continue
        if str(action.get(_EXPORT_NAME) or "").strip() == export_name:
            raise ValueError("animation export names must be unique for this character")
    return export_name


def _record_for_action(root, action, *, animation_id, source, display_name, export_name, fps, looping,
                       root_motion, source_reference, ignored_action=None):
    rig = _rig(root)
    start, end = action.frame_range
    return AnimationRecord(
        animation_id=animation_id,
        display_name=str(display_name).strip(),
        export_name=_unique_export_name(root, export_name, ignored_action=ignored_action),
        source=_source(source),
        rig_signature=rig_signature(rig),
        frame_start=float(start), frame_end=float(end), fps=fps, looping=looping,
        root_motion=_root_motion(root_motion), owns_curves=False, source_reference=source_reference,
    )


def _rig_scope_id(root):
    rig = _rig(root)
    rig_id = str(rig.get(_RIG_ID) or "").strip()
    if not rig_id:
        raise ValueError("animation lifecycle requires a stable Asset Assistant rig id")
    return rig_id


def _persist_action_metadata(root, action, record):
    """Persist Asset Assistant metadata atomically without touching Action curves."""
    rig_id = _rig_scope_id(root)
    try:
        persist_animation_record(action, record)
        action[_RIG_ID] = rig_id
        action[_EXPORT_NAME] = record.export_name
    except Exception:
        clear_animation_record(action)
        if _EXPORT_NAME in action:
            del action[_EXPORT_NAME]
        if _RIG_ID in action:
            del action[_RIG_ID]
        raise


def register_animation_action(root, action, *, source=AnimationSource.ARTIST, display_name=None,
                              export_name=None, fps=24.0, looping=False,
                              root_motion=RootMotionIntent.NONE, source_reference=None):
    """Register an existing Action while preserving ownership of its curves."""
    _validate_candidate(root, action)
    display_name = str(display_name or action.name).strip()
    export_name = str(export_name or display_name).strip()
    record = _record_for_action(
        root, action, animation_id="animation-" + uuid4().hex, source=source,
        display_name=display_name, export_name=export_name, fps=fps, looping=looping,
        root_motion=root_motion, source_reference=source_reference,
    )
    _persist_action_metadata(root, action, record)
    return record


def managed_actions(root):
    """Return first-class Actions explicitly associated with this Asset Assistant rig."""
    import bpy
    rig = _rig(root)
    signature = rig_signature(rig)
    rig_id = str(rig.get(_RIG_ID) or "").strip()
    result = []
    for action in bpy.data.actions:
        if not has_animation_record(action):
            continue
        record = animation_record(action)
        if record.rig_signature != signature:
            continue
        action_rig_id = str(action.get(_RIG_ID) or "").strip()
        if rig_id:
            if action_rig_id != rig_id:
                continue
        elif action_rig_id:
            continue
        elif rig not in _assigned_objects(action):
            continue
        inspect_animation_record(root, action)
        result.append(action)
    return tuple(result)


def exportable_actions(root):
    """Return first-class Actions plus legacy generated Actions for later engine export staging."""
    from .animation import generated_actions
    managed = list(managed_actions(root))
    seen = {action.as_pointer() for action in managed}
    for action in generated_actions(root):
        if action.as_pointer() not in seen:
            managed.append(action)
    return tuple(managed)


def action_for_animation_id(root, animation_id):
    animation_id = str(animation_id).strip()
    if not animation_id:
        raise ValueError("animation_id cannot be empty")
    return next((action for action in managed_actions(root)
                 if animation_record(action).animation_id == animation_id), None)


def remove_animation(root, animation_id):
    """Delete one managed animation Action from the current Blender working file."""
    import bpy
    action = action_for_animation_id(root, animation_id)
    if action is None:
        raise ValueError("managed animation was not found")
    record = inspect_animation_record(root, action)
    rig = _rig(root)
    if rig.animation_data is not None and rig.animation_data.action == action:
        rig.animation_data.action = None
    bpy.data.actions.remove(action)
    return record


def replace_animation_action(root, animation_id, replacement, *, source=AnimationSource.ARTIST,
                             display_name=None, export_name=None, fps=24.0, looping=False,
                             root_motion=RootMotionIntent.NONE, source_reference=None):
    """Replace one managed clip while preserving its stable animation identity."""
    import bpy
    current = action_for_animation_id(root, animation_id)
    if current is None:
        raise ValueError("managed animation was not found")
    if replacement == current:
        raise ValueError("replacement Action must be different from the current Action")
    _validate_candidate(root, replacement)
    current_record = inspect_animation_record(root, current)
    display_name = str(display_name or replacement.name).strip()
    export_name = str(export_name or current_record.export_name).strip()
    record = _record_for_action(
        root, replacement, animation_id=current_record.animation_id, source=source,
        display_name=display_name, export_name=export_name, fps=fps, looping=looping,
        root_motion=root_motion, source_reference=source_reference, ignored_action=current,
    )
    _persist_action_metadata(root, replacement, record)
    rig = _rig(root)
    was_active = rig.animation_data is not None and rig.animation_data.action == current
    try:
        if was_active:
            rig.animation_data.action = replacement
        if current_record.owns_curves:
            bpy.data.actions.remove(current)
        else:
            clear_animation_record(current)
            if _EXPORT_NAME in current:
                del current[_EXPORT_NAME]
            if _RIG_ID in current:
                del current[_RIG_ID]
    except Exception:
        clear_animation_record(replacement)
        if _EXPORT_NAME in replacement:
            del replacement[_EXPORT_NAME]
        if _RIG_ID in replacement:
            del replacement[_RIG_ID]
        if was_active and current.name in bpy.data.actions:
            rig.animation_data.action = current
        raise
    return record


__all__ = [
    "action_for_animation_id", "exportable_actions", "managed_actions",
    "register_animation_action", "remove_animation", "replace_animation_action",
]
