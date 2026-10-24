# SPDX-License-Identifier: GPL-3.0-or-later
"""Inspect, preview, and safely retune Asset Assistant-generated animations."""

import json
from math import isfinite

from .animation import (
    add_flight,
    add_idle,
    add_locomotion,
    add_run,
    generated_actions,
    validate_clip_destination,
)
from .animation_records import animation_record, has_animation_record, inspect_animation_record, persist_animation_record
from .core import AnimationRecord, AnimationSource
from .modification import inspect_generated_asset
from .workflow import provider_for


INSPECTION_SCHEMA = "asset-assistant.animation-inspection/v1"
REQUEST_SCHEMA = "asset-assistant.animation-request/v1"
_GENERATED_CLIP = "asset_assistant_clip"
_EXPORT_NAME = "asset_assistant_export_name"
_STRENGTH = "asset_assistant_animation_strength"


def _duration(record):
    return (float(record.frame_end) - float(record.frame_start)) / float(record.fps)


def _supported(record, provider):
    return (
        record.source == AnimationSource.GENERATED
        and record.owns_curves
        and record.provider_key == provider.key
        and isinstance(record.capability, str)
        and callable(getattr(provider, record.capability, None))
    )


def animation_inspection_document(root):
    """Return a dedicated animation inspection document for external refinement."""
    snapshot = inspect_generated_asset(root)
    provider = provider_for(root)
    animations = []
    for action in generated_actions(root):
        clip_id = str(action.get(_GENERATED_CLIP) or action.name)
        if not has_animation_record(action):
            animations.append({
                "clip_id": clip_id,
                "export_name": str(action.get(_EXPORT_NAME) or clip_id),
                "first_class": False,
                "tunable": False,
                "reason": "Legacy generated Action has no first-class animation record.",
            })
            continue
        record = inspect_animation_record(root, action)
        strength = action.get(_STRENGTH)
        animations.append({
            "animation_id": record.animation_id,
            "clip_id": clip_id,
            "display_name": record.display_name,
            "export_name": record.export_name,
            "source": record.source.value,
            "provider_key": record.provider_key,
            "capability": record.capability,
            "frame_start": float(record.frame_start),
            "frame_end": float(record.frame_end),
            "fps": float(record.fps),
            "duration_seconds": _duration(record),
            "strength": float(strength) if isinstance(strength, (int, float)) else None,
            "looping": record.looping,
            "root_motion": record.root_motion.value,
            "owns_curves": record.owns_curves,
            "first_class": True,
            "tunable": _supported(record, provider),
            "supported_changes": ["duration_seconds", "strength", "export_name"] if _supported(record, provider) else [],
        })
    return {
        "schema": INSPECTION_SCHEMA,
        "asset": {
            "asset_id": snapshot.asset_id,
            "provider_key": snapshot.provider_key,
            "provider_label": snapshot.provider_label,
        },
        "animations": sorted(animations, key=lambda item: item.get("clip_id", "")),
        "request_template": {
            "schema": REQUEST_SCHEMA,
            "asset_id": snapshot.asset_id,
            "provider_key": snapshot.provider_key,
            "operations": [
                {
                    "animation_id": "copy from one tunable animation above",
                    "duration_seconds": "optional positive number",
                    "strength": "optional number from 0.1 to 2.0",
                    "export_name": "optional nonempty string",
                }
            ],
            "notes": "Initial animation Modify supports one generated clip per request. Omit fields that should be preserved.",
        },
    }


def animation_inspection_json(root):
    return json.dumps(animation_inspection_document(root), indent=2, sort_keys=True) + "\n"


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(label + " must be a finite number")
    return float(value)


def _action_for_id(root, animation_id):
    for action in generated_actions(root):
        if not has_animation_record(action):
            continue
        record = animation_record(action)
        if record.animation_id == animation_id:
            return action, inspect_animation_record(root, action)
    return None, None


def preview_animation_request(root, document):
    """Validate one returned animation request without mutating Blender data."""
    if not isinstance(document, dict):
        raise TypeError("Animation request must contain a JSON object")
    if document.get("schema") != REQUEST_SCHEMA:
        raise ValueError("Unsupported animation request schema")
    snapshot = inspect_generated_asset(root)
    if document.get("asset_id") != snapshot.asset_id:
        raise ValueError("Animation request targets a different Asset Assistant asset")
    if document.get("provider_key") != snapshot.provider_key:
        raise ValueError("Animation request provider does not match the selected asset")
    operations = document.get("operations", [])
    if not isinstance(operations, list):
        raise TypeError("operations must be a JSON array")
    if len(operations) != 1:
        raise ValueError("Initial animation Modify supports exactly one animation operation per request")
    raw = operations[0]
    if not isinstance(raw, dict):
        raise TypeError("animation operation must be a JSON object")
    allowed = {"animation_id", "duration_seconds", "strength", "export_name"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError("Unknown animation change fields: " + ", ".join(sorted(unknown)))
    animation_id = raw.get("animation_id")
    if not isinstance(animation_id, str) or not animation_id.strip():
        raise ValueError("animation_id must be a nonempty string")
    action, record = _action_for_id(root, animation_id.strip())
    if action is None:
        raise ValueError("Requested generated animation was not found")
    provider = provider_for(root)
    if not _supported(record, provider):
        raise ValueError("Animation is not a reproducible Asset Assistant-generated clip")

    current_duration = _duration(record)
    duration = current_duration
    if "duration_seconds" in raw:
        duration = _finite(raw["duration_seconds"], "duration_seconds")
        if duration < 0.2 or duration > 20.0:
            raise ValueError("duration_seconds must be between 0.2 and 20.0")

    current_strength = action.get(_STRENGTH)
    if "strength" in raw:
        strength = _finite(raw["strength"], "strength")
        if strength < 0.1 or strength > 2.0:
            raise ValueError("strength must be between 0.1 and 2.0")
    else:
        if not isinstance(current_strength, (int, float)):
            raise ValueError("This legacy generated clip has no saved motion strength; include strength explicitly")
        strength = float(current_strength)

    export_name = record.export_name
    if "export_name" in raw:
        if not isinstance(raw["export_name"], str) or not raw["export_name"].strip():
            raise ValueError("export_name must be a nonempty string")
        export_name = raw["export_name"].strip()
        for other in generated_actions(root):
            if other == action:
                continue
            other_name = str(other.get(_EXPORT_NAME) or other.get(_GENERATED_CLIP) or other.name).strip()
            if other_name == export_name:
                raise ValueError("Animation export names must remain unique")

    if duration != current_duration or not isinstance(current_strength, (int, float)) or strength != float(current_strength):
        validate_clip_destination(root)

    return {
        "animation_id": record.animation_id,
        "clip_id": str(action.get(_GENERATED_CLIP) or action.name),
        "capability": record.capability,
        "provider_key": record.provider_key,
        "duration_seconds": duration,
        "strength": strength,
        "export_name": export_name,
        "changes": {
            "duration_seconds": duration != current_duration,
            "strength": not isinstance(current_strength, (int, float)) or strength != float(current_strength),
            "export_name": export_name != record.export_name,
        },
    }


def preview_animation_json(root, payload):
    try:
        document = json.loads(payload)
    except (TypeError, ValueError) as error:
        raise ValueError("Animation request is not valid JSON: " + str(error)) from None
    return preview_animation_request(root, document)


def _generator_for(capability):
    functions = {
        "idle": add_idle,
        "locomotion": add_locomotion,
        "run": add_run,
        "flight": add_flight,
    }
    if capability not in functions:
        raise ValueError("Unsupported generated animation capability: " + str(capability))
    return functions[capability]


def _updated_record(old_record, new_record, export_name):
    return AnimationRecord(
        animation_id=old_record.animation_id,
        display_name=old_record.display_name,
        export_name=export_name,
        source=old_record.source,
        rig_signature=new_record.rig_signature,
        frame_start=new_record.frame_start,
        frame_end=new_record.frame_end,
        fps=new_record.fps,
        looping=new_record.looping,
        root_motion=new_record.root_motion,
        owns_curves=True,
        source_reference=old_record.source_reference,
        provider_key=old_record.provider_key,
        capability=old_record.capability,
    )


def apply_animation_request(root, scene, document):
    """Regenerate one owned clip transactionally while preserving stable identity and other Actions."""
    import bpy

    plan = preview_animation_request(root, document)
    old_action, old_record = _action_for_id(root, plan["animation_id"])
    if old_action is None:
        raise ValueError("Requested animation disappeared before apply")
    if not plan["changes"]["duration_seconds"] and not plan["changes"]["strength"]:
        # Metadata-only requests must not regenerate or replace edited curves.
        from .animation import set_clip_export_name
        if plan["changes"]["export_name"]:
            set_clip_export_name(root, plan["clip_id"], plan["export_name"])
        return inspect_animation_record(root, old_action)
    clip_id = plan["clip_id"]
    original_clip_marker = old_action.get(_GENERATED_CLIP)
    original_name = old_action.name
    rig = next(child for child in root.children if child.type == "ARMATURE")
    active_before = rig.animation_data.action if rig.animation_data is not None else None
    backup_marker = "__asset_assistant_tuning_backup__" + old_record.animation_id
    old_action[_GENERATED_CLIP] = backup_marker
    new_action = None
    try:
        generator = _generator_for(plan["capability"])
        new_action, _ = generator(root, scene, plan["duration_seconds"], plan["strength"])
        generated_record = inspect_animation_record(root, new_action)
        persist_animation_record(new_action, _updated_record(old_record, generated_record, plan["export_name"]))
        new_action[_EXPORT_NAME] = plan["export_name"]
        new_action[_STRENGTH] = plan["strength"]
        new_action[_GENERATED_CLIP] = clip_id
        inspect_animation_record(root, new_action)

        if active_before is not old_action and rig.animation_data is not None:
            rig.animation_data.action = active_before
        bpy.data.actions.remove(old_action)
        new_action.name = original_name
        return inspect_animation_record(root, new_action)
    except Exception:
        if new_action is not None and new_action.name in bpy.data.actions:
            bpy.data.actions.remove(new_action)
        if old_action.name in bpy.data.actions:
            old_action[_GENERATED_CLIP] = original_clip_marker
            if rig.animation_data is not None:
                rig.animation_data.action = active_before
        raise


def apply_animation_json(root, scene, payload):
    try:
        document = json.loads(payload)
    except (TypeError, ValueError) as error:
        raise ValueError("Animation request is not valid JSON: " + str(error)) from None
    return apply_animation_request(root, scene, document)


__all__ = [
    "INSPECTION_SCHEMA",
    "REQUEST_SCHEMA",
    "animation_inspection_document",
    "animation_inspection_json",
    "preview_animation_request",
    "preview_animation_json",
    "apply_animation_request",
    "apply_animation_json",
]
