# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import patch

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

import blender_adapter.modify_fastpath as modify_fastpath
import blender_adapter.modify_ui as modify_ui
from blender_adapter.adapter import create_character
from object_core.modification import ModificationRequest, SemanticOperation
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class ImportedModifyFastPathTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        for collection in tuple(bpy.data.collections):
            if collection.users == 0:
                bpy.data.collections.remove(collection)
        modify_fastpath.install(modify_ui)

    def _human(self):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        root = create_character(provider.mesh(values), name=provider.label, scene=bpy.context.scene)
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root

    def test_supplied_import_snapshot_skips_duplicate_helper_inspection(self):
        root = self._human()
        snapshot = modify_ui.inspect_generated_asset(root)
        request = ModificationRequest(
            semantic_operations=(
                SemanticOperation(
                    "shape",
                    "jaw",
                    (("profile", "tapered"), ("amount", 0.5)),
                ),
            ),
        )

        with patch.object(
            modify_ui,
            "inspect_generated_asset",
            wraps=modify_ui.inspect_generated_asset,
        ) as inspect_asset:
            result = modify_ui._apply_external_request(
                bpy.context,
                root,
                request,
                snapshot=snapshot,
            )

        self.assertTrue(result.owns_geometry)
        self.assertEqual(0, inspect_asset.call_count)
        self.assertEqual("jaw", result.semantic_operations[-1].target)

    def test_standalone_helper_still_inspects_when_snapshot_is_not_supplied(self):
        root = self._human()
        request = ModificationRequest(
            semantic_operations=(
                SemanticOperation(
                    "shape",
                    "jaw",
                    (("profile", "tapered"), ("amount", 0.5)),
                ),
            ),
        )

        with patch.object(
            modify_ui,
            "inspect_generated_asset",
            wraps=modify_ui.inspect_generated_asset,
        ) as inspect_asset:
            result = modify_ui._apply_external_request(bpy.context, root, request)

        self.assertTrue(result.owns_geometry)
        self.assertEqual(1, inspect_asset.call_count)


if __name__ == "__main__":
    unittest.main()
