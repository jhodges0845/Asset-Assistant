# SPDX-License-Identifier: GPL-3.0-or-later
"""Provider registry and declaration validation.

Concrete provider implementations live under ``object_core.providers`` so the
registry can remain focused on shared contracts as new asset families are added.
"""

from .providers import (
    AVIAN_PARAMETERS,
    HUMAN_PARAMETERS,
    QUADRUPED_PARAMETERS,
    AvianProvider,
    BoxProvider,
    HumanProvider,
    HumanoidProvider,
    Parameter,
    QuadrupedProvider,
    SemanticTarget,
)


LEGACY_PROVIDER_KEYS = {"dog": "quadruped"}


def validate_provider(provider):
    """Validate declarations without generating assets or depending on a host."""
    for field in ("key", "label"):
        value = getattr(provider, field, None)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Provider " + field + " must be a nonempty string")
    for field in ("supports_rig", "supports_idle", "uses_skin_weights"):
        if not isinstance(getattr(provider, field, None), bool):
            raise TypeError(provider.key + ": " + field + " must be a boolean")
    supports_locomotion = getattr(provider, "supports_locomotion", False)
    supports_flight = getattr(provider, "supports_flight", False)
    supports_run = getattr(provider, "supports_run", False)
    supports_materials = getattr(provider, "supports_materials", False)
    for name, value in (("supports_locomotion", supports_locomotion), ("supports_flight", supports_flight), ("supports_run", supports_run), ("supports_materials", supports_materials)):
        if not isinstance(value, bool):
            raise TypeError(provider.key + ": " + name + " must be a boolean")
    if provider.supports_idle and not provider.supports_rig:
        raise ValueError(provider.key + ": idle support requires rig support")
    if supports_locomotion and not provider.supports_rig:
        raise ValueError(provider.key + ": locomotion support requires rig support")
    if supports_flight and not provider.supports_rig:
        raise ValueError(provider.key + ": flight support requires rig support")
    if supports_run and not provider.supports_rig:
        raise ValueError(provider.key + ": run support requires rig support")
    if provider.uses_skin_weights and not provider.supports_rig:
        raise ValueError(provider.key + ": skin weights require rig support")
    locomotion_label = getattr(provider, "locomotion_label", None)
    if locomotion_label is not None and (not isinstance(locomotion_label, str) or not locomotion_label.strip()):
        raise ValueError(provider.key + ": locomotion_label must be a nonempty string when declared")

    required = ["mesh"]
    if provider.supports_rig: required.append("skeleton")
    if provider.supports_idle: required.append("idle")
    if supports_locomotion: required.append("locomotion")
    if supports_flight: required.append("flight")
    if supports_run: required.append("run")
    if provider.uses_skin_weights: required.append("skin_weights")
    if supports_materials: required.append("materials")
    for method in required:
        if not callable(getattr(provider, method, None)):
            raise TypeError(provider.key + ": required method " + method + " must be callable")

    parameters = getattr(provider, "parameters", None)
    if not isinstance(parameters, tuple):
        raise TypeError(provider.key + ": parameters must be a tuple of Parameter definitions")
    keys = set()
    for parameter in parameters:
        if not isinstance(parameter, Parameter):
            raise TypeError(provider.key + ": parameters must contain Parameter definitions")
        if not isinstance(parameter.key, str) or not parameter.key.strip() or parameter.key in keys:
            raise ValueError(provider.key + ": parameter keys must be nonempty and unique")
        keys.add(parameter.key)

    semantic_targets = getattr(provider, "semantic_targets", ())
    if not isinstance(semantic_targets, tuple):
        raise TypeError(provider.key + ": semantic_targets must be a tuple")
    semantic_keys = set()
    for target in semantic_targets:
        if not isinstance(target, SemanticTarget):
            raise TypeError(provider.key + ": semantic_targets must contain SemanticTarget definitions")
        if not target.key.strip() or target.key in semantic_keys:
            raise ValueError(provider.key + ": semantic target keys must be nonempty and unique")
        if not target.label.strip() or not target.kind.strip() or not target.operations:
            raise ValueError(provider.key + ": semantic targets require label, kind, and operations")
        if any(not isinstance(op, str) or not op.strip() for op in target.operations):
            raise ValueError(provider.key + ": semantic target operations must be nonempty strings")
        semantic_keys.add(target.key)
    return provider


OBJECT_TYPES = {provider.key: validate_provider(provider) for provider in (HumanoidProvider(), HumanProvider(), BoxProvider(), QuadrupedProvider(), AvianProvider())}


def canonical_provider_key(key):
    return LEGACY_PROVIDER_KEYS.get(key, key)


def get_provider(key):
    canonical_key = canonical_provider_key(key)
    try:
        provider = OBJECT_TYPES[canonical_key]
    except KeyError:
        raise ValueError("Unsupported object type: " + str(key)) from None
    validate_provider(provider)
    if provider.key != canonical_key:
        raise ValueError("Provider registry key does not match declared key: " + str(canonical_key))
    return provider


__all__ = ["Parameter", "AVIAN_PARAMETERS", "AvianProvider", "QUADRUPED_PARAMETERS", "QuadrupedProvider", "HUMAN_PARAMETERS", "HumanoidProvider", "HumanProvider", "BoxProvider", "validate_provider", "OBJECT_TYPES", "LEGACY_PROVIDER_KEYS", "canonical_provider_key", "get_provider"]
