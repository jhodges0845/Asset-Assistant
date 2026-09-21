# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation_json_ui import (
    _ANIMATION_SCHEMA,
    _rig_signature,
    create_action_from_payload,
    validate_animation_payload,
)
from blender_adapter.animation_records import animation_record
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class AnimationJsonUiTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ("objects", "meshes", "armatures", "collections", "materials", "images", "actions")}

    def tearDown(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
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
            name="AnimationJsonHuman",
            scene=bpy.context.scene,
            skeleton=provider.skeleton(values),
            skin_weights=provider.skin_weights(mesh, values),
        )
        root["object_type"] = provider.key
        rig = next(child for child in root.children if child.type == "ARMATURE")
        return root, rig

    def _payload(self, rig):
        bone = rig.pose.bones[0]
        return {
            "schema": _ANIMATION_SCHEMA,
            "target": {"rig_signature": _rig_signature(rig)},
            "clip": {"name": "LLM Test", "fps": 24, "looping": False},
            "keyframes": [
                {"frame": 1, "bones": {bone.name: {"rotation_quaternion": [1, 0, 0, 0]}}},
                {"frame": 12, "bones": {bone.name: {"rotation_quaternion": [0.999, 0.02, 0, 0]}}},
            ],
        }

    def test_validation_rejects_wrong_rig_signature(self):
        _, rig = self._rigged_human()
        payload = self._payload(rig)
        payload["target"]["rig_signature"] = "different-rig"
        with self.assertRaisesRegex(ValueError, "different rig"):
            validate_animation_payload(payload, rig)

    def test_create_action_from_llm_payload_creates_new_managed_action(self):
        root, rig = self._rigged_human()
        normalized = validate_animation_payload(self._payload(rig), rig)

        action = create_action_from_payload(root, rig, bpy.context.scene, normalized)

        self.assertEqual("LLM Test", action.name)
        self.assertIs(rig.animation_data.action, action)
        record = animation_record(action)
        self.assertEqual("LLM Test", record.display_name)
        self.assertEqual(24.0, record.fps)
        self.assertEqual(1, bpy.context.scene.frame_start)
        self.assertEqual(12, bpy.context.scene.frame_end)


if __name__ == "__main__":
    unittest.main()
