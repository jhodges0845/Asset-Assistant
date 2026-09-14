# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit Blender panel-class bindings for the composed Asset Assistant workspace.

Presentation modules decide what to draw through PresentationRegistry. This module is
the narrow host boundary that attaches those composed renderers to Blender panel
classes and hides legacy panels that are now represented inside the workspace.
"""


def bind_workspace_panel(panel_type, renderer, *, category="Asset Assistant"):
    """Attach the composed workspace renderer to Blender's primary panel class."""
    panel_type.bl_label = "Asset Assistant"
    panel_type.bl_category = category
    panel_type.bl_order = 0
    panel_type.bl_options = set(getattr(panel_type, "bl_options", set())) - {"DEFAULT_CLOSED"}

    def draw_workspace(panel, context):
        return renderer(panel, context)

    draw_workspace._asset_assistant_workspace = True
    panel_type.draw = draw_workspace


def hide_legacy_panels(panel_types, *, category="Asset Assistant"):
    """Keep legacy panel classes registered but hidden behind the unified workspace."""
    for order, panel_type in enumerate(panel_types, start=1):
        panel_type.bl_category = category
        panel_type.bl_order = order

        def poll(_cls, _context):
            return False

        panel_type.poll = classmethod(poll)


__all__ = ["bind_workspace_panel", "hide_legacy_panels"]
