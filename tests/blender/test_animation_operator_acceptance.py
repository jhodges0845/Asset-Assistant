# SPDX-License-Identifier: GPL-3.0-or-later
"""External animation refinement through registered Blender operators."""
import json
import bpy
import pytest
import blender_adapter as addon
from blender_adapter.adapter import create_character
from blender_adapter import animation as clips
from blender_adapter.animation_records import animation_record
from blender_adapter.animation_tuning import REQUEST_SCHEMA
from blender_adapter.animation_tuning_ui import _REQUEST_KEY, _PREVIEW_KEY
from object_core.objects import get_provider


def keys(action):
    return tuple((curve.data_path, curve.array_index,
                  tuple((tuple(key.co), tuple(key.handle_left), tuple(key.handle_right),
                         key.interpolation) for key in curve.keyframe_points))
                 for curve in clips.action_curves(action, action.slots[0]))


@pytest.mark.parametrize("provider_key", ["human", "quadruped", "avian"])
def test_external_animation_operators_all_clip_families(provider_key, tmp_path):
    previous = bpy.context.window.scene
    kinds = ("objects", "meshes", "armatures", "collections", "materials", "images", "actions")
    before = {kind: set(getattr(bpy.data, kind)) for kind in kinds}
    scene = bpy.data.scenes.new("Animation operator acceptance")
    bpy.context.window.scene = scene
    addon.register()
    try:
        provider = get_provider(provider_key)
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        root = create_character(mesh, scene=scene, skeleton=provider.skeleton(values),
                                skin_weights=provider.skin_weights(mesh, values))
        root["object_type"] = provider_key
        for name, value in values.items():
            root[name] = value
        scene.humanoid_settings.target = root
        bpy.context.view_layer.objects.active = root
        root.select_set(True)
        creators = [("Idle", clips.add_idle), ("Walk", clips.add_locomotion),
                    ("Flight", clips.add_flight) if provider_key == "avian" else ("Run", clips.add_run)]
        for _, create in creators:
            create(root, scene, duration=1.2)
        inspection = tmp_path / "inspection.json"
        assert bpy.ops.asset_assistant.export_animation_inspection(filepath=str(inspection)) == {"FINISHED"}
        exported = json.loads(inspection.read_text())
        assert {item["clip_id"] for item in exported["animations"]} == {name for name, _ in creators}
        request_path = tmp_path / "changes.json"
        for name, _ in creators:
            action = clips.generated_action(root, name)
            identity = animation_record(action).animation_id
            curve = clips.action_curves(action, action.slots[0])[0]
            curve.keyframe_points[1].co.y += .17
            original = keys(action)
            others = {other: (clips.generated_action(root, other), keys(clips.generated_action(root, other)))
                      for other, _ in creators if other != name}
            request = dict(schema=REQUEST_SCHEMA, asset_id=exported["asset"]["asset_id"],
                           provider_key=provider_key,
                           operations=[dict(animation_id=identity, export_name="Artist " + name)])
            request_path.write_text(json.dumps(request))
            assert bpy.ops.asset_assistant.import_animation_changes(filepath=str(request_path)) == {"FINISHED"}
            assert bpy.ops.asset_assistant.preview_animation_changes() == {"FINISHED"}
            assert keys(action) == original
            assert "keeps keyframes" in scene[_PREVIEW_KEY]
            assert bpy.ops.asset_assistant.apply_animation_changes() == {"FINISHED"}
            assert _REQUEST_KEY not in scene
            assert clips.generated_action(root, name) == action
            assert keys(action) == original
            assert animation_record(action).animation_id == identity
            assert animation_record(action).export_name == "Artist " + name
            request["operations"][0].update(duration_seconds=1.6, strength=.8)
            request_path.write_text(json.dumps(request))
            assert bpy.ops.asset_assistant.import_animation_changes(filepath=str(request_path)) == {"FINISHED"}
            assert bpy.ops.asset_assistant.preview_animation_changes() == {"FINISHED"}
            assert "regenerates keys" in scene[_PREVIEW_KEY]
            assert keys(action) == original
            assert bpy.ops.asset_assistant.apply_animation_changes() == {"FINISHED"}
            tuned = clips.generated_action(root, name)
            record = animation_record(tuned)
            assert record.animation_id == identity
            assert abs((record.frame_end - record.frame_start) / record.fps - 1.6) < .0001
            assert abs(tuned["asset_assistant_animation_strength"] - .8) < .0001
            for other, (preserved, snapshot) in others.items():
                assert clips.generated_action(root, other) == preserved
                assert keys(preserved) == snapshot
    finally:
        addon.unregister()
        bpy.context.window.scene = previous
        bpy.data.scenes.remove(scene)
        for kind in kinds:
            for item in set(getattr(bpy.data, kind)) - before[kind]:
                getattr(bpy.data, kind).remove(item, do_unlink=True)
