# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle, add_locomotion, generated_action
from blender_adapter.animation_records import animation_record, inspect_animation_record
from blender_adapter.animation_tuning import (
    REQUEST_SCHEMA,
    animation_inspection_document,
    apply_animation_request,
    preview_animation_request,
)
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderAnimationTuningTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ("objects", "meshes", "armatures", "collections", "materials", "images", "actions")}

    def tearDown(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.window.scene = self.previous_scene
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)

    def _human(self):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        root = create_character(
            mesh,
            name="TuningHuman",
            scene=bpy.context.scene,
            skeleton=provider.skeleton(values),
            skin_weights=provider.skin_weights(mesh, values),
        )
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root

    def _request(self, root, animation_id, **changes):
        document = {
            "schema": REQUEST_SCHEMA,
            "asset_id": str(root["asset_assistant_asset_id"]),
            "provider_key": "human",
            "operations": [{"animation_id": animation_id}],
        }
        document["operations"][0].update(changes)
        return document

    def test_inspection_exposes_reproducible_duration_and_strength(self):
        root = self._human()
        action, _ = add_idle(root, bpy.context.scene, duration=2.5, strength=1.25)

        document = animation_inspection_document(root)
        item = document["animations"][0]

        self.assertEqual(animation_record(action).animation_id, item["animation_id"])
        self.assertEqual("Idle", item["clip_id"])
        self.assertTrue(item["tunable"])
        self.assertAlmostEqual(2.5, item["duration_seconds"])
        self.assertAlmostEqual(1.25, item["strength"])
        self.assertEqual(["duration_seconds", "strength", "export_name"], item["supported_changes"])

    def test_preview_validates_without_mutating_action(self):
        root = self._human()
        action, _ = add_idle(root, bpy.context.scene, duration=2.0, strength=0.8)
        original_range = tuple(action.frame_range)
        original_id = animation_record(action).animation_id

        plan = preview_animation_request(
            root,
            self._request(root, original_id, duration_seconds=1.4, strength=1.3),
        )

        self.assertEqual(original_id, plan["animation_id"])
        self.assertAlmostEqual(1.4, plan["duration_seconds"])
        self.assertAlmostEqual(1.3, plan["strength"])
        self.assertEqual(original_range, tuple(action.frame_range))
        self.assertEqual(original_id, animation_record(action).animation_id)

    def test_apply_regenerates_owned_clip_and_preserves_stable_identity(self):
        root = self._human()
        idle, _ = add_idle(root, bpy.context.scene, duration=2.0, strength=0.8)
        walk, _ = add_locomotion(root, bpy.context.scene, duration=1.2, strength=1.0)
        old_idle_name = idle.name
        idle_id = animation_record(idle).animation_id
        walk_id = animation_record(walk).animation_id

        result = apply_animation_request(
            root,
            bpy.context.scene,
            self._request(
                root,
                idle_id,
                duration_seconds=1.5,
                strength=1.4,
                export_name="Maxine Idle",
            ),
        )

        tuned = generated_action(root, "Idle")
        preserved_walk = generated_action(root, "Walk")
        self.assertIsNotNone(tuned)
        self.assertIsNotNone(preserved_walk)
        self.assertEqual(idle_id, result.animation_id)
        self.assertEqual(idle_id, inspect_animation_record(root, tuned).animation_id)
        self.assertEqual(walk_id, inspect_animation_record(root, preserved_walk).animation_id)
        self.assertEqual("Maxine Idle", tuned["asset_assistant_export_name"])
        self.assertAlmostEqual(1.4, tuned["asset_assistant_animation_strength"])
        self.assertAlmostEqual(1.5, (result.frame_end - result.frame_start) / result.fps)
        self.assertEqual(old_idle_name, tuned.name)
        self.assertEqual(2, len([action for action in bpy.data.actions if action.get("asset_assistant_generated")]))

    def test_invalid_request_is_rejected_before_mutation(self):
        root = self._human()
        action, _ = add_idle(root, bpy.context.scene, duration=2.0, strength=1.0)
        animation_id = animation_record(action).animation_id
        action_count = len(bpy.data.actions)

        with self.assertRaisesRegex(ValueError, "between 0.1 and 2.0"):
            apply_animation_request(
                root,
                bpy.context.scene,
                self._request(root, animation_id, strength=5.0),
            )

        self.assertEqual(action_count, len(bpy.data.actions))
        self.assertIs(action, generated_action(root, "Idle"))
        self.assertEqual(animation_id, animation_record(action).animation_id)


if __name__ == "__main__":
    unittest.main()
