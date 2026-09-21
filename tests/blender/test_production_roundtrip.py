# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import tempfile
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle
from blender_adapter.animation_records import animation_record
from blender_adapter.animation_tuning import (
    REQUEST_SCHEMA as ANIMATION_REQUEST_SCHEMA,
    animation_inspection_document,
    apply_animation_request,
    preview_animation_request,
)
from blender_adapter.modification import apply_semantic_modification, inspect_generated_asset
from blender_adapter.targets import GodotAdapter
from blender_adapter.working_asset_ui import save_editable_checkpoint
from object_core.modification import ModificationRequest, SemanticOperation, plan_modification
from object_core.modify_exchange import inspection_document, request_from_document
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class ProductionCharacterRoundTripTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ("objects", "meshes", "armatures", "collections", "materials", "images", "actions")}

    def tearDown(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.window.scene = self.previous_scene
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)

    def _human(self):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        root = create_character(
            mesh,
            name="ProductionHuman",
            scene=bpy.context.scene,
            skeleton=provider.skeleton(values),
            skin_weights=provider.skin_weights(mesh, values),
            materials=provider.materials(values),
        )
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        settings = getattr(bpy.context.scene, "humanoid_settings", None)
        if settings is not None:
            settings.target = root
        return root

    def test_body_refine_animation_refine_checkpoint_and_engine_export(self):
        root = self._human()

        initial_snapshot = inspect_generated_asset(root)
        exported_model = inspection_document(initial_snapshot)
        self.assertEqual(initial_snapshot.asset_id, exported_model["asset"]["asset_id"])
        targets = {item["key"] for item in exported_model["asset"]["semantic_targets"]}
        self.assertTrue({"body", "shoulders", "face", "jaw"}.issubset(targets))

        returned_model_request = {
            "schema": exported_model["request_template"]["schema"],
            "asset_id": initial_snapshot.asset_id,
            "provider_key": initial_snapshot.provider_key,
            "parameter_changes": {},
            "animation_export_names": {},
            "semantic_operations": [
                {"operation": "shape", "target": "shoulders", "arguments": {"profile": "broad", "amount": 0.45}},
                {"operation": "shape", "target": "face", "arguments": {"profile": "defined", "amount": 0.35}},
                {"operation": "shape", "target": "jaw", "arguments": {"profile": "tapered", "amount": 0.25}},
            ],
            "component_operations": [],
        }
        request = request_from_document(returned_model_request, initial_snapshot)
        body_plan = plan_modification(initial_snapshot, request)
        self.assertTrue(body_plan.safe_to_apply)
        refined_snapshot = apply_semantic_modification(root, body_plan)
        self.assertEqual(3, len(refined_snapshot.semantic_operations))

        idle, _ = add_idle(root, bpy.context.scene, duration=2.6, strength=0.85)
        stable_id = animation_record(idle).animation_id
        exported_animation = animation_inspection_document(root)
        self.assertEqual(stable_id, exported_animation["animations"][0]["animation_id"])

        returned_animation_request = {
            "schema": ANIMATION_REQUEST_SCHEMA,
            "asset_id": refined_snapshot.asset_id,
            "provider_key": refined_snapshot.provider_key,
            "operations": [{
                "animation_id": stable_id,
                "duration_seconds": 2.2,
                "strength": 1.1,
                "export_name": "Refined Idle",
            }],
        }
        preview = preview_animation_request(root, returned_animation_request)
        self.assertTrue(preview["changes"]["duration_seconds"])
        self.assertTrue(preview["changes"]["strength"])
        tuned = apply_animation_request(root, bpy.context.scene, returned_animation_request)
        self.assertEqual(stable_id, tuned.animation_id)
        self.assertEqual("Refined Idle", tuned.export_name)

        with tempfile.TemporaryDirectory() as directory:
            checkpoint = os.path.join(directory, "refined-human.blend")
            saved = save_editable_checkpoint(checkpoint, bpy.ops.wm.save_as_mainfile, bpy.context.scene)
            self.assertTrue(os.path.isfile(saved))
            self.assertGreater(os.path.getsize(saved), 0)

            glb_path = os.path.join(directory, "refined-human.glb")
            result = GodotAdapter(asset_use="ANIMATED").export(root, bpy.context, glb_path)
            if not result.success:
                self.fail("Godot export failed: " + "; ".join(issue.message for issue in result.issues))
            self.assertTrue(os.path.isfile(glb_path))
            self.assertGreater(os.path.getsize(glb_path), 0)

        final_snapshot = inspect_generated_asset(root)
        self.assertEqual(refined_snapshot.asset_id, final_snapshot.asset_id)
        self.assertEqual(3, len(final_snapshot.semantic_operations))
        self.assertTrue(final_snapshot.owns_geometry)
        self.assertTrue(final_snapshot.owns_animations)


if __name__ == "__main__":
    unittest.main()
