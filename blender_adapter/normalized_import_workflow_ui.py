# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep imported assets on normalized workflow APIs all the way through the UI.

Importers may create different raw Blender hierarchies. This module makes the
artist-facing summary and Animate workspace consume the same logical asset model
used by inspection, validation, checkpointing and export instead of falling back
to direct-child or generated-provider assumptions.
"""

from .asset_structure import asset_rigs, logical_asset
from .workflow import is_external_asset


def _target(context):
    settings = getattr(getattr(context, "scene", None), "humanoid_settings", None)
    return getattr(settings, "target", None) if settings is not None else None


def _component_count(structure):
    """Count first-class components, not arbitrary imported base meshes."""
    component_ids = set()
    for obj in structure.get("objects", ()):
        getter = getattr(obj, "get", None)
        component_id = getter("asset_assistant_component_id", "") if callable(getter) else ""
        if component_id:
            component_ids.add(str(component_id))
    return len(component_ids)


def _draw_normalized_summary(asset_identity_ui, layout, context):
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
    animation_count = structure["animation_count"]
    component_count = _component_count(structure)

    status = card.row(align=True)
    status.label(text="Rigged" if has_rig else "No Rig", icon="ARMATURE_DATA")
    status.label(text=str(animation_count) + (" Clip" if animation_count == 1 else " Clips"), icon="ACTION")
    status.label(text=asset_identity_ui._component_label(component_count), icon="CUBE")
    return logical_root


def _draw_animation_adoption(box, target):
    """Enable adoption from the normalized base rig rather than direct children."""
    box.label(text="Bring Your Own Animation", icon="IMPORT")
    rigs = asset_rigs(target) if target is not None else ()
    row = box.row()
    row.enabled = len(rigs) == 1
    row.scale_y = 1.15
    row.operator("asset_assistant.adopt_animation_action", text="Adopt Existing Action", icon="ACTION")
    box.label(text="Keeps artist curves, NLA and drivers intact.")


def _decorate_asset_summary(asset_identity_ui):
    def decorate(next_renderer, layout, context):
        settings = getattr(context.scene, "humanoid_settings", None)
        target = getattr(settings, "target", None) if settings else None
        if target is None:
            return next_renderer(layout, context)

        logical_root = _draw_normalized_summary(asset_identity_ui, layout, context)
        if logical_root is not None:
            asset_identity_ui._draw_identity(layout, logical_root)
        return logical_root

    return decorate


def _decorate_animate(next_renderer, panel, context, ui_module, animation_names_ui, animation_adoption_ui):
    root = _target(context)
    if root is None or not is_external_asset(root):
        return next_renderer(panel, context, ui_module, animation_names_ui, animation_adoption_ui)

    from . import workflow_ui

    workflow_ui._section_header(panel.layout, "ANIMATION", "Create, preview and manage clips", "ACTION")
    has_single_rig = len(asset_rigs(root)) == 1
    if has_single_rig:
        panel.layout.separator()
        clip_box = panel.layout.box()
        clip_box.label(text="CLIP LIBRARY", icon="ACTION")
        animation_names_ui.ASSET_ASSISTANT_PT_animation_names.draw(
            type("ClipLibraryProxy", (), {"layout": clip_box})(), context
        )
    if animation_adoption_ui is not None:
        panel.layout.separator()
        _draw_animation_adoption(panel.layout.box(), root)


def install(presentation_registry, asset_identity_ui):
    """Compose normalized imported-asset presentation through explicit registry slots."""
    presentation_registry.decorate(
        "shared.asset_summary",
        _decorate_asset_summary(asset_identity_ui),
        owner=__name__ + ".asset_summary",
        order=100,
    )
    presentation_registry.decorate(
        "workspace.animate",
        _decorate_animate,
        owner=__name__ + ".animate",
        order=100,
    )


__all__ = ["install"]
