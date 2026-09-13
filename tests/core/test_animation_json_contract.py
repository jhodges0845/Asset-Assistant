# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from blender_adapter.animation_json_contract import enhance_context_payload


class AnimationJsonContractTests(unittest.TestCase):
    def test_context_teaches_llm_coordinate_and_return_contract(self):
        payload = {
            "schema": "asset_assistant.animation_context.v1",
            "instructions": {},
            "rig": {
                "signature": "rig-123",
                "bones": [
                    {"name": "hips", "parent": None},
                    {"name": "spine", "parent": "hips"},
                ],
            },
            "scene": {"fps": 30.0, "scale_length": 1.0},
            "reference_animation": None,
        }

        result = enhance_context_payload(payload, addon_version=(1, 2, 3))

        self.assertEqual("Asset Assistant", result["asset_assistant"]["product"])
        self.assertEqual("1.2.3", result["asset_assistant"]["addon_version"])
        self.assertEqual("-Y", result["coordinate_conventions"]["character_forward_axis"])
        self.assertEqual("+Z", result["coordinate_conventions"]["world_up_axis"])
        self.assertEqual(["hips", "spine"], result["authoring_contract"]["allowed_bones"])
        self.assertIn("-Y", result["authoring_contract"]["movement_semantics"]["forward_lean"])
        self.assertEqual("rig-123", result["return_schema_example"]["target"]["rig_signature"])
        self.assertEqual(30.0, result["return_schema_example"]["clip"]["fps"])
        self.assertIn("hips", result["return_schema_example"]["keyframes"][0]["bones"])
        self.assertEqual("IN_PLACE", result["instructions"]["root_motion_default"])

    def test_contract_requires_json_only_and_no_invented_bones(self):
        result = enhance_context_payload({
            "instructions": {},
            "rig": {"signature": "x", "bones": [{"name": "root"}]},
            "scene": {"fps": 24.0},
        })

        self.assertIn("JSON only", result["instructions"]["read_first"])
        rules = " ".join(result["authoring_contract"]["rules"])
        self.assertIn("invent bones", rules)
        self.assertIn("in-place", rules)


if __name__ == "__main__":
    unittest.main()
