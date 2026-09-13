# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from blender_adapter.model_json_contract import enhance_inspection_document
from object_core.modify_exchange import inspection_document
from object_core.modification import AssetSnapshot


class ModelJsonContractTests(unittest.TestCase):
    def _snapshot(self):
        return AssetSnapshot(
            asset_id="asset-123",
            provider_key="human_experimental",
            provider_label="Human",
            parameters=(("height_cm", 180), ("weight_kg", 95), ("body_type", "average")),
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

        semantics = payload["semantic_vocabulary"]["targets"]
        self.assertTrue(any(target["key"] == "shoulders" for target in semantics))
        self.assertIn("CURRENT_ASSET_RELATIVE", payload["instructions"]["reference_authority"])
        self.assertIn("Do not invent semantic target names", " ".join(payload["model_authoring_contract"]["rules"]))

    def test_contract_does_not_mutate_portable_document(self):
        original = inspection_document(self._snapshot())
        enhance_inspection_document(original)
        self.assertNotIn("asset_assistant", original)
        self.assertNotIn("model_authoring_contract", original)


if __name__ == "__main__":
    unittest.main()
