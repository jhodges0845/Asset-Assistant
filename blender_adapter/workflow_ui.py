# SPDX-License-Identifier: GPL-3.0-or-later
"""Present Asset Assistant as one compact Blender sidebar workspace."""

from pathlib import Path

_CATEGORY = "Asset Assistant"


def _section_header(layout, title, subtitle="", icon="NONE"):
    """Create a compact Blender-native section heading."""
    layout.label(text=title, icon=icon)
    if subtitle:
        layout.label(text=subtitle)


def _asset_summary(layout, context):
    settings = getattr(context.scene, "humanoid_settings", None)
    target = getattr(settings, "target", None) if settings else None
    card = layout.box()
    title = card.row(align=True)
    title.label(text="CURRENT ASSET", icon="OBJECT_DATA")
    if target is None:
        card.label(text="Nothing selected yet")
        return
    title.label(text=target.name)
    children = tuple(target.children)
    has_rig = any(obj.type == "ARMATURE" for obj in children)
    component_count = sum(obj.type == "MESH" for obj in children)
    animation_count = 0
    for obj in children:
        if obj.type != "ARMATURE" or not obj.animation_data:
            continue
        if obj.animation_data.action is not None:
            animation_count += 1
        animation_count += len(obj.animation_data.nla_tracks)
    status = card.row(align=True)
    status.label(text="Rigged" if has_rig else "No Rig", icon="ARMATURE_DATA")
    status.label(text=str(animation_count) + " Clips", icon="ACTION")
    status.label(text=str(component_count) + " Parts", icon="OUTLINER_OB_MESH")


def _draw_component_actions(box, target, hair_component_ui, clothing_component_ui, self_rigged_accessory):
    generated = box.box()
    _section_header(generated, "ADD COMPONENT", "Build onto the current asset", "ADD")
    if target is None:
        generated.label(text="Create or choose an asset first.", icon="INFO")
    if hair_component_ui is not None:
        row = generated.row(); row.enabled = target is not None; row.scale_y = 1.1
        row.operator("asset_assistant.generate_hair_shell", text="Hair", icon="OUTLINER_OB_MESH")
    if clothing_component_ui is not None:
        row = generated.row(); row.enabled = target is not None and clothing_component_ui._supports_shirt(target); row.scale_y = 1.1
        row.operator("asset_assistant.generate_basic_shirt", text="Shirt", icon="MOD_CLOTH")
    row = generated.row(); row.enabled = target is not None; row.scale_y = 1.1
    row.operator("asset_assistant.generate_ring_component", text="Ring / Bracelet", icon="MESH_TORUS")
    if self_rigged_accessory is not None:
        row = generated.row(); row.enabled = target is not None; row.scale_y = 1.1
        row.operator("asset_assistant.generate_self_rigged_accessory", text="Self-Rigged Accessory", icon="ARMATURE_DATA")
    imported = box.box()
    _section_header(imported, "IMPORT COMPONENT", "Bring in artist-created geometry", "IMPORT")
    row = imported.row(); row.enabled = target is not None; row.scale_y = 1.2
    row.operator("asset_assistant.adopt_selected_component", text="Adopt Selected Mesh", icon="IMPORT")
    imported.label(text="Adopted mesh geometry becomes Asset Assistant-managed.")
    imported.label(text="Existing materials remain artist-owned.")


def _draw_animation_adoption(box, target):
    box.label(text="Bring Your Own Animation", icon="IMPORT")
    row = box.row(); row.enabled = target is not None and sum(obj.type == "ARMATURE" for obj in target.children) == 1
    row.scale_y = 1.15
    row.operator("asset_assistant.adopt_animation_action", text="Adopt Existing Action", icon="ACTION")
    box.label(text="Keeps artist curves, NLA and drivers intact.")


def _stage_proxy(panel, stage):
    proxy = type("AssetAssistantStageProxy", (), {})()
    proxy.layout = panel.layout
    proxy.stage = stage
    return proxy


def _draw_artist_modify(panel, context, ui, modify_ui):
    layout = panel.layout
    settings = context.scene.humanoid_settings
    root = modify_ui._character(context)
    if root is None:
        empty = layout.box()
        empty.label(text="Choose an Asset Assistant asset to edit.", icon="INFO")
        empty.prop(settings, "target", text="Asset")
        return
    try:
        provider = modify_ui.provider_for(root)
    except (ValueError, TypeError, AttributeError) as error:
        layout.label(text=str(error), icon="ERROR")
        return
    intro = layout.box()
    intro.label(text="SOURCE VALUES", icon="IMPORT")
    intro.label(text=provider.label + " settings from " + root.name)
    load = intro.row(); load.scale_y = 1.2
    load.operator("asset_assistant.modify_inspect", text="Load Current Values", icon="IMPORT")
    params = layout.box()
    _section_header(params, "ADJUSTMENTS", "Tune the asset, preview the impact, then apply", "MODIFIER")
    for field in provider.parameters:
        params.prop(settings, modify_ui._field_name(ui, provider, field))
    actions = layout.box()
    preview = actions.row(); preview.scale_y = 1.2
    preview.operator("asset_assistant.modify_preview", text="Preview Changes", icon="PREVIEW_RANGE")
    apply_row = actions.row(); apply_row.scale_y = 1.45
    apply_row.operator("asset_assistant.modify_apply", text="Apply Changes", icon="CHECKMARK")
    actions.label(text="Ownership is re-checked before anything changes.")
    status = context.scene.get(modify_ui._STATUS_KEY)
    summary = context.scene.get(modify_ui._SUMMARY_KEY, "")
    if status or summary:
        report = layout.box()
        report.label(text="CHANGE REVIEW", icon="INFO")
        if status:
            report.label(text=status.replace("_", " ").title())
        for line in str(summary).splitlines():
            report.label(text=line, icon="ERROR" if line.startswith("Blocked:") else "NONE")
    advanced = layout.box()
    advanced.prop(settings, "asset_assistant_modify_advanced", text="Advanced / External Edit", toggle=True)
    if settings.asset_assistant_modify_advanced:
        advanced.label(text="Portable handoff for external tools or assisted editing")
        advanced.operator("asset_assistant.modify_export_inspection", text="Export Inspection File", icon="EXPORT")
        advanced.operator("asset_assistant.modify_import_request", text="Import Change File", icon="IMPORT")
        advanced.operator("asset_assistant.modify_apply_imported", text="Apply Imported Changes", icon="CHECKMARK")
        imported_path = context.scene.get(modify_ui._IMPORTED_PATH_KEY)
        if imported_path:
            advanced.label(text="Loaded: " + Path(imported_path).name)


def _draw_asset_type_picker(layout, settings, ui):
    box = layout.box()
    box.label(text="BASE ASSET", icon="OBJECT_DATA")
    rows = (("human_experimental", "quadruped"), ("avian", "box"))
    for keys in rows:
        row = box.row(align=True); row.scale_y = 1.25
        for key in keys:
            provider = ui.get_provider(key)
            row.prop_enum(settings, "object_type", key, text=provider.label)
    return box


def _draw_create(panel, context, ui, modify_ui, working_asset_ui):
    settings = context.scene.humanoid_settings
    tabs = panel.layout.row(align=True); tabs.scale_y = 1.2
    tabs.prop(settings, "asset_assistant_create_view", expand=True)
    panel.layout.separator()
    if settings.asset_assistant_create_view == "GENERATE":
        _section_header(panel.layout, "BUILD A NEW ASSET", "Pick a base, shape it, then generate", "OUTLINER_OB_MESH")
        _draw_asset_type_picker(panel.layout, settings, ui)
        provider = ui.get_provider(settings.object_type)
        params = panel.layout.box()
        params.label(text="SHAPE & PROPORTIONS", icon="PREFERENCES")
        for field in provider.parameters:
            params.prop(settings, ui._field_name(provider, field))
        action = panel.layout.row(); action.scale_y = 1.65
        action.operator("humanoid.generate_blockout", text="Generate " + provider.label, icon="ADD")
        panel.layout.label(text="Creates a new editable Asset Assistant model.")
        if working_asset_ui is not None:
            panel.layout.separator()
            resume = panel.layout.box()
            _section_header(resume, "CONTINUE EXISTING", "Resume an editable Asset Assistant checkpoint", "FILE_FOLDER")
            row = resume.row(); row.scale_y = 1.15
            row.operator("asset_assistant.open_editable_checkpoint", text="Open Editable Checkpoint", icon="FILE_FOLDER")
        return
    if settings.asset_assistant_create_view == "MODIFY":
        _section_header(panel.layout, "MODIFY ASSET", "Adjust the current asset without exposing the plumbing", "MODIFIER")
        _draw_artist_modify(panel, context, ui, modify_ui)
        return
    _section_header(panel.layout, "RIG & POSE", "Prepare the current asset for animation", "ARMATURE_DATA")
    ui._WorkflowPanel.draw(_stage_proxy(panel, "RIGGING"), context)


def _draw_animate(panel, context, ui, animation_names_ui, animation_adoption_ui):
    _section_header(panel.layout, "ANIMATION", "Create, preview and manage clips", "ACTION")
    ui._WorkflowPanel.draw(_stage_proxy(panel, "ANIMATION"), context)
    target = getattr(context.scene.humanoid_settings, "target", None)
    if target is not None:
        panel.layout.separator()
        clip_box = panel.layout.box(); clip_box.label(text="CLIP LIBRARY", icon="ACTION")
        animation_names_ui.ASSET_ASSISTANT_PT_animation_names.draw(type("ClipLibraryProxy", (), {"layout": clip_box})(), context)
    if animation_adoption_ui is not None:
        panel.layout.separator(); _draw_animation_adoption(panel.layout.box(), target)


def _draw_components(panel, context, component_adoption_ui, hair_component_ui, clothing_component_ui, self_rigged_accessory):
    layout = panel.layout; settings = context.scene.humanoid_settings
    _section_header(layout, "PARTS & COMPONENTS", "Hair, clothing, accessories and imported pieces", "OUTLINER_COLLECTION")
    target_box = layout.box(); target_box.prop(settings, "target", text="Asset")
    target = getattr(settings, "target", None)
    _draw_component_actions(layout, target, hair_component_ui, clothing_component_ui, self_rigged_accessory)


def _draw_export(panel, context, ui, working_asset_ui):
    layout = panel.layout; settings = context.scene.humanoid_settings
    _section_header(layout, "EXPORT", "Validate once, then ship to your target", "EXPORT")
    target_box = layout.box(); target_box.prop(settings, "target", text="Asset")
    target = getattr(settings, "target", None)
    if target is None:
        layout.label(text="Create or choose an asset first.", icon="INFO"); return
    setup = layout.box(); setup.label(text="DESTINATION", icon="EXPORT"); setup.prop(settings, "output_target")
    if settings.output_target == "CURA": setup.label(text="STL • current pose • millimetres • one solid")
    else:
        setup.prop(settings, "asset_use"); setup.prop(settings, "require_textures")
    validation = layout.box(); validation.label(text="READINESS", icon="CHECKMARK")
    if settings.output_target != "CURA": validation.operator("humanoid.prepare_materials", text="Add Missing Materials", icon="MATERIAL")
    action = validation.row(); action.scale_y = 1.2; action.operator("humanoid.validate_character", text="Run Validation", icon="CHECKMARK")
    snapshot = settings.validation_results
    if snapshot:
        errors = sum(row.status == "ERROR" for row in snapshot); warnings = sum(row.status == "WARN" for row in snapshot); passes = sum(row.status == "PASS" for row in snapshot)
        validation.label(text=f"{errors} errors  •  {warnings} warnings  •  {passes} passed", icon="CHECKMARK" if errors == 0 else "ERROR")
        ui._draw_validation_results(validation, snapshot, max(24, int(context.region.width / 7) - 6))
    else: validation.label(text="Run validation to check readiness.", icon="INFO")
    readiness_rows = snapshot if settings.output_target == "CURA" else ui._export_issues(context)
    ready = ui.is_ready(readiness_rows)
    confidence = layout.box(); confidence.label(text="READY TO EXPORT" if ready else "NOT READY YET", icon="CHECKMARK" if ready else "ERROR")
    export_row = confidence.row(); export_row.scale_y = 1.6; export_row.enabled = ready
    export_row.operator("humanoid.export_asset", text="Export Asset", icon="EXPORT")
    if settings.last_export: confidence.label(text="Saved: " + settings.last_export, icon="CHECKMARK")
    if working_asset_ui is not None:
        checkpoint = layout.box(); checkpoint.label(text="EDITABLE WORKING STATE", icon="FILE_BLEND")
        checkpoint.operator("asset_assistant.save_editable_checkpoint", text="Validate + Save Checkpoint", icon="FILE_TICK")


def _draw_workspace_nav(layout, settings):
    top = layout.row(align=True); top.scale_y = 1.25
    top.prop_enum(settings, "asset_assistant_workspace", "CREATE", text="Create")
    top.prop_enum(settings, "asset_assistant_workspace", "ANIMATE", text="Animate")
    bottom = layout.row(align=True); bottom.scale_y = 1.25
    bottom.prop_enum(settings, "asset_assistant_workspace", "COMPONENTS", text="Components")
    bottom.prop_enum(settings, "asset_assistant_workspace", "EXPORT", text="Export")


def _draw_workspace(panel, context, presentation_registry, ui, modify_ui, animation_names_ui, working_asset_ui, component_adoption_ui, hair_component_ui, clothing_component_ui, animation_adoption_ui, self_rigged_accessory):
    layout = panel.layout; settings = context.scene.humanoid_settings
    presentation_registry.resolve("shared.workspace_navigation", _draw_workspace_nav)(layout, settings)
    layout.separator(factor=0.5)
    presentation_registry.resolve("shared.asset_summary", _asset_summary)(layout, context)
    layout.separator()
    if settings.asset_assistant_workspace == "CREATE":
        presentation_registry.resolve("workspace.create", _draw_create)(panel, context, ui, modify_ui, working_asset_ui)
    elif settings.asset_assistant_workspace == "ANIMATE":
        presentation_registry.resolve("workspace.animate", _draw_animate)(panel, context, ui, animation_names_ui, animation_adoption_ui)
    elif settings.asset_assistant_workspace == "COMPONENTS":
        presentation_registry.resolve("workspace.components", _draw_components)(panel, context, component_adoption_ui, hair_component_ui, clothing_component_ui, self_rigged_accessory)
    else:
        presentation_registry.resolve("workspace.export", _draw_export)(panel, context, ui, working_asset_ui)


def _hide_legacy_panel(panel_type):
    def poll(_cls, _context): return False
    panel_type.poll = classmethod(poll)


def prepare(presentation_registry, ui, modify_ui, animation_names_ui, working_asset_ui=None, component_adoption_ui=None, hair_component_ui=None, clothing_component_ui=None, animation_adoption_ui=None, self_rigged_accessory=None):
    annotations = ui.HUMANOID_PG_settings.__annotations__
    if "asset_assistant_workspace" not in annotations:
        annotations["asset_assistant_workspace"] = ui.EnumProperty(name="Workspace", default="CREATE", items=[("CREATE", "Create", "Create, modify or rig an asset"), ("ANIMATE", "Animate", "Create, preview and manage animation clips"), ("COMPONENTS", "Components", "Manage components, hair, clothing and accessories"), ("EXPORT", "Export", "Validate and export for a target application")])
    if "asset_assistant_create_view" not in annotations:
        annotations["asset_assistant_create_view"] = ui.EnumProperty(name="Create View", default="GENERATE", items=[("GENERATE", "Generate", "Create a new base asset"), ("MODIFY", "Modify", "Safely modify the current asset"), ("RIG", "Rig", "Rig or pose the current asset")])
    if "asset_assistant_modify_advanced" not in annotations:
        annotations["asset_assistant_modify_advanced"] = ui.BoolProperty(name="Advanced / External Edit", default=False)
    ui.HUMANOID_PT_panel.bl_label = "Asset Assistant"; ui.HUMANOID_PT_panel.bl_category = _CATEGORY; ui.HUMANOID_PT_panel.bl_order = 0
    ui.HUMANOID_PT_panel.bl_options = set(getattr(ui.HUMANOID_PT_panel, "bl_options", set())) - {"DEFAULT_CLOSED"}
    def draw_workspace(panel, context):
        _draw_workspace(panel, context, presentation_registry, ui, modify_ui, animation_names_ui, working_asset_ui, component_adoption_ui, hair_component_ui, clothing_component_ui, animation_adoption_ui, self_rigged_accessory)
    draw_workspace._asset_assistant_workspace = True; ui.HUMANOID_PT_panel.draw = draw_workspace
    legacy_panels = (modify_ui.ASSET_ASSISTANT_PT_modify, ui.HUMANOID_PT_rigging, ui.HUMANOID_PT_animations, ui.HUMANOID_PT_validation, ui.HUMANOID_PT_export, animation_names_ui.ASSET_ASSISTANT_PT_animation_names)
    for order, legacy in enumerate(legacy_panels, start=1):
        legacy.bl_category = _CATEGORY; legacy.bl_order = order; _hide_legacy_panel(legacy)
