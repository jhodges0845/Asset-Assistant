# SPDX-License-Identifier: GPL-3.0-or-later
"""Self-document Asset Assistant model inspection JSON for context-free LLM use."""

import copy

from .core import REQUEST_SCHEMA, get_provider

_REPOSITORY = "https://github.com/jhodges0845/blender-object-generator"
_DOC_PATH = "docs/model-json-roundtrip.md"

_HUMAN_SHAPE_PROFILES = {
    "body": (),
    "torso": ("athletic",),
    "shoulders": ("broad",),
    "head": ("oval",),
    "face": ("narrow", "defined"),
    "jaw": ("tapered", "strong"),
    "cheeks": ("high", "soft"),
    "arm.left": ("lean",),
    "arm.right": ("lean",),
    "leg.left": ("athletic",),
    "leg.right": ("athletic",),
}


def _version_text(version):
    return ".".join(str(part) for part in version)


def _parameter_contract(provider, current):
    result = []
    for field in getattr(provider, "parameters", ()):
        row = {
            "key": field.key,
            "label": field.label,
            "current": current.get(field.key, field.default),
            "default": field.default,
        }
        if getattr(field, "choices", ()):
            row["choices"] = [choice[0] for choice in field.choices]
        else:
            row["minimum"] = field.minimum
            row["maximum"] = field.maximum
        result.append(row)
    return result


def _number_argument(minimum=None, maximum=None, default=None, description=""):
    result = {"type": "number"}
    if minimum is not None:
        result["minimum"] = minimum
    if maximum is not None:
        result["maximum"] = maximum
    if default is not None:
        result["default"] = default
    if description:
        result["description"] = description
    return result


def _operation_contract(provider, target_key, operation):
    """Describe only argument forms the current provider implementation accepts."""
    if getattr(provider, "key", "") != "human_experimental":
        return {"operation": operation, "arguments": {}, "note": "Provider has not published a detailed argument schema yet."}

    scale_arguments = {
        "factor": _number_argument(0.1, 4.0, 1.0, "Uniform scale for the selected semantic region."),
        "x": _number_argument(0.1, 4.0, 1.0, "Region scale on model X (left/right width)."),
        "y": _number_argument(0.1, 4.0, 1.0, "Region scale on model Y (front/back depth)."),
        "z": _number_argument(0.1, 4.0, 1.0, "Region scale on model Z (vertical height/length)."),
        "offset_x": _number_argument(default=0.0, description="Optional X translation in model centimeters."),
        "offset_y": _number_argument(default=0.0, description="Optional Y translation in model centimeters."),
        "offset_z": _number_argument(default=0.0, description="Optional Z translation in model centimeters."),
    }
    if operation == "scale":
        return {
            "operation": "scale",
            "arguments": scale_arguments,
            "guidance": "Use small changes near 1.0 for artistic refinement; omitted axes inherit factor.",
        }
    if operation == "shape":
        profiles = list(_HUMAN_SHAPE_PROFILES.get(target_key, ()))
        arguments = dict(scale_arguments)
        if profiles:
            arguments["profile"] = {
                "type": "enum",
                "values": profiles,
                "description": "Provider-owned known-good shape profile for this exact target.",
            }
            arguments["amount"] = _number_argument(0.0, 1.5, 0.65, "Strength of the selected shape profile.")
        return {
            "operation": "shape",
            "arguments": arguments,
            "guidance": (
                "Shape may combine a supported profile with small scale/offset arguments. "
                "Do not invent profile names; omit profile when only direct scaling is desired."
            ),
        }
    return {"operation": operation, "arguments": {}}


def _semantic_targets_with_contract(provider, targets):
    enriched = []
    for target in targets:
        row = copy.deepcopy(target)
        row["operation_contracts"] = {
            operation: _operation_contract(provider, row.get("key"), operation)
            for operation in row.get("executable_operations") or []
        }
        enriched.append(row)
    return enriched


def _last_profile(operations, target):
    for operation in reversed(tuple(operations)):
        if operation.get("target") != target or operation.get("operation") != "shape":
            continue
        profile = (operation.get("arguments") or {}).get("profile")
        if profile:
            return profile
    return "neutral"


def _human_semantic_state(provider, parameters, operations):
    """Return compact provider-derived measurements rather than dumping raw mesh data."""
    try:
        proportions = provider.proportions(parameters)
    except (KeyError, ValueError, TypeError, AttributeError):
        return None

    shoulder = float(proportions.shoulder_width_cm)
    hip = float(proportions.hip_width_cm)
    waist = float(proportions.waist_width_cm)
    head_width = float(proportions.head_width_cm)
    head_height = float(proportions.head_height_cm)
    chest = float(proportions.chest_width_cm)
    return {
        "measurement_basis": "provider-derived current procedural proportions before viewport-only artist mesh edits",
        "units": "centimeters",
        "overall": {
            "height_cm": float(parameters.get("height_cm", 0.0)),
            "weight_kg": float(parameters.get("weight_kg", 0.0)),
            "body_type": parameters.get("body_type"),
            "shoulder_width_cm": shoulder,
            "chest_width_cm": chest,
            "waist_width_cm": waist,
            "hip_width_cm": hip,
            "head_width_cm": head_width,
            "head_height_cm": head_height,
        },
        "regions": {
            "shoulders": {
                "width_cm": shoulder,
                "shoulder_to_hip_ratio": round(shoulder / hip, 4) if hip else None,
                "shape_profile": _last_profile(operations, "shoulders"),
            },
            "torso": {
                "chest_width_cm": chest,
                "waist_width_cm": waist,
                "chest_to_waist_ratio": round(chest / waist, 4) if waist else None,
                "shape_profile": _last_profile(operations, "torso"),
            },
            "head": {
                "width_cm": head_width,
                "height_cm": head_height,
                "width_height_ratio": round(head_width / head_height, 4) if head_height else None,
                "shape_profile": _last_profile(operations, "head"),
            },
            "face": {"shape_profile": _last_profile(operations, "face")},
            "jaw": {"shape_profile": _last_profile(operations, "jaw")},
            "cheeks": {"shape_profile": _last_profile(operations, "cheeks")},
            "arm.left": {"shape_profile": _last_profile(operations, "arm.left")},
            "arm.right": {"shape_profile": _last_profile(operations, "arm.right")},
            "leg.left": {"shape_profile": _last_profile(operations, "leg.left")},
            "leg.right": {"shape_profile": _last_profile(operations, "leg.right")},
        },
        "important": (
            "Use these values to judge the current model and author deltas. They describe the procedural/semantic state, "
            "not unrestricted raw mesh geometry."
        ),
    }


def _model_state(provider, asset):
    if getattr(provider, "key", "") == "human_experimental":
        return _human_semantic_state(
            provider,
            asset.get("parameters") or {},
            asset.get("applied_semantic_operations") or [],
        )
    return {
        "measurement_basis": "provider parameters",
        "parameters": copy.deepcopy(asset.get("parameters") or {}),
        "important": "This provider has not published richer semantic measurements yet.",
    }


def _example_semantic_operation(asset):
    for target in asset.get("semantic_targets", ()):
        executable = target.get("executable_operations") or []
        if not executable:
            continue
        operation = executable[0]
        contract = (target.get("operation_contracts") or {}).get(operation) or {}
        arguments = contract.get("arguments") or {}
        example_args = {}
        if "profile" in arguments and arguments["profile"].get("values"):
            example_args["profile"] = arguments["profile"]["values"][0]
            if "amount" in arguments:
                example_args["amount"] = arguments["amount"].get("default", 0.65)
        elif operation in ("scale", "shape"):
            example_args["factor"] = 1.05
        return {"operation": operation, "target": target.get("key"), "arguments": example_args}
    return None


def enhance_inspection_document(document, addon_version=(0, 9, 0)):
    """Return an LLM-oriented copy of the portable Modify inspection document."""
    payload = copy.deepcopy(document)
    asset = payload.get("asset") or {}
    provider_key = str(asset.get("provider_key") or "")
    provider = get_provider(provider_key)
    request_template = payload.get("request_template") or {}

    enriched_targets = _semantic_targets_with_contract(provider, asset.get("semantic_targets") or [])
    asset["semantic_targets"] = enriched_targets
    payload["asset"] = asset
    example_semantic = _example_semantic_operation(asset)

    payload["asset_assistant"] = {
        "product": "Asset Assistant",
        "addon_version": _version_text(addon_version),
        "repository": _REPOSITORY,
        "documentation": _REPOSITORY + "/blob/main/" + _DOC_PATH,
        "return_schema": REQUEST_SCHEMA,
        "workflow": "Export Model Context JSON -> LLM authors Model Change JSON -> Import -> Preview -> Apply",
    }

    payload["model_authoring_contract"] = {
        "goal": "Describe safe, targeted changes to this exact Asset Assistant model without replacing artist work blindly.",
        "output": "Return one JSON object only using the exact request_template schema and asset/provider identity from this file.",
        "rules": [
            "Do not change asset_id or provider_key.",
            "Use only parameter keys listed in parameter_contract.",
            "Use only semantic targets, executable operations, arguments, enum values, and numeric ranges published in semantic_vocabulary.",
            "Do not invent semantic target names, profile names, component ids, animation ids, or unsupported operations.",
            "Read model_state before deciding how large a requested change should be.",
            "Omitted fields mean preserve the current model state.",
            "Prefer small, composable semantic operations over large destructive changes.",
            "Do not assume raw Blender vertex editing is available through this JSON contract.",
            "Preserve rig, weights, materials, animations, components, and artist-owned data unless the exported contract explicitly supports changing them.",
            "Return JSON only; do not wrap it in Markdown.",
        ],
        "preservation": {
            "owns_geometry": bool((asset.get("components") or {}).get("owns_geometry")),
            "owns_rig": bool((asset.get("components") or {}).get("owns_rig")),
            "owns_materials": bool((asset.get("components") or {}).get("owns_materials")),
            "owns_animations": bool((asset.get("components") or {}).get("owns_animations")),
            "instruction": "Treat false ownership flags as protected/artist-owned boundaries and do not request destructive regeneration across them.",
        },
        "recommended_user_prompt": (
            "Using this Asset Assistant model context, create a safe Model Change JSON matching my artistic request. "
            "Use model_state to understand the current shape, use only published operation arguments, preserve unrelated artist work, and return JSON only."
        ),
    }

    payload["parameter_contract"] = _parameter_contract(provider, asset.get("parameters") or {})
    payload["model_state"] = _model_state(provider, asset)
    payload["semantic_vocabulary"] = {
        "targets": enriched_targets,
        "already_applied": asset.get("applied_semantic_operations") or [],
        "instruction": (
            "Every executable operation includes an operation_contract. Use only those argument keys, enum values, and ranges. "
            "Use model_state as the current-state reference when choosing the magnitude of a change."
        ),
    }

    payload["return_schema_example"] = {
        "schema": request_template.get("schema", REQUEST_SCHEMA),
        "asset_id": asset.get("asset_id"),
        "provider_key": provider_key,
        "parameter_changes": {},
        "animation_export_names": {},
        "semantic_operations": [example_semantic] if example_semantic is not None else [],
        "component_operations": [],
        "notes": "Describe the intended visual change briefly.",
    }

    payload["instructions"] = {
        "read_first": (
            "Read model_authoring_contract, model_state, parameter_contract, semantic_vocabulary, asset.components, "
            "and request_template before authoring changes."
        ),
        "reference_authority": "CURRENT_ASSET_RELATIVE",
        "important": (
            "This file describes a modification contract, not unrestricted mesh access. Build on the current asset "
            "using supported parameters and semantic operations instead of reconstructing the model from scratch."
        ),
    }
    return payload


__all__ = ["enhance_inspection_document"]
