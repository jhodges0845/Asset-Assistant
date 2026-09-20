# SPDX-License-Identifier: GPL-3.0-or-later

import tempfile
import unittest
from pathlib import Path

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter import ui
from blender_adapter.adapter import create_character
import blender_adapter.working_asset_ui as working_asset_ui
from blender_adapter.working_asset_ui import (
    open_editable_checkpoint,
    save_editable_checkpoint,
    validate_checkpoint_scene,
    validate_working_state,
)
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class EditableCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._registered_settings = False
        if not hasattr(bpy.types.Scene, "humanoid_settings"):
            bpy.utils.register_class(ui.HUMANOID_PG_result)
            bpy.utils.register_class(ui.HUMANOID_PG_settings)
            bpy.types.Scene.humanoid_settings = bpy.props.PointerProperty(type=ui.HUMANOID_PG_settings)
            cls._registered_settings = True

    @classmethod
    def tearDownClass(cls):
        if cls._registered_settings:
            del bpy.types.Scene.humanoid_settings
            bpy.utils.unregister_class(ui.HUMANOID_PG_settings)
            bpy.utils.unregister_class(ui.HUMANOID_PG_result)

    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        scene = bpy.context.scene
        for key in (
            "asset_assistant_working_state_kind",
            "asset_assistant_working_state_version",
            "asset_assistant_working_state_status",
            "asset_assistant_working_state_message",
        ):
            if key in scene:
                del scene[key]
        scene.humanoid_settings.target = None
        working_asset_ui._OPEN_EXPECTS_CHECKPOINT = False

    def _human(self):
        provider = get_provider("human_experimental")
        values = {field.key: field.default for field in provider.parameters}
        root = create_character(provider.mesh(values), name=provider.label, scene=bpy.context.scene)
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root

    def _external_import(self, capability="STATIC"):
        scene = bpy.context.scene
        group = "checkpoint-import-group"
        root = bpy.data.objects.new("ImportedAsset", None)
        mesh_data = bpy.data.meshes.new("ImportedAssetMesh")
        mesh_data.from_pydata(
            [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
            [],
            [(0, 1, 2)],
        )
        mesh = bpy.data.objects.new("ImportedMesh", mesh_data)
        scene.collection.objects.link(root)
        scene.collection.objects.link(mesh)
        root["asset_assistant_import_group"] = group
        root["asset_assistant_import_root"] = True
        root["asset_assistant_external_asset"] = True
        root["asset_assistant_source"] = "ADOPTED"
        root["asset_assistant_external_capability"] = capability
        mesh["asset_assistant_import_group"] = group
        return root, mesh

    def test_checkpoint_forces_blend_extension_and_saves_copy(self):
        calls = []

        def fake_save(**kwargs):
            calls.append(kwargs)
            return {"FINISHED"}

        filepath = save_editable_checkpoint("/tmp/hero.checkpoint", fake_save)

        expected = str(Path("/tmp/hero.blend"))
        self.assertEqual(expected, filepath)
        self.assertEqual([{"filepath": expected, "copy": True}], calls)

    def test_checkpoint_destination_rechecks_filesystem_after_file_is_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hero.checkpoint.blend"
            path.write_bytes(b"old checkpoint")

            normalized, exists = working_asset_ui._checkpoint_destination(path)
            self.assertEqual(str(path), normalized)
            self.assertTrue(exists)

            path.unlink()

            normalized, exists = working_asset_ui._checkpoint_destination(path)
            self.assertEqual(str(path), normalized)
            self.assertFalse(exists)

    def test_reset_checkpoint_dialog_discards_stale_overwrite_state(self):
        class _Operator:
            filepath = ""
            check_existing = True

        operator = _Operator()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reusable.checkpoint.blend"
            path.write_bytes(b"old checkpoint")
            working_asset_ui._reset_checkpoint_save_dialog(operator, path)
            self.assertTrue(operator.check_existing)

            path.unlink()
            operator.check_existing = True
            working_asset_ui._reset_checkpoint_save_dialog(operator, path)

            self.assertEqual(str(path), operator.filepath)
            self.assertFalse(operator.check_existing)

    def test_checkpoint_marks_saved_copy_but_restores_current_scene(self):
        scene = bpy.context.scene
        self._human()
        observed = []

        def fake_save(**kwargs):
            observed.append((
                scene.get("asset_assistant_working_state_kind"),
                scene.get("asset_assistant_working_state_version"),
            ))
            return {"FINISHED"}

        save_editable_checkpoint("/tmp/hero.blend", fake_save, scene)

        self.assertEqual([("asset-assistant-editable-checkpoint", 1)], observed)
        self.assertNotIn("asset_assistant_working_state_kind", scene)
        self.assertNotIn("asset_assistant_working_state_version", scene)
        self.assertEqual("READY", scene["asset_assistant_working_state_status"])

    def test_adopted_import_group_is_valid_editable_checkpoint_state(self):
        root, mesh = self._external_import()

        snapshots = validate_working_state(bpy.context.scene)

        self.assertEqual(1, len(snapshots))
        self.assertEqual("external", snapshots[0]["kind"])
        self.assertEqual(root, snapshots[0]["root"])
        self.assertEqual(1, snapshots[0]["meshes"])
        self.assertIsNone(mesh.parent)
        self.assertEqual("READY", bpy.context.scene["asset_assistant_working_state_status"])

    def test_reopened_imported_checkpoint_restores_external_target(self):
        scene = bpy.context.scene
        root, _mesh = self._external_import()
        scene["asset_assistant_working_state_kind"] = "asset-assistant-editable-checkpoint"
        scene["asset_assistant_working_state_version"] = 1
        scene.humanoid_settings.target = None

        snapshots = validate_checkpoint_scene(scene)

        self.assertEqual(1, len(snapshots))
        self.assertEqual(root, scene.humanoid_settings.target)
        self.assertEqual("READY", scene["asset_assistant_working_state_status"])

    def test_external_checkpoint_rejects_lost_import_boundary_mesh(self):
        root, mesh = self._external_import()
        del mesh["asset_assistant_import_group"]

        with self.assertRaisesRegex(ValueError, "no longer contains mesh geometry"):
            validate_working_state(bpy.context.scene)

    def test_working_state_requires_recognizable_asset_before_save(self):
        with self.assertRaisesRegex(ValueError, "requires at least one recognizable"):
            validate_working_state(bpy.context.scene)

    def test_checkpoint_rejects_incomplete_blender_save(self):
        with self.assertRaisesRegex(RuntimeError, "did not finish"):
            save_editable_checkpoint("/tmp/hero.blend", lambda **kwargs: {"CANCELLED"})

    def test_open_requires_blend_file_and_uses_open_mainfile_contract(self):
        calls = []
        with tempfile.NamedTemporaryFile(suffix=".blend") as checkpoint:
            filepath = open_editable_checkpoint(
                checkpoint.name,
                lambda **kwargs: calls.append(kwargs) or {"FINISHED"},
            )
        self.assertTrue(filepath.endswith(".blend"))
        self.assertEqual([{"filepath": filepath}], calls)

    def test_reopened_checkpoint_revalidates_asset_and_restores_single_target(self):
        scene = bpy.context.scene
        root = self._human()
        scene["asset_assistant_working_state_kind"] = "asset-assistant-editable-checkpoint"
        scene["asset_assistant_working_state_version"] = 1

        snapshots = validate_checkpoint_scene(scene)

        self.assertEqual(1, len(snapshots))
        self.assertEqual(root.get("asset_assistant_asset_id"), snapshots[0].asset_id)
        self.assertEqual(root, scene.humanoid_settings.target)
        self.assertEqual("READY", scene["asset_assistant_working_state_status"])

    def test_native_blender_load_validates_marked_checkpoint(self):
        scene = bpy.context.scene
        root = self._human()
        scene["asset_assistant_working_state_kind"] = "asset-assistant-editable-checkpoint"
        scene["asset_assistant_working_state_version"] = 1
        scene.humanoid_settings.target = None

        working_asset_ui._validate_reopened_checkpoint(None)

        self.assertEqual(root, scene.humanoid_settings.target)
        self.assertEqual("READY", scene["asset_assistant_working_state_status"])

    def test_native_blender_load_ignores_ordinary_unmarked_file(self):
        scene = bpy.context.scene

        working_asset_ui._validate_reopened_checkpoint(None)

        self.assertNotIn("asset_assistant_working_state_status", scene)
        self.assertNotIn("asset_assistant_working_state_message", scene)

    def test_reopen_validation_rejects_unmarked_blend_scene(self):
        with self.assertRaisesRegex(ValueError, "not marked"):
            validate_checkpoint_scene(bpy.context.scene)


if __name__ == "__main__":
    unittest.main()
