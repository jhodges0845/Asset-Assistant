# SPDX-License-Identifier: GPL-3.0-or-later
"""High-impact Blender-native presentation for the Asset Assistant Create workspace.

This module owns presentation only. Existing provider parameters and operators are
reused so generation, Modify, Rig, animation, and export behavior remain unchanged.
"""

_ASSET_TILES = (
    ("human_experimental", "USER"),
    ("human_surface_study", "OUTLINER_OB_MESH"),
    ("quadruped", "ARMATURE_DATA"),
    ("avian", "OUTLINER_OB_MESH"),
    ("box", "CUBE"),
)

_CREATE_MODES = (
    ("GENERATE", "Generate", "ADD"),
    ("MODIFY", "Modify", "MODIFIER"),
    ("RIG", "Rig", "ARMATURE_DATA"),
)

_PRESENTATION_REGISTRY = None
_WORKFLOW_UI = None
_ASSET_INSPECTION_UI = None
_ASSET_FILE_IMPORT_UI = None


def _draw_create_mode_nav(layout, settings):
    """Keep Generate / Modify / Rig available without overpowering the main flow."""
    row = layout.row(align=True)
    row.scale_y = 1.2
    for key, label, icon in _CREATE_MODES:
        row.prop_enum(
            settings,
            "asset_assistant_create_view",
            key,
            text=label,
            icon=icon,
        )


def _draw_asset_tiles(layout, settings, ui):
    """Draw each provider as one cohesive tall button with icon and label together."""
    tiles = layout.row(align=True)
    tiles.scale_y = 2.25
    for key, icon in _ASSET_TILES:
        provider = ui.get_provider(key)
        tiles.prop_enum(
            settings,
            "object_type",
            key,
            text=provider.label,
            icon=icon,
        )


def _draw_start_options(layout, context, working_asset_ui):
    """Offer file import and in-scene inspection before generation.

    Editable checkpoints are complete Blender files, so they can be reopened through
    Blender's normal File > Open workflow. Keeping a second open-file button here made
    the distinction between importing an asset and replacing the current session less
    clear without adding a necessary capability.
    """
    if working_asset_ui is None and _ASSET_INSPECTION_UI is None and _ASSET_FILE_IMPORT_UI is None:
        return
    start = layout.box()
    start.label(text="START WITH", icon="FILE_FOLDER")
    start.label(text="Import an asset or inspect scene work")

    if _ASSET_FILE_IMPORT_UI is not None:
        import_row = start.row()
        import_row.scale_y = 1.5
        import_row.operator(
            "asset_assistant.preflight_asset_file",
            text="Import Asset File",
            icon="IMPORT",
        )
        start.label(text="Supports .blend, .glb, .gltf and .fbx")

    if _ASSET_INSPECTION_UI is not None:
        secondary = start.row()
        secondary.scale_y = 1.2
        secondary.operator(
            "asset_assistant.inspect_selected_asset",
            text="Inspect Selected",
            icon="VIEWZOOM",
        )

    if _ASSET_FILE_IMPORT_UI is not None:
        _ASSET_FILE_IMPORT_UI.draw_file_preflight_report(start, context.scene)
    if _ASSET_INSPECTION_UI is not None:
        _ASSET_INSPECTION_UI.draw_inspection_report(start, context.scene)


def _draw_generate(panel, context, ui, working_asset_ui):
    settings = context.scene.humanoid_settings
    layout = panel.layout
    provider = ui.get_provider(settings.object_type)
    fields = tuple(provider.parameters)
    if settings.object_type == "human_surface_study":
        layout.label(text="Experimental static anatomy; no rig or UVs", icon="INFO")

    _draw_start_options(layout, context, working_asset_ui)
    if working_asset_ui is not None or _ASSET_INSPECTION_UI is not None or _ASSET_FILE_IMPORT_UI is not None:
        layout.separator(factor=0.6)

    create = layout.box()
    hero = create.row(align=True)
    hero.scale_y = 1.35
    hero.label(text="CREATE NEW ASSET", icon="USER")
    create.label(text="Choose a starting point, tune the essentials, then build")
    create.separator(factor=0.5)

    _draw_asset_tiles(create, settings, ui)
    create.separator(factor=0.7)

    setup_title = create.row(align=True)
    setup_title.label(text="QUICK SETUP", icon="PREFERENCES")
    setup_title.label(text=provider.label)
    for field in fields[:3]:
        create.prop(settings, ui._field_name(provider, field))

    if len(fields) > 3:
        advanced = create.column(align=True)
        advanced.separator(factor=0.35)
        advanced.prop(
            settings,
            "asset_assistant_create_advanced",
            text="Advanced Options",
            toggle=True,
            icon="DOWNARROW_HLT" if settings.asset_assistant_create_advanced else "RIGHTARROW",
        )
        if settings.asset_assistant_create_advanced:
            for field in fields[3:]:
                advanced.prop(settings, ui._field_name(provider, field))

    create.separator(factor=0.75)
    action = create.row()
    action.scale_y = 2.0
    replacing = getattr(settings, "target", None) is not None
    action.operator(
        "asset_assistant.generate_replace_current",
        text=("Replace Current with " if replacing else "Generate ") + provider.label,
        icon="FILE_REFRESH" if replacing else "ADD",
    )
    create.label(
        text="Replaces the current asset after a successful build"
        if replacing else "Creates a new editable Asset Assistant model"
    )


def _draw_create(panel, context, ui, modify_ui, working_asset_ui):
    """Create renderer with a first-impression visual hierarchy."""
    settings = context.scene.humanoid_settings
    layout = panel.layout

    _draw_create_mode_nav(layout, settings)
    layout.separator(factor=0.8)

    if settings.asset_assistant_create_view == "GENERATE":
        _draw_generate(panel, context, ui, working_asset_ui)
        return

    if settings.asset_assistant_create_view == "MODIFY":
        workspace = _WORKFLOW_UI
        workspace._section_header(
            layout,
            "MODIFY ASSET",
            "Load, tune, preview, then apply",
            "MODIFIER",
        )
        renderer = _PRESENTATION_REGISTRY.resolve("create.modify", workspace._draw_artist_modify)
        renderer(panel, context, ui, modify_ui)
        return

    workspace = _WORKFLOW_UI
    workspace._section_header(
        layout,
        "RIG & POSE",
        "Prepare the current asset for animation",
        "ARMATURE_DATA",
    )
    ui._WorkflowPanel.draw(workspace._stage_proxy(panel, "RIGGING"), context)


def install(presentation_registry, workflow_ui, ui, asset_inspection_ui=None, asset_file_import_ui=None):
    """Register the Create renderer before Blender registers the settings class."""
    global _PRESENTATION_REGISTRY, _WORKFLOW_UI, _ASSET_INSPECTION_UI, _ASSET_FILE_IMPORT_UI
    _PRESENTATION_REGISTRY = presentation_registry
    _WORKFLOW_UI = workflow_ui
    _ASSET_INSPECTION_UI = asset_inspection_ui
    _ASSET_FILE_IMPORT_UI = asset_file_import_ui

    annotations = ui.HUMANOID_PG_settings.__annotations__
    if "asset_assistant_create_advanced" not in annotations:
        annotations["asset_assistant_create_advanced"] = ui.BoolProperty(
            name="Advanced Options",
            default=False,
        )

    presentation_registry.register_renderer(
        "workspace.create",
        _draw_create,
        owner=__name__,
    )


__all__ = ["install"]
