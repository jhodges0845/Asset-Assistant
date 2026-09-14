# SPDX-License-Identifier: GPL-3.0-or-later
"""Make rigging part of the Animate workflow instead of asset creation.

Rigging can support deformation, weighting, posing and bone-driven attachments in
addition to animation, but those are rig-dependent editing concerns rather than base
asset creation. The artist-facing workflow therefore keeps Create focused on
Generate/Modify and exposes Rig & Pose at the top of Animate.
"""

_CREATE_MODES = (
    ("GENERATE", "Generate", "ADD"),
    ("MODIFY", "Modify", "MODIFIER"),
)


def _decorate_create(next_renderer, panel, context, ui, modify_ui, working_asset_ui):
    settings = context.scene.humanoid_settings
    if getattr(settings, "asset_assistant_create_view", None) == "RIG":
        settings.asset_assistant_create_view = "MODIFY"
    return next_renderer(panel, context, ui, modify_ui, working_asset_ui)


def _decorate_animate(next_renderer, panel, context, ui, animation_names_ui, animation_adoption_ui):
    from . import workflow_ui

    workflow_ui._section_header(
        panel.layout,
        "RIG & POSE",
        "Set up or adjust the rig before working with animation",
        "ARMATURE_DATA",
    )
    ui._WorkflowPanel.draw(workflow_ui._stage_proxy(panel, "RIGGING"), context)
    panel.layout.separator()
    return next_renderer(
        panel,
        context,
        ui,
        animation_names_ui,
        animation_adoption_ui,
    )


def install(presentation_registry, workspace_create_ui):
    """Compose Rig/Create/Animate presentation through explicit registry slots.

    The old RIG enum value remains registered so existing .blend files do not break.
    If an older file reopens with that value selected, migrate the visible Create view
    to Modify and keep all rig controls available from Animate.
    """
    workspace_create_ui._CREATE_MODES = _CREATE_MODES

    presentation_registry.decorate(
        "workspace.create",
        _decorate_create,
        owner=__name__ + ".create",
        order=100,
    )
    presentation_registry.decorate(
        "workspace.animate",
        _decorate_animate,
        owner=__name__ + ".animate",
        order=200,
    )


__all__ = ["install"]
