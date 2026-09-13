# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from blender_adapter.model_json_contract import enhance_inspection_document
from object_core.modify_exchange import inspection_document
from object_core.modification import AssetSnapshot, SemanticOperation


class ModelJsonContractTests(unittest.TestCase):
    def _snapshot(self, semantic_operations=()):
        return AssetSnapshot(
            asset_id="asset-123",
            provider_key="human_experimental",
            provider_label="Human",
            parameters=(("height_cm", 180), ("weight_kg", 95), ("body_type", "average")),
            semantic_operations=semantic_operations,
            owns_geometry=True,
            has_rig=True,
            owns_rig=True,
            has_materials=True,
            owns_materials=True,
            has_animations=False,
            owns_animations=False,
        )

    def test_contract_teaches_llm_exact_safe_vocabulary(self):
        payload = enhance_inspection_document(inspection_document(self._snapshot()), addon_version=(0, 9, 0))

        self.assertEqual("Asset Assistant", payload["asset_assistant"]["product"])
        self.assertEqual("asset-assistant.modify-request/v3", payload["asset_assistant"]["return_schema"])
        self.assertEqual("asset-123", payload["return_schema_example"]["asset_id"])
        self.assertEqual("human_experimental", payload["return_schema_example"]["provider_key"])

        parameters = {row["key"]: row for row in payload["parameter_contract"]}
        self.assertEqual(180, parameters["height_cm"]["current"])
        self.assertEqual(120, parameters["height_cm"]["minimum"])
        self.assertEqual(240, parameters["height_cm"]["maximum"])
        self.assertIn("average", parameters["body_type"]["choices"])

        semantics = {target["key"]: target for target in payload["semantic_vocabulary"]["targets"]}
        self.assertIn("shoulders", semantics)
        shoulder_scale = semantics["shoulders"]["operation_contracts"]["scale"]
        self.assertEqual(0.1, shoulder_scale["arguments"]["x"]["minimum"])
        self.assertEqual(4.0, shoulder_scale["arguments"]["x"]["maximum"])
        face_shape = semantics["face"]["operation_contracts"]["shape"]
        self.assertEqual(["narrow", "defined"], face_shape["arguments"]["profile"]["values"])

        self.assertIn("CURRENT_ASSET_RELATIVE", payload["instructions"]["reference_authority"])
        self.assertIn("Do not invent semantic target names", " ".join(payload["model_authoring_contract"]["rules"]))

    def test_contract_describes_current_semantic_model_state(self):
        semantic = SemanticOperation("shape", "face", (("profile", "defined"), ("amount", 0.5)))
        payload = enhance_inspection_document(
            inspection_document(self._snapshot((semantic,))),
            addon_version=(0, 9, 0),
        )

        state = payload["model_state"]
        self.assertEqual("centimeters", state["units"])
        self.assertGreater(state["overall"]["shoulder_width_cm"], 0.0)
        self.assertGreater(state["overall"]["hip_width_cm"], 0.0)
        self.assertGreater(state["regions"]["shoulders"]["shoulder_to_hip_ratio"], 0.0)
        self.assertEqual("defined", state["regions"]["face"]["shape_profile"])

    def test_return_example_uses_real_supported_values(self):
        payload = enhance_inspection_document(inspection_document(self._snapshot()))
        semantic = payload["return_schema_example"]["semantic_operations"]
        self.assertTrue(semantic)
        operation = semantic[0]
        self.assertNotEqual("REPLACE_WITH_SUPPORTED_PROFILE", operation["arguments"].get("profile"))

    def test_contract_does_not_mutate_portable_document(self):
        original = inspection_document(self._snapshot())
        enhance_inspection_document(original)
        self.assertNotIn("asset_assistant", original)
        self.assertNotIn("model_authoring_contract", original)


if __name__ == "__main__":
    unittest.main()
