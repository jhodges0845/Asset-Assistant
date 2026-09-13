# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender adapter entry point. Importing this package does not require Blender."""

import sys

from . import core_gateway as core

sys.modules[__name__ + ".core"] = core

bl_info = {
    "name": "Asset Assistant", "author": "Asset Assistant contributors", "version": (0, 9, 0),
    "blender": (5, 2, 1), "location": "3D View > Sidebar > Asset Assistant",
    "description": "Generate, modify, rig, animate, validate, and export editable 3D assets", "category": "3D View",
}


def register():
    from . import (
        animation_adoption_ui, animation_artist_ui, animation_json_contract, animation_json_ui, animation_modify_exchange,
        animation_names_ui, animation_tuning_ui, asset_file_import_ui, asset_identity_ui, asset_inspection_ui, avian_ui,
        checkpoint_component_repair, clothing_component_ui, component_adoption_ui, component_modify_apply,
        component_modify_exchange, cura_scale_ui, generation_replace_ui, hair_component_ui, import_normalization,
        imported_rig_access, modification, modify_fastpath, modify_ui, normalized_import_workflow_ui, rig_animate_ui,
        run_ui, self_rigged_accessory, ui, ui_fastpath, workflow_ui, workspace_create_ui, workspace_nav_ui,
        working_asset_ui,
    )
    run_ui.prepare(ui); avian_ui.prepare(ui); animation_tuning_ui.prepare(ui)
    workspace_nav_ui.install(workflow_ui)
    workspace_create_ui.install(workflow_ui, ui, asset_inspection_ui, asset_file_import_ui)
    asset_identity_ui.install(workflow_ui)
    workflow_ui.prepare(ui, modify_ui, animation_names_ui, working_asset_ui, component_adoption_ui, hair_component_ui,
                        clothing_component_ui, animation_adoption_ui, self_rigged_accessory)
    animation_json_contract.install(animation_json_ui, bl_info["version"])
    animation_json_ui.install(animation_names_ui, animation_artist_ui)
    asset_inspection_ui.install(ui, workflow_ui, modify_ui); import_normalization.install(asset_file_import_ui)
    imported_rig_access.install(ui); normalized_import_workflow_ui.install(workflow_ui, asset_identity_ui, ui)
    rig_animate_ui.install(workflow_ui, workspace_create_ui, normalized_import_workflow_ui)
    checkpoint_component_repair.install(working_asset_ui); ui_fastpath.install(ui)
    animation_modify_exchange.install(modification, modify_ui); modify_fastpath.install(modify_ui)
    component_modify_exchange.install(modify_ui); component_modify_apply.install(modify_ui)
    ui.register(); imported_rig_access.register(); animation_names_ui.register(); animation_artist_ui.register(); animation_json_ui.register()
    animation_tuning_ui.register(); animation_adoption_ui.register(); generation_replace_ui.register()
    asset_inspection_ui.register(); asset_file_import_ui.register(); run_ui.register(ui.HUMANOID_PG_settings)
    cura_scale_ui.register(ui.HUMANOID_PG_settings); modify_ui.register(); working_asset_ui.register()
    component_adoption_ui.register(); hair_component_ui.register(); clothing_component_ui.register(); self_rigged_accessory.register()


def unregister():
    from . import (
        animation_adoption_ui, animation_artist_ui, animation_json_ui, animation_names_ui, animation_tuning_ui, asset_file_import_ui,
        asset_inspection_ui, clothing_component_ui, component_adoption_ui, cura_scale_ui, generation_replace_ui,
        hair_component_ui, imported_rig_access, modify_ui, run_ui, self_rigged_accessory, ui, working_asset_ui,
    )
    self_rigged_accessory.unregister(); clothing_component_ui.unregister(); hair_component_ui.unregister()
    component_adoption_ui.unregister(); working_asset_ui.unregister(); modify_ui.unregister()
    cura_scale_ui.unregister(ui.HUMANOID_PG_settings); run_ui.unregister(ui.HUMANOID_PG_settings)
    asset_file_import_ui.unregister(); asset_inspection_ui.unregister(); generation_replace_ui.unregister()
    animation_adoption_ui.unregister(); animation_tuning_ui.unregister(); animation_json_ui.unregister(); animation_artist_ui.unregister()
    animation_names_ui.unregister(); imported_rig_access.unregister(); ui.unregister()
