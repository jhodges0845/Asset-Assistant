# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle
from blender_adapter.animation_lifecycle import register_animation_action
from blender_adapter.animation_modify_exchange import animation_state
from object_core.animations import AnimationSource
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderAnimationModifyExchangeTests(unittest.TestCase):
    def setUp(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ("objects", "meshes", "armatures", "collections", "materials", "images", "actions")}

    def tearDown(self):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
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
            name="ModifyExchangeHuman",
            scene=bpy.context.scene,
            skeleton=provider.skeleton(values),
            skin_weights=provider.skin_weights(mesh, values),
        )
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        return root

    def test_artist_animation_is_visible_but_not_owned(self):
        root = self._human()
        generated, _ = add_idle(root, bpy.context.scene, duration=1.0)
        artist = generated.copy()
        artist.name = "Artist Idle"
        for key in tuple(artist.keys()):
            if str(key).startswith("asset_assistant_"):
                del artist[key]
        rig = next(child for child in root.children if child.type == "ARMATURE")
        if rig.animation_data and rig.animation_data.action == generated:
            rig.animation_data.action = None
        bpy.data.actions.remove(generated)
        record = register_animation_action(
            root,
            artist,
            source=AnimationSource.ARTIST,
            export_name="ArtistIdle",
            fps=30.0,
            looping=True,
        )

        warnings = []
        clips, has_animations, owns_animations = animation_state(root, warnings)

        self.assertTrue(has_animations)
        self.assertFalse(owns_animations)
        self.assertEqual([], warnings)
        self.assertEqual(1, len(clips))
        self.assertEqual(record.animation_id, clips[0].clip_id)
        self.assertEqual("artist", clips[0].source)
        self.assertEqual("ArtistIdle", clips[0].export_name)
        self.assertFalse(clips[0].owns_curves)


if __name__ == "__main__":
    unittest.main()
