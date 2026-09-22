# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression coverage for lightweight Blender UI readiness checks."""
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None


@unittest.skipIf(bpy is None, 'requires Blender; use scripts/test_blender.py')
class UIFastPathTests(unittest.TestCase):
    def setUp(self):
        import blender_adapter as addon
        self.addon = addon
        self.previous_scene = bpy.context.window.scene
        self.scene = bpy.data.scenes.new('UIFastPathTest')
        bpy.context.window.scene = self.scene
        addon.register()
        self.settings = self.scene.humanoid_settings
        self.settings.object_type = 'box'
        self.settings.box_width_cm = 10
        self.settings.box_depth_cm = 10
        self.settings.box_height_cm = 10
        bpy.ops.humanoid.generate_blockout()

    def tearDown(self):
        self.addon.unregister()
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)

    def test_generation_ui_hides_legacy_humanoid_provider(self):
        enum_items = type(self.settings).bl_rna.properties['object_type'].enum_items
        identifiers = {item.identifier for item in enum_items}
        self.assertNotIn('humanoid', identifiers)
        self.assertIn('human', identifiers)
        self.assertIn('quadruped', identifiers)
        self.assertIn('avian', identifiers)
        self.assertIn('box', identifiers)

    def test_export_poll_uses_snapshot_without_full_validation(self):
        from blender_adapter import ui
        original = ui._export_issues
        ui._export_issues = lambda context: (_ for _ in ()).throw(AssertionError('full validation during poll'))
        try:
            self.assertFalse(bpy.ops.humanoid.export_asset.poll())
            row = self.settings.validation_results.add()
            row.code, row.status, row.message = 'ready', 'PASS', 'Ready'
            self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        finally:
            ui._export_issues = original

    def test_header_attention_uses_snapshot_without_full_validation(self):
        from blender_adapter import ui
        original = ui._export_issues
        ui._export_issues = lambda context: (_ for _ in ()).throw(AssertionError('full validation during header draw'))
        try:
            self.assertFalse(ui._needs_attention(bpy.context, 'MODEL'))
            row = self.settings.validation_results.add()
            row.code, row.status, row.message = 'geometry', 'ERROR', 'Broken geometry'
            self.assertTrue(ui._needs_attention(bpy.context, 'MODEL'))
        finally:
            ui._export_issues = original
