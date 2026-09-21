# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify a real exported GLB is recognized after Blender imports it."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle, add_locomotion
from blender_adapter.asset_file_import_ui import _import_external
from blender_adapter.asset_inspection_ui import inspect_selected_asset
from blender_adapter.materials import prepare_materials
from blender_adapter.targets import get_adapter
from blender_adapter.workflow import add_basic_rig
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class GLBImportRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ("objects", "meshes", "armatures", "collections", "materials", "images", "actions")}
        self.scene = bpy.data.scenes.new("GLBImportRoundTrip")
        bpy.context.window.scene = self.scene
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        self.root = create_character(provider.mesh(values), name="GLBHuman", scene=self.scene)
        self.root["object_type"] = provider.key
        for key, value in values.items():
            self.root[key] = value
        add_basic_rig(self.root, bpy.context)
        prepare_materials(self.root)
        add_idle(self.root, self.scene)
        add_locomotion(self.root, self.scene)
        self.temp = TemporaryDirectory()

    def tearDown(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                try:
                    data.remove(item, do_unlink=True)
                except TypeError:
                    data.remove(item)
        self.temp.cleanup()

    def test_exported_animated_glb_reimports_with_mesh_rig_material_and_clips(self):
        path = Path(self.temp.name) / "human.glb"
        result = get_adapter("GODOT", asset_use="ANIMATED").export(self.root, bpy.context, path)
        self.assertTrue(result.success, result.issues)

        imported_root = _import_external(str(path), ".glb", bpy.context)
        report = inspect_selected_asset(imported_root)

        self.assertEqual("REVIEW", report["status"])
        self.assertGreaterEqual(report["metrics"]["meshes"], 1)
        self.assertEqual(1, report["metrics"]["armatures"])
        self.assertGreaterEqual(report["metrics"]["materials"], 1)
        self.assertEqual(2, report["metrics"]["animations"])


if __name__ == "__main__":
    unittest.main()
