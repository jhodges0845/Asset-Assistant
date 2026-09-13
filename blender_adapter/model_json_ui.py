# SPDX-License-Identifier: GPL-3.0-or-later
"""First-class LLM model JSON workflow layered over the existing safe Modify exchange."""

import json
from pathlib import Path

from .model_json_contract import enhance_inspection_document


def _enhanced_inspection_json(original, snapshot, addon_version):
    document = json.loads(original(snapshot))
    enhanced = enhance_inspection_document(document, addon_version=addon_version)
    return json.dumps(enhanced, indent=2, sort_keys=True) + "\n"


def _draw_artist_modify(workflow_ui, modify_ui, ui, panel, context):
    """Keep manual Modify and make the LLM round-trip visible instead of hiding it as plumbing."""
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

    llm = layout.box()
    workflow_ui._section_header(
        llm,
        "LLM MODEL JSON",
        "Export this model's safe editing vocabulary, then import the LLM change file",
        "FILE_SCRIPT",
    )
    row = llm.row(align=True); row.scale_y = 1.25
    row.operator("asset_assistant.modify_export_inspection", text="Export Model Context JSON", icon="EXPORT")
    row.operator("asset_assistant.modify_import_request", text="Import Model Change JSON", icon="IMPORT")
    llm.label(text="The context file teaches the LLM the exact parameters, semantic targets and preservation rules.")
    imported_path = context.scene.get(modify_ui._IMPORTED_PATH_KEY)
    if imported_path:
        llm.label(text="Loaded: " + Path(imported_path).name, icon="FILE_TICK")
        apply_row = llm.row(); apply_row.scale_y = 1.35
        apply_row.operator("asset_assistant.modify_apply_imported", text="Apply Validated Model Changes", icon="CHECKMARK")
    llm.label(text="Import previews/validates first; apply re-checks ownership before mutation.")

    params = layout.box()
    workflow_ui._section_header(params, "MANUAL ADJUSTMENTS", "Tune provider values directly", "MODIFIER")
    for field in provider.parameters:
        params.prop(settings, modify_ui._field_name(ui, provider, field))

    actions = layout.box()
    preview = actions.row(); preview.scale_y = 1.2
    preview.operator("asset_assistant.modify_preview", text="Preview Manual Changes", icon="PREVIEW_RANGE")
    apply_row = actions.row(); apply_row.scale_y = 1.45
    apply_row.operator("asset_assistant.modify_apply", text="Apply Manual Changes", icon="CHECKMARK")
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


def install(modify_ui, workflow_ui, ui, addon_version=(0, 9, 0)):
    """Enhance the existing exchange format and promote it in Create > Modify."""
    original_json = modify_ui.inspection_json
    if not getattr(original_json, "_asset_assistant_model_llm", False):
        def inspection_json_with_contract(snapshot):
            return _enhanced_inspection_json(original_json, snapshot, addon_version)
        inspection_json_with_contract._asset_assistant_model_llm = True
        modify_ui.inspection_json = inspection_json_with_contract

    modify_ui.ASSET_ASSISTANT_OT_modify_export_inspection.bl_label = "Export Model Context JSON"
    modify_ui.ASSET_ASSISTANT_OT_modify_export_inspection.bl_description = (
        "Export a self-documenting model context JSON for an LLM to author safe model changes"
    )
    modify_ui.ASSET_ASSISTANT_OT_modify_import_request.bl_label = "Import Model Change JSON"
    modify_ui.ASSET_ASSISTANT_OT_modify_import_request.bl_description = (
        "Load and validate an LLM-authored Asset Assistant model change JSON without applying it"
    )
    modify_ui.ASSET_ASSISTANT_OT_modify_apply_imported.bl_label = "Apply Validated Model Changes"

    def draw_model_modify(panel, context):
        return _draw_artist_modify(workflow_ui, modify_ui, ui, panel, context)

    draw_model_modify._asset_assistant_model_llm = True
    workflow_ui._draw_artist_modify = draw_model_modify


__all__ = ["install"]
