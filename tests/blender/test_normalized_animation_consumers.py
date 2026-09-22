# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle
from blender_adapter.animation_lifecycle import managed_actions, register_animation_action
from object_core.animations import AnimationSource
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class NormalizedAnimationConsumerTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        self.before = {
            name: set(getattr(bpy.data, name))
            for name in ("objects", "meshes", "armatures", "collections", "materials", "actions")
        }

    def tearDown(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)

    def test_animation_lifecycle_accepts_import_group_rig_that_is_not_direct_child(self):
        provider = get_provider("human")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        root = create_character(
            mesh,
            name="ImportedStyleHuman",
            scene=bpy.context.scene,
            skeleton=provider.skeleton(values),
            skin_weights=provider.skin_weights(mesh, values),
        )
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value

        rig = next(child for child in root.children if child.type == "ARMATURE")
        generated, _ = add_idle(root, bpy.context.scene, duration=1.0)
        artist = generated.copy()
        artist.name = "Imported Walk"
        for key in tuple(artist.keys()):
            if str(key).startswith("asset_assistant_"):
                del artist[key]
        if rig.animation_data and rig.animation_data.action == generated:
            rig.animation_data.action = None
        bpy.data.actions.remove(generated)

        group = "normalized-import-test"
        members = [root, rig] + [child for child in root.children if child.type == "MESH"]
        for obj in members:
            obj["asset_assistant_import_group"] = group
        root["asset_assistant_import_root"] = True
        rig.parent = None

        record = register_animation_action(
            root,
            artist,
            source=AnimationSource.IMPORTED,
            export_name="Walk",
            fps=24.0,
            looping=True,
        )

        self.assertEqual("Walk", record.export_name)
        self.assertIn(artist, managed_actions(root))


if __name__ == "__main__":
    unittest.main()
