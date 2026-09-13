# SPDX-License-Identifier: GPL-3.0-or-later
"""Artist-facing asset identity without coupling display names to provider identity."""

from .asset_structure import logical_asset


def _source_label(target):
    source = str(target.get("asset_assistant_source", "")).strip().upper()
    labels = {
        "GENERATED": "Generated",
        "IMPORTED": "Imported",
        "ADOPTED": "Imported / Adopted",
    }
    if source in labels:
        return labels[source]
    if target.get("generator") in ("humanoid_blockout", "object_generator"):
        return "Generated"
    return "External / Unclassified"


def _provider_label(target):
    try:
        from .workflow import provider_for
        return provider_for(target).label
    except (ValueError, TypeError, AttributeError, KeyError):
        stored = str(target.get("object_type", "")).strip()
        if stored:
            return stored.replace("_", " ").title()
        capability = str(target.get("asset_assistant_external_capability", "")).strip().title()
        return (capability + " Asset") if capability else "Imported Asset"


def _component_label(count):
    return str(count) + (" Component" if count == 1 else " Components")


def _draw_summary(layout, context):
    settings = getattr(context.scene, "humanoid_settings", None)
    target = getattr(settings, "target", None) if settings else None
    card = layout.box()
    title = card.row(align=True)
    title.label(text="CURRENT ASSET", icon="OBJECT_DATA")
    if target is None:
        card.label(text="Nothing selected yet")
        return None

    structure = logical_asset(target)
    logical_root = structure["root"] or target
    title.label(text=logical_root.name)
    has_rig = bool(structure["rigs"])
    mesh_count = len(structure["meshes"])
    animation_count = structure["animation_count"]

    status = card.row(align=True)
    status.label(text="Rigged" if has_rig else "No Rig", icon="ARMATURE_DATA")
    status.label(text=str(animation_count) + (" Clip" if animation_count == 1 else " Clips"), icon="ACTION")
    status.label(text=_component_label(mesh_count), icon="CUBE")
    return logical_root


def _draw_identity(layout, target):
    identity = layout.box()
    identity.label(text="ASSET IDENTITY", icon="OBJECT_DATA")
    identity.prop(target, "name", text="Name")

    details = identity.column(align=True)
    details.label(text="Type: " + _provider_label(target), icon="OUTLINER_OB_MESH")
    details.label(text="Source: " + _source_label(target), icon="IMPORT")
    return identity


def draw_asset_summary(layout, context):
    settings = getattr(context.scene, "humanoid_settings", None)
    target = getattr(settings, "target", None) if settings else None
    is_empty_create = (
        settings is not None
        and target is None
        and getattr(settings, "asset_assistant_workspace", None) == "CREATE"
        and getattr(settings, "asset_assistant_create_view", None) == "GENERATE"
    )
    if is_empty_create:
        return
    target = _draw_summary(layout, context)
    if target is not None:
        _draw_identity(layout, target)


def install(presentation_registry):
    """Register the artist-facing asset summary explicitly."""
    presentation_registry.register_renderer(
        "shared.asset_summary",
        draw_asset_summary,
        owner=__name__,
    )


__all__ = ["install", "draw_asset_summary"]
