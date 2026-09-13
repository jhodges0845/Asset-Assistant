# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-independent inspection and planning contracts for Modify."""

from dataclasses import dataclass
from math import isfinite
from typing import Optional, Tuple

from .components import ComponentRecord, validate_component
from .objects import get_provider


@dataclass(frozen=True)
class AnimationSnapshot:
    clip_id: str
    export_name: str
    animation_id: Optional[str] = None
    display_name: Optional[str] = None
    source: Optional[str] = None
    rig_signature: Optional[str] = None
    frame_start: Optional[float] = None
    frame_end: Optional[float] = None
    fps: Optional[float] = None
    looping: Optional[bool] = None
    root_motion: Optional[str] = None
    owns_curves: Optional[bool] = None
    source_reference: Optional[str] = None
    provider_key: Optional[str] = None
    capability: Optional[str] = None


@dataclass(frozen=True)
class SemanticOperation:
    """Portable provider-aware edit against a declared semantic target."""

    operation: str
    target: str
    arguments: Tuple[Tuple[str, object], ...] = ()

    def argument_values(self):
        return dict(self.arguments)


@dataclass(frozen=True)
class ComponentOperation:
    """Portable requested component mutation; execution is intentionally separate."""

    operation: str
    component_id: str
    component: ComponentRecord = None


@dataclass(frozen=True)
class AssetSnapshot:
    asset_id: str
    provider_key: str
    provider_label: str
    parameters: Tuple[Tuple[str, object], ...]
    animations: Tuple[AnimationSnapshot, ...] = ()
    semantic_operations: Tuple[SemanticOperation, ...] = ()
    components: Tuple[ComponentRecord, ...] = ()
    has_rig: bool = False
    has_materials: bool = False
    has_animations: bool = False
    owns_geometry: bool = False
    owns_rig: bool = False
    owns_materials: bool = False
    owns_animations: bool = False
    warnings: Tuple[str, ...] = ()

    def parameter_values(self):
        return dict(self.parameters)


@dataclass(frozen=True)
class ModificationRequest:
    """Explicit requested changes; omitted fields mean preserve."""

    parameter_changes: Tuple[Tuple[str, object], ...] = ()
    animation_export_names: Tuple[Tuple[str, str], ...] = ()
    semantic_operations: Tuple[SemanticOperation, ...] = ()
    component_operations: Tuple[ComponentOperation, ...] = ()


@dataclass(frozen=True)
class ModificationPlan:
    asset_id: str
    provider_key: str
    requested_parameter_changes: Tuple[Tuple[str, object], ...]
    requested_animation_renames: Tuple[Tuple[str, str], ...]
    requested_semantic_operations: Tuple[SemanticOperation, ...]
    requested_component_operations: Tuple[ComponentOperation, ...]
    rebuild_components: Tuple[str, ...]
    blockers: Tuple[str, ...]

    @property
    def safe_to_apply(self):
        return not self.blockers


def _as_unique_dict(items, label):
    result = {}
    for key, value in items:
        if not isinstance(key, str) or not key.strip():
            raise ValueError(label + " keys must be nonempty strings")
        if key in result:
            raise ValueError("Duplicate " + label + " key: " + key)
        result[key] = value
    return result


def _choice_values(parameter):
    """Return the serialized values accepted for a provider enum parameter."""
    values = []
    for choice in parameter.choices:
        if isinstance(choice, (tuple, list)) and choice:
            values.append(choice[0])
        else:
            values.append(choice)
    return tuple(values)


def _validate_parameter(parameter, value):
    if parameter.choices:
        if value not in _choice_values(parameter):
            raise ValueError(parameter.label + " is not an allowed choice")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(parameter.label + " must be a number")
    normalized = float(value)
    if not isfinite(normalized):
        raise ValueError(parameter.label + " must be finite")
    if not parameter.minimum <= normalized <= parameter.maximum:
        raise ValueError(parameter.label + " is outside its supported range")
    return normalized


def _validate_json_value(value, path="argument"):
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(path + " must be finite")
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_validate_json_value(item, path) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _validate_json_value(item, path + "." + str(key))) for key, item in value.items()))
    raise TypeError(path + " must contain JSON-compatible values")


def _normalize_semantic_operations(provider, operations):
    targets = {target.key: target for target in getattr(provider, "semantic_targets", ())}
    normalized = []
    for operation in operations:
        if not isinstance(operation, SemanticOperation):
            raise TypeError("semantic_operations must contain SemanticOperation values")
        if operation.target not in targets:
            raise ValueError("Unsupported semantic target for " + provider.label + ": " + operation.target)
        target = targets[operation.target]
        if operation.operation not in target.operations:
            raise ValueError(operation.operation + " is not supported for semantic target " + operation.target)
        args = _as_unique_dict(operation.arguments, "semantic argument")
        normalized_args = tuple(sorted((key, _validate_json_value(value, key)) for key, value in args.items()))
        normalized.append(SemanticOperation(operation.operation, operation.target, normalized_args))
    return tuple(normalized)


def _normalize_component_operations(snapshot, operations):
    known = {record.component_id: record for record in snapshot.components}
    normalized = []
    seen = set()
    for operation in operations:
        if not isinstance(operation, ComponentOperation):
            raise TypeError("component_operations must contain ComponentOperation values")
        action = operation.operation.strip() if isinstance(operation.operation, str) else ""
        component_id = operation.component_id.strip() if isinstance(operation.component_id, str) else ""
        if action not in ("add", "remove", "replace"):
            raise ValueError("Unsupported component operation: " + action)
        if not component_id:
            raise ValueError("component operation id must be a nonempty string")
        if component_id in seen:
            raise ValueError("Duplicate component operation id: " + component_id)
        seen.add(component_id)
        if action == "add" and component_id in known:
            raise ValueError("Cannot add an already attached component: " + component_id)
        if action in ("remove", "replace") and component_id not in known:
            raise ValueError("Unknown attached component: " + component_id)
        component = operation.component
        if action in ("add", "replace"):
            if component is None:
                raise ValueError(action + " component operation requires component metadata")
            validate_component(component)
            if component.component_id != component_id:
                raise ValueError("component operation id does not match component metadata")
        elif component is not None:
            raise ValueError("remove component operation must not include replacement metadata")
        normalized.append(ComponentOperation(action, component_id, component))
    return tuple(normalized)


def _conservative_parameter_impact(provider, snapshot):
    components = ["geometry"]
    if provider.supports_rig and snapshot.has_rig:
        components.append("rig")
    if getattr(provider, "supports_materials", False) and snapshot.has_materials:
        components.append("materials")
    if snapshot.has_animations and any(getattr(provider, capability, False) for capability in ("supports_idle", "supports_locomotion", "supports_run", "supports_flight")):
        components.append("animations")
    return tuple(components)


def _semantic_apply_blockers(provider, operations):
    if not operations:
        return []
    supported = set(getattr(provider, "semantic_apply_capabilities", ()))
    if not callable(getattr(provider, "semantic_mesh", None)):
        return [provider.label + " does not yet implement semantic geometry apply"]
    blockers = []
    for operation in operations:
        capability = (operation.target, operation.operation)
        if capability not in supported:
            blockers.append(
                provider.label + " semantic apply does not yet support "
                + operation.operation + " on " + operation.target
            )
    return blockers


def plan_modification(snapshot, request):
    if not isinstance(snapshot, AssetSnapshot):
        raise TypeError("snapshot must be an AssetSnapshot")
    if not isinstance(request, ModificationRequest):
        raise TypeError("request must be a ModificationRequest")

    provider = get_provider(snapshot.provider_key)
    if snapshot.provider_label != provider.label:
        raise ValueError("Snapshot provider label does not match provider registry")

    current = snapshot.parameter_values()
    changes = _as_unique_dict(request.parameter_changes, "parameter change")
    parameter_by_key = {parameter.key: parameter for parameter in provider.parameters}
    normalized_changes = []
    for key, value in changes.items():
        if key not in parameter_by_key:
            raise ValueError("Unsupported parameter for " + provider.label + ": " + key)
        if key not in current:
            raise ValueError("Snapshot is missing provider parameter: " + key)
        normalized = _validate_parameter(parameter_by_key[key], value)
        if normalized != current[key]:
            normalized_changes.append((key, normalized))

    animation_names = _as_unique_dict(request.animation_export_names, "animation rename")
    generated_clips = {clip.clip_id: clip for clip in snapshot.animations}
    normalized_renames = []
    for clip_id, export_name in animation_names.items():
        if clip_id not in generated_clips:
            raise ValueError("Unknown generated animation clip: " + clip_id)
        if not isinstance(export_name, str) or not export_name.strip():
            raise ValueError("Animation export name must be a nonempty string")
        cleaned = export_name.strip()
        if cleaned != generated_clips[clip_id].export_name:
            normalized_renames.append((clip_id, cleaned))

    semantic = _normalize_semantic_operations(provider, request.semantic_operations)
    component_operations = _normalize_component_operations(snapshot, request.component_operations)
    if normalized_changes:
        rebuild = _conservative_parameter_impact(provider, snapshot)
    elif semantic:
        rebuild = ("geometry",)
    else:
        rebuild = ()

    blockers = []
    ownership = {"geometry": snapshot.owns_geometry, "rig": snapshot.owns_rig, "materials": snapshot.owns_materials, "animations": snapshot.owns_animations}
    for component in rebuild:
        if not ownership[component]:
            blockers.append("Cannot safely replace unowned or ambiguous " + component)
    if normalized_renames and not snapshot.owns_animations:
        blockers.append("Cannot safely rename unowned or ambiguous animations")
    blockers.extend(_semantic_apply_blockers(provider, semantic))
    if component_operations:
        blockers.append("Component mutations are validated for transport but are not executable through Modify yet")

    return ModificationPlan(
        asset_id=snapshot.asset_id,
        provider_key=provider.key,
        requested_parameter_changes=tuple(normalized_changes),
        requested_animation_renames=tuple(normalized_renames),
        requested_semantic_operations=semantic,
        requested_component_operations=component_operations,
        rebuild_components=tuple(rebuild),
        blockers=tuple(blockers),
    )
