# SPDX-License-Identifier: GPL-3.0-or-later
"""Make rigging part of the Animate workflow instead of asset creation.

Rigging can support deformation, weighting, posing and bone-driven attachments in
addition to animation, but those are rig-dependent editing concerns rather than base
asset creation.  The artist-facing workflow therefore keeps Create focused on
Generate/Modify and exposes Rig & Pose at the top of Animate.
"""

from .asset_structure import asset_rigs


_CREATE_MODES = (
    ("GENERATE", "Generate", "ADD"),
    ("MODIFY", "Modify", "MODIFIER"),
)


def _single_imported_rig(_panel, _context, root):
    """Let the shared Rig & Pose section own imported-rig state and guidance."""
    return len(asset_rigs(root)) == 1


def install(workflow_ui, workspace_create_ui, normalized_import_workflow_ui):
    """Move the primary Rig UI from Create to the top of Animate.

    The old RIG enum value remains registered so existing .blend files do not break.
    If an older file reopens with that value selected, migrate the visible Create view
    to Modify and keep all rig controls available from Animate.
    """
    workspace_create_ui._CREATE_MODES = _CREATE_MODES

    original_draw_create = workflow_ui._draw_create

    def draw_create(panel, context, ui, modify_ui, working_asset_ui):
        settings = context.scene.humanoid_settings
        if getattr(settings, "asset_assistant_create_view", None) == "RIG":
            settings.asset_assistant_create_view = "MODIFY"
        return original_draw_create(panel, context, ui, modify_ui, working_asset_ui)

    workflow_ui._draw_create = draw_create

    # Imported Animate previously drew its own small rig header.  The shared RIGGING
    # stage now renders that state for generated and imported assets alike, including
    # Pose Mode entry/exit.  Keep only the eligibility check in the imported wrapper.
    normalized_import_workflow_ui._draw_imported_animation_header = _single_imported_rig

    original_draw_animate = workflow_ui._draw_animate

    def draw_animate(panel, context, ui, animation_names_ui, animation_adoption_ui):
        workflow_ui._section_header(
            panel.layout,
            "RIG & POSE",
            "Set up or adjust the rig before working with animation",
            "ARMATURE_DATA",
        )
        ui._WorkflowPanel.draw(workflow_ui._stage_proxy(panel, "RIGGING"), context)
        panel.layout.separator()
        return original_draw_animate(
            panel,
            context,
            ui,
            animation_names_ui,
            animation_adoption_ui,
        )

    workflow_ui._draw_animate = draw_animate


__all__ = ["install"]
