# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify animated exchange files are recognized after Blender imports them."""

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
from blender_adapter.targets import get_adapter, asset_objects, base_asset_rig
from blender_adapter.import_normalization import enroll_imported_working_asset
from blender_adapter.workflow import add_basic_rig
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class GLBImportRoundTripTests(unittest.TestCase):
    def prepare_asset(self):
        """Optional model edit before materials and clips are created."""

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
        self.prepare_asset()
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
        self._prove_exchange("GODOT", ".glb")

    def test_animated_gltf_reimport(self):
        self._prove_exchange("GODOT", ".gltf")

    def test_animated_unity_fbx_reimport(self):
        self._prove_exchange("UNITY", ".fbx")

    def test_animated_unreal_fbx_reimport(self):
        self._prove_exchange("UNREAL", ".fbx")

    def _prove_exchange(self, target, extension):
        path = Path(self.temp.name) / ("human" + extension)
        result = get_adapter(target, asset_use="ANIMATED").export(self.root, bpy.context, path)
        self.assertTrue(result.success, result.issues)

        imported_root = _import_external(str(path), extension, bpy.context)
        imported_clips = [(imported_root, None)]
        report = inspect_selected_asset(imported_root)

        self.assertEqual("REVIEW", report["status"])
        self.assertGreaterEqual(report["metrics"]["meshes"], 1)
        self.assertEqual(1, report["metrics"]["armatures"])
        self.assertGreaterEqual(report["metrics"]["materials"], 1)
        self.assertEqual(0 if target == "UNREAL" else 2, report["metrics"]["animations"])
        if target == "UNREAL":
            for clip in ("Idle", "Walk"):
                clip_path = path.with_name(path.stem + "_" + clip + extension)
                self.assertTrue(clip_path.is_file())
                clip_root = _import_external(str(clip_path), extension, bpy.context)
                imported_clips.append((clip_root, clip))
                clip_report = inspect_selected_asset(clip_root)
                self.assertEqual(1, clip_report["metrics"]["armatures"])
                self.assertEqual(1, clip_report["metrics"]["animations"])

        for candidate, _clip in imported_clips:
            objects = set(asset_objects(candidate))
            rig = base_asset_rig(candidate)
            self.assertIsNotNone(rig)
            transforms = {obj: obj.matrix_world.copy() for obj in objects}
            animation = rig.animation_data
            active = animation.action if animation else None
            strips = tuple((track, strip, strip.action, strip.frame_start,
                            strip.frame_end, strip.repeat, strip.influence)
                           for track in animation.nla_tracks for strip in track.strips) if animation else ()
            actions = set(bpy.data.actions)
            inspection = inspect_selected_asset(candidate)
            self.assertIs(enroll_imported_working_asset(bpy.context, inspection), candidate)
            self.assertEqual(actions, set(bpy.data.actions))
            self.assertEqual(active, rig.animation_data.action if rig.animation_data else None)
            after_strips = tuple((track, strip, strip.action, strip.frame_start,
                                  strip.frame_end, strip.repeat, strip.influence)
                                 for track in rig.animation_data.nla_tracks for strip in track.strips) if rig.animation_data else ()
            self.assertEqual(strips, after_strips)
            for obj in objects:
                self.assertEqual(transforms[obj], obj.matrix_world)
                self.assertEqual(objects, set(asset_objects(obj)))
                self.assertIs(base_asset_rig(obj), rig)
            self.assertEqual(inspection["metrics"], inspect_selected_asset(candidate)["metrics"])
            if target == "UNITY" and inspection["metrics"]["animations"]:
                reexport = Path(self.temp.name) / ("adopted-" + (_clip or "all") + ".glb")
                exported = get_adapter("GODOT", asset_use="ANIMATED").export(candidate, bpy.context, reexport)
                self.assertTrue(exported.success, exported.issues)
                self.assertEqual(actions, set(bpy.data.actions))
                self.assertIs(rig.animation_data.action, active)
                self.assertEqual(strips, tuple(
                    (track, strip, strip.action, strip.frame_start, strip.frame_end,
                     strip.repeat, strip.influence)
                    for track in rig.animation_data.nla_tracks for strip in track.strips))
                roundtrip = _import_external(str(reexport), ".glb", bpy.context)
                metrics = inspect_selected_asset(roundtrip)["metrics"]
                self.assertEqual(1, metrics["armatures"])
                self.assertEqual(inspection["metrics"]["animations"], metrics["animations"])
                self.assertEqual(inspection["metrics"]["meshes"], metrics["meshes"])

        return imported_clips


if __name__ == "__main__":
    unittest.main()
