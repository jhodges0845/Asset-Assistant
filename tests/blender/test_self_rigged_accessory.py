# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.components import inspect_component, remove_component
from blender_adapter.self_rigged_accessory import create_self_rigged_gauntlet
from object_core.components import ComponentBehavior, RigBinding
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class SelfRiggedAccessoryTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def _human(self):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        root = create_character(
            mesh,
            name="SelfRiggedHuman",
            scene=bpy.context.scene,
            skeleton=provider.skeleton(values),
            skin_weights=provider.skin_weights(mesh, values),
        )
        root["object_type"] = provider.key
        return root

    def test_gauntlet_owns_independent_rig_and_action(self):
        root = self._human()
        component_root, record = create_self_rigged_gauntlet(root)

        inspected = inspect_component(root, record.component_id)
        self.assertEqual(ComponentBehavior.SELF_RIGGED, inspected.behavior)
        self.assertEqual(RigBinding.OWNED, inspected.rig_binding)
        self.assertTrue(inspected.owns_rig)

        rigs = [child for child in component_root.children if child.type == "ARMATURE"]
        meshes = [child for child in component_root.children if child.type == "MESH"]
        self.assertEqual(1, len(rigs))
        self.assertEqual(1, len(meshes))
        rig = rigs[0]
        self.assertTrue(rig.get("asset_assistant_component_rig"))
        self.assertEqual(record.component_id, rig.get("asset_assistant_component_id"))
        self.assertIsNotNone(rig.animation_data)
        self.assertIsNotNone(rig.animation_data.action)
        action = rig.animation_data.action
        self.assertTrue(action.get("asset_assistant_component_animation"))
        self.assertEqual(record.component_id, action.get("asset_assistant_component_id"))
        self.assertEqual("Flex", action.get("asset_assistant_component_animation_name"))

        character_rig = next(child for child in root.children if child.type == "ARMATURE")
        self.assertIsNot(rig, character_rig)
        modifier = next(mod for mod in meshes[0].modifiers if mod.type == "ARMATURE")
        self.assertIs(modifier.object, rig)

    def test_inspection_rejects_missing_owned_component_rig(self):
        root = self._human()
        component_root, record = create_self_rigged_gauntlet(root)
        rig = next(child for child in component_root.children if child.type == "ARMATURE")
        bpy.data.objects.remove(rig, do_unlink=True)

        with self.assertRaisesRegex(ValueError, "exactly one managed component armature"):
            inspect_component(root, record.component_id)

    def test_remove_self_rigged_component_cleans_owned_rig_and_action(self):
        root = self._human()
        component_root, record = create_self_rigged_gauntlet(root)
        rig = next(child for child in component_root.children if child.type == "ARMATURE")
        rig_data_name = rig.data.name
        action = rig.animation_data.action
        action_name = action.name
        unrelated = bpy.data.actions.new("Artist Unrelated Action")

        removed = remove_component(root, record.component_id)

        self.assertEqual(record.component_id, removed.component_id)
        self.assertIsNone(bpy.data.armatures.get(rig_data_name))
        self.assertIsNone(bpy.data.actions.get(action_name))
        self.assertIs(bpy.data.actions.get(unrelated.name), unrelated)
        with self.assertRaisesRegex(ValueError, "not registered"):
            inspect_component(root, record.component_id)


if __name__ == "__main__":
    unittest.main()
