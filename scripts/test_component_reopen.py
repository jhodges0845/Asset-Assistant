# SPDX-License-Identifier: GPL-3.0-or-later
"""Real .blend save/reopen smoke test for component and animation ownership."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import bpy

root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle
from blender_adapter.animation_records import animation_record, inspect_animation_record
from blender_adapter.components import inspect_component
from blender_adapter.self_rigged_accessory import create_self_rigged_gauntlet
from object_core.components import ComponentBehavior, RigBinding
from object_core.objects import get_provider


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


provider = get_provider("human")
values = {field.key: field.default for field in provider.parameters}
mesh = provider.mesh(values)
root = create_character(
    mesh,
    name="RoundTripHuman",
    scene=bpy.context.scene,
    skeleton=provider.skeleton(values),
    skin_weights=provider.skin_weights(mesh, values),
    materials=provider.materials(values),
)
root["object_type"] = provider.key
for key, value in values.items():
    root[key] = value

asset_id = root["asset_assistant_asset_id"]
idle, _ = add_idle(root, bpy.context.scene)
animation_id = animation_record(idle).animation_id
component_root, component = create_self_rigged_gauntlet(root, name="RoundTrip Gauntlet")
component_id = component.component_id
component_rig = next(child for child in component_root.children if child.type == "ARMATURE")
component_action = component_rig.animation_data.action
require(component_action is not None, "self-rigged component must own an active action before save")
require(component_action.get("asset_assistant_component_animation"), "component action ownership tag missing before save")

with TemporaryDirectory(prefix="asset-assistant-reopen-") as directory:
    checkpoint = Path(directory) / "component-roundtrip.blend"
    result = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
    require("FINISHED" in result and checkpoint.is_file(), "Blender did not write the round-trip checkpoint")

    # Prove the assertions below are reading the file rather than surviving memory.
    component_root.name = "MUTATED_AFTER_SAVE"
    del component_action["asset_assistant_component_animation"]

    result = bpy.ops.wm.open_mainfile(filepath=str(checkpoint))
    require("FINISHED" in result, "Blender did not reopen the round-trip checkpoint")

    roots = [obj for obj in bpy.data.objects if obj.get("asset_assistant_asset_id") == asset_id]
    require(len(roots) == 1, "base asset identity did not survive .blend reopen")
    reopened_root = roots[0]

    reopened_component = inspect_component(reopened_root, component_id)
    require(reopened_component.behavior == ComponentBehavior.SELF_RIGGED,
            "self-rigged behavior did not survive .blend reopen")
    require(reopened_component.owns_rig and reopened_component.rig_binding == RigBinding.OWNED,
            "component rig ownership did not survive .blend reopen")

    component_rigs = [
        obj for obj in bpy.data.objects
        if obj.type == "ARMATURE"
        and obj.get("asset_assistant_component_id") == component_id
        and obj.get("asset_assistant_component_rig")
    ]
    require(len(component_rigs) == 1, "component-owned armature did not survive .blend reopen")
    reopened_component_rig = component_rigs[0]
    reopened_component_action = reopened_component_rig.animation_data.action if reopened_component_rig.animation_data else None
    require(reopened_component_action is not None, "component action assignment did not survive .blend reopen")
    require(reopened_component_action.get("asset_assistant_component_id") == component_id,
            "component action identity did not survive .blend reopen")
    require(reopened_component_action.get("asset_assistant_component_animation"),
            "component action ownership did not survive .blend reopen")
    require(reopened_component_action.get("asset_assistant_component_animation_name") == "Flex",
            "component animation name did not survive .blend reopen")

    base_actions = [action for action in bpy.data.actions if action.get("asset_assistant_animation_id") == animation_id]
    require(len(base_actions) == 1, "base animation stable identity did not survive .blend reopen")
    reopened_animation = inspect_animation_record(reopened_root, base_actions[0])
    require(reopened_animation.animation_id == animation_id,
            "base animation record changed across .blend reopen")

print("Component reopen smoke test passed")
