# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from object_core.modification import AssetSnapshot, ModificationRequest, plan_modification


class ModifyEnumChoiceTests(unittest.TestCase):
    def _snapshot(self):
        return AssetSnapshot(
            asset_id="asset-123",
            provider_key="human",
            provider_label="Human",
            parameters=(
                ("height_cm", 180),
                ("weight_kg", 95),
                ("body_type", "average"),
            ),
            owns_geometry=True,
        )

    def test_accepts_serialized_choice_value_from_provider_enum(self):
        plan = plan_modification(
            self._snapshot(),
            ModificationRequest(parameter_changes=(("body_type", "slim"),)),
        )

        self.assertEqual((("body_type", "slim"),), plan.requested_parameter_changes)
        self.assertTrue(plan.safe_to_apply)

    def test_rejects_unknown_choice_value(self):
        with self.assertRaisesRegex(ValueError, "Body Type is not an allowed choice"):
            plan_modification(
                self._snapshot(),
                ModificationRequest(parameter_changes=(("body_type", "not-a-body-type"),)),
            )


if __name__ == "__main__":
    unittest.main()
