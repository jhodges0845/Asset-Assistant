# SPDX-License-Identifier: GPL-3.0-or-later
"""Visual identity for the four primary Asset Assistant workspaces."""

_WORKSPACES = (
    ("CREATE", "Create", "USER"),
    ("ANIMATE", "Animate", "ACTION"),
    ("COMPONENTS", "Components", "CUBE"),
    ("EXPORT", "Export", "EXPORT"),
)


def _draw_workspace_nav(layout, settings):
    """Draw four large single-piece workspace buttons with icon + label together."""
    row = layout.row(align=True)
    row.scale_y = 1.65

    for key, label, icon in _WORKSPACES:
        row.prop_enum(
            settings,
            "asset_assistant_workspace",
            key,
            text=label,
            icon=icon,
        )


def install(presentation_registry):
    """Register navigation without mutating ``workflow_ui`` callbacks."""
    presentation_registry.register_renderer(
        "shared.workspace_navigation",
        _draw_workspace_nav,
        owner=__name__,
    )


__all__ = ["install"]
