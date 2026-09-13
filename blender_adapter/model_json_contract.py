# SPDX-License-Identifier: GPL-3.0-or-later
"""Self-document Asset Assistant model inspection JSON for context-free LLM use."""

import copy

from .core import REQUEST_SCHEMA, get_provider

_REPOSITORY = "https://github.com/jhodges0845/blender-object-generator"
_DOC_PATH = "docs/model-json-roundtrip.md"


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


def _example_semantic_operation(asset):
    for target in asset.get("semantic_targets", ()):
        executable = target.get("executable_operations") or []
        if not executable:
            continue
        operation = executable[0]
        example = {
            "operation": operation,
            "target": target.get("key"),
            "arguments": {},
        }
        if operation == "scale":
            example["arguments"] = {"factor": 1.05}
        elif operation == "shape":
            example["arguments"] = {"profile": "REPLACE_WITH_SUPPORTED_PROFILE"}
        return example
    return None


def enhance_inspection_document(document, addon_version=(0, 9, 0)):
    """Return an LLM-oriented copy of the portable Modify inspection document."""
    payload = copy.deepcopy(document)
    asset = payload.get("asset") or {}
    provider_key = str(asset.get("provider_key") or "")
    provider = get_provider(provider_key)
    request_template = payload.get("request_template") or {}
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
            "Use only semantic targets and executable operations listed in asset.semantic_targets.",
            "Do not invent semantic target names, component ids, animation ids, or unsupported operations.",
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
            "Use only the provided parameters/semantic targets, preserve unrelated artist work, and return JSON only."
        ),
    }

    payload["parameter_contract"] = _parameter_contract(provider, asset.get("parameters") or {})
    payload["semantic_vocabulary"] = {
        "targets": asset.get("semantic_targets") or [],
        "already_applied": asset.get("applied_semantic_operations") or [],
        "instruction": (
            "Prefer executable semantic operations for shape intent such as broader shoulders, a narrower face, "
            "or stronger limbs. Use provider parameters for broad procedural proportions when possible."
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
            "Read model_authoring_contract, parameter_contract, semantic_vocabulary, asset.components, "
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
