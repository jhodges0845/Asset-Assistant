# SPDX-License-Identifier: GPL-3.0-or-later

import json
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle, set_clip_export_name
from blender_adapter.animation_records import animation_record, inspect_animation_record
from object_core.animations import AnimationSource, RootMotionIntent
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderAnimationRecordTests(unittest.TestCase):
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

    def _rigged_human(self):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        root = create_character(
            mesh,
            name="Human",
            scene=bpy.context.scene,
            skeleton=provider.skeleton(values),
            skin_weights=provider.skin_weights(mesh, values),
        )
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root, provider

    def test_generated_idle_persists_first_class_record(self):
        root, provider = self._rigged_human()
        action, _ = add_idle(root, bpy.context.scene, duration=2.0, strength=1.0)

        record = inspect_animation_record(root, action)

        self.assertTrue(record.animation_id.startswith("animation-"))
        self.assertEqual("Idle", record.display_name)
        self.assertEqual("Idle", record.export_name)
        self.assertEqual(AnimationSource.GENERATED, record.source)
        self.assertEqual(provider.key, record.provider_key)
        self.assertEqual("idle", record.capability)
        self.assertTrue(record.looping)
        self.assertEqual(RootMotionIntent.IN_PLACE, record.root_motion)
        self.assertTrue(record.owns_curves)
        self.assertAlmostEqual(
            bpy.context.scene.render.fps / bpy.context.scene.render.fps_base,
            record.fps,
        )

    def test_export_name_change_updates_portable_record(self):
        root, _ = self._rigged_human()
        action, _ = add_idle(root, bpy.context.scene)
        animation_id = animation_record(action).animation_id

        set_clip_export_name(root, "Idle", "Breathing Idle")

        record = inspect_animation_record(root, action)
        self.assertEqual(animation_id, record.animation_id)
        self.assertEqual("Breathing Idle", record.export_name)
        self.assertEqual("Breathing Idle", action["asset_assistant_export_name"])

    def test_record_export_name_tampering_is_detected(self):
        root, _ = self._rigged_human()
        action, _ = add_idle(root, bpy.context.scene)
        action["asset_assistant_export_name"] = "Tampered"

        with self.assertRaisesRegex(ValueError, "export name"):
            inspect_animation_record(root, action)

    def test_rig_signature_tampering_is_detected(self):
        root, _ = self._rigged_human()
        action, _ = add_idle(root, bpy.context.scene)
        document = json.loads(action["asset_assistant_animation_record"])
        document["rig_signature"] = "sha256:not-the-current-rig"
        action["asset_assistant_animation_record"] = json.dumps(document, sort_keys=True)

        with self.assertRaisesRegex(ValueError, "rig signature"):
            inspect_animation_record(root, action)

    def test_legacy_generated_action_without_record_can_still_be_renamed(self):
        root, _ = self._rigged_human()
        rig = next(child for child in root.children if child.type == "ARMATURE")
        action = bpy.data.actions.new("Legacy Idle")
        action["asset_assistant_generated"] = True
        action["asset_assistant_rig"] = rig.name
        if rig.get("asset_assistant_rig_id"):
            action["asset_assistant_rig_id"] = rig["asset_assistant_rig_id"]
        action["asset_assistant_clip"] = "Idle"
        action["asset_assistant_export_name"] = "Idle"

        set_clip_export_name(root, "Idle", "Legacy Idle Export")

        self.assertEqual("Legacy Idle Export", action["asset_assistant_export_name"])
        self.assertNotIn("asset_assistant_animation_record", action)


if __name__ == "__main__":
    unittest.main()
