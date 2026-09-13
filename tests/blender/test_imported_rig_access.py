# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from types import SimpleNamespace

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter import imported_rig_access


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class ImportedRigAccessTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.before_objects = set(bpy.data.objects)
        self.before_armatures = set(bpy.data.armatures)
        self.scene = bpy.data.scenes.new("ImportedRigAccess")
        bpy.context.window.scene = self.scene

    def tearDown(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for obj in set(bpy.data.objects) - self.before_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for armature in set(bpy.data.armatures) - self.before_armatures:
            if armature.users == 0:
                bpy.data.armatures.remove(armature)

    def test_imported_target_exposes_normalized_base_rig_even_when_not_direct_child(self):
        root = bpy.data.objects.new("Imported Asset", None)
        self.scene.collection.objects.link(root)
        root["asset_assistant_external_asset"] = True
        root["asset_assistant_import_group"] = "rig-access"
        root["asset_assistant_import_root"] = True

        holder = bpy.data.objects.new("Importer Holder", None)
        self.scene.collection.objects.link(holder)
        holder["asset_assistant_import_group"] = "rig-access"
        holder.parent = root

        armature = bpy.data.armatures.new("ImportedRig.Data")
        rig = bpy.data.objects.new("ImportedRig", armature)
        self.scene.collection.objects.link(rig)
        rig["asset_assistant_import_group"] = "rig-access"
        rig.parent = holder

        # The full add-on is intentionally not registered by the generic Blender
        # test harness. Exercise the rig-access contract with the same scene/target
        # shape the registered PointerProperty provides at runtime instead of making
        # this regression depend on unrelated add-on registration order.
        scene_contract = SimpleNamespace(
            humanoid_settings=SimpleNamespace(target=root),
            objects=self.scene.objects,
        )
        object_context = SimpleNamespace(scene=scene_contract, mode="OBJECT")
        pose_context = SimpleNamespace(scene=scene_contract, mode="POSE")

        self.assertIs(imported_rig_access._base_rig(object_context), rig)
        self.assertTrue(imported_rig_access.ASSET_ASSISTANT_OT_select_base_rig.poll(object_context))
        self.assertTrue(imported_rig_access.ASSET_ASSISTANT_OT_pose_base_rig.poll(object_context))
        self.assertFalse(imported_rig_access.ASSET_ASSISTANT_OT_exit_pose_mode.poll(object_context))

        self.assertFalse(imported_rig_access.ASSET_ASSISTANT_OT_select_base_rig.poll(pose_context))
        self.assertFalse(imported_rig_access.ASSET_ASSISTANT_OT_pose_base_rig.poll(pose_context))
        self.assertTrue(imported_rig_access.ASSET_ASSISTANT_OT_exit_pose_mode.poll(pose_context))


if __name__ == "__main__":
    unittest.main()
