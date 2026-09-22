# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle, set_clip_export_name
from blender_adapter.materials import prepare_materials
from blender_adapter.modification import apply_parameter_modification, inspect_generated_asset
from blender_adapter.workflow import add_basic_rig
from object_core.modification import ModificationRequest, plan_modification
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderModificationParameterApplyTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        for action in tuple(bpy.data.actions):
            bpy.data.actions.remove(action)
        for collection in tuple(bpy.data.collections):
            if collection.users == 0:
                bpy.data.collections.remove(collection)

    def _asset(self, provider_key, *, rig=False, materials=False, animation=False):
        provider = get_provider(provider_key)
        values = {field.key: field.default for field in provider.parameters}
        root = create_character(provider.mesh(values), name=provider.label, scene=bpy.context.scene)
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        bpy.context.view_layer.objects.active = root
        root.select_set(True)
        if materials:
            prepare_materials(root)
        if rig:
            add_basic_rig(root, bpy.context)
        if animation:
            add_idle(root, bpy.context.scene)
        return root, provider, values

    def _avian(self, *, rig=False, materials=False, animation=False):
        return self._asset("avian", rig=rig, materials=materials, animation=animation)

    def test_parameter_change_replaces_owned_geometry_on_same_root(self):
        root, _, values = self._avian()
        root.location = (2.0, -3.0, 1.25)
        root_identity = root.as_pointer()
        before_mesh = next(obj for obj in root.children if obj.type == "MESH")
        before_mesh_pointer = before_mesh.as_pointer()

        snapshot = inspect_generated_asset(root)
        plan = plan_modification(
            snapshot,
            ModificationRequest(parameter_changes=(("wingspan_cm", 120),)),
        )
        result = apply_parameter_modification(root, plan)

        self.assertEqual(root_identity, root.as_pointer())
        self.assertEqual((2.0, -3.0, 1.25), tuple(root.location))
        self.assertEqual(120.0, root["wingspan_cm"])
        self.assertEqual(values["body_length_cm"], root["body_length_cm"])
        self.assertTrue(all(obj.as_pointer() != before_mesh_pointer for obj in root.children))
        self.assertTrue(result.owns_geometry)
        self.assertEqual(120.0, result.parameter_values()["wingspan_cm"])

    def test_supported_parameter_regeneration_works_for_each_deforming_provider(self):
        cases = (
            ("human", "height_cm", 190.0),
            ("quadruped", "body_length_cm", 82.0),
            ("avian", "wingspan_cm", 120.0),
        )
        for provider_key, parameter, replacement in cases:
            with self.subTest(provider=provider_key):
                root, provider, values = self._asset(provider_key)
                root.location = (1.0, 2.0, 3.0)
                root_identity = root.as_pointer()

                snapshot = inspect_generated_asset(root)
                plan = plan_modification(
                    snapshot,
                    ModificationRequest(parameter_changes=((parameter, replacement),)),
                )
                self.assertTrue(plan.safe_to_apply)
                self.assertEqual(("geometry",), plan.rebuild_components)

                result = apply_parameter_modification(root, plan)

                self.assertEqual(provider.key, result.provider_key)
                self.assertEqual(root_identity, root.as_pointer())
                self.assertEqual((1.0, 2.0, 3.0), tuple(root.location))
                self.assertEqual(replacement, root[parameter])
                self.assertEqual(replacement, result.parameter_values()[parameter])
                self.assertTrue(result.owns_geometry)
                for key, value in values.items():
                    if key != parameter:
                        self.assertEqual(value, root[key])

                bpy.ops.object.select_all(action="SELECT")
                bpy.ops.object.delete(use_global=False)

    def test_rig_materials_and_generated_animation_survive_regeneration(self):
        root, _, _ = self._avian(rig=True, materials=True, animation=True)
        set_clip_export_name(root, "Idle", "Rest Pose")
        old_rig = next(obj for obj in root.children if obj.type == "ARMATURE")
        old_rig_id = old_rig.get("asset_assistant_rig_id")

        snapshot = inspect_generated_asset(root)
        plan = plan_modification(
            snapshot,
            ModificationRequest(parameter_changes=(("tail_length_cm", 30),)),
        )
        result = apply_parameter_modification(root, plan)

        new_rig = next(obj for obj in root.children if obj.type == "ARMATURE")
        self.assertNotEqual(old_rig_id, new_rig.get("asset_assistant_rig_id"))
        self.assertTrue(result.owns_geometry)
        self.assertTrue(result.owns_rig)
        self.assertTrue(result.owns_materials)
        self.assertTrue(result.owns_animations)
        self.assertEqual(("Rest Pose",), tuple(clip.export_name for clip in result.animations))
        idle = next(action for action in bpy.data.actions
                    if action.get("asset_assistant_clip") == "Idle")
        self.assertEqual(new_rig.get("asset_assistant_rig_id"), idle.get("asset_assistant_rig_id"))

    def test_artist_constraint_blocks_destructive_parameter_change(self):
        root, _, _ = self._avian(rig=True)
        rig = next(obj for obj in root.children if obj.type == "ARMATURE")
        bone = next(iter(rig.pose.bones))
        bone.constraints.new("COPY_ROTATION")

        snapshot = inspect_generated_asset(root)
        plan = plan_modification(
            snapshot,
            ModificationRequest(parameter_changes=(("body_length_cm", 50),)),
        )

        self.assertFalse(snapshot.owns_rig)
        self.assertFalse(plan.safe_to_apply)
        self.assertIn("Cannot safely replace unowned or ambiguous rig", plan.blockers)
        with self.assertRaisesRegex(ValueError, "blockers"):
            apply_parameter_modification(root, plan)
        self.assertEqual(42, root["body_length_cm"])
        self.assertEqual(1, len(bone.constraints))


if __name__ == "__main__":
    unittest.main()
