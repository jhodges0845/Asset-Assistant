# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle
from blender_adapter.animation_lifecycle import (
    managed_actions,
    register_animation_action,
    remove_animation,
    replace_animation_action,
)
from blender_adapter.animation_records import animation_record, has_animation_record
from object_core.animations import AnimationSource
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderAnimationLifecycleTests(unittest.TestCase):
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

    def _rigged_human(self):
        provider = get_provider("human_experimental")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        root = create_character(
            mesh,
            name="LifecycleHuman",
            scene=bpy.context.scene,
            skeleton=provider.skeleton(values),
            skin_weights=provider.skin_weights(mesh, values),
        )
        root["object_type"] = provider.key
        for key, value in values.items():
            root[key] = value
        rig = next(child for child in root.children if child.type == "ARMATURE")
        return root, rig

    def _artist_action(self, root, name):
        generated, _ = add_idle(root, bpy.context.scene, duration=1.0)
        artist = generated.copy()
        artist.name = name
        for key in tuple(artist.keys()):
            if str(key).startswith("asset_assistant_"):
                del artist[key]
        rig = next(child for child in root.children if child.type == "ARMATURE")
        if rig.animation_data and rig.animation_data.action == generated:
            rig.animation_data.action = None
        bpy.data.actions.remove(generated)
        return artist

    def test_register_artist_action_preserves_curve_ownership(self):
        root, _ = self._rigged_human()
        artist = self._artist_action(root, "Artist Idle")
        frame_range = tuple(artist.frame_range)

        record = register_animation_action(
            root,
            artist,
            source=AnimationSource.ARTIST,
            export_name="ArtistIdle",
            fps=30.0,
            looping=True,
        )

        self.assertEqual(AnimationSource.ARTIST, record.source)
        self.assertFalse(record.owns_curves)
        self.assertEqual(frame_range, tuple(artist.frame_range))
        self.assertIn(artist, managed_actions(root))
        self.assertEqual("ArtistIdle", artist["asset_assistant_export_name"])

    def test_registration_failure_does_not_partially_claim_artist_action(self):
        root, rig = self._rigged_human()
        artist = self._artist_action(root, "Unclaimed Artist Action")
        del rig["asset_assistant_rig_id"]

        with self.assertRaisesRegex(ValueError, "stable Asset Assistant rig id"):
            register_animation_action(root, artist, fps=24.0)

        self.assertFalse(has_animation_record(artist))
        self.assertNotIn("asset_assistant_export_name", artist)
        self.assertNotIn("asset_assistant_rig_id", artist)

    def test_remove_artist_animation_deletes_action_from_working_file(self):
        root, _ = self._rigged_human()
        artist = self._artist_action(root, "Delete My Curves")
        record = register_animation_action(root, artist, fps=24.0)
        name = artist.name

        removed = remove_animation(root, record.animation_id)

        self.assertEqual(record.animation_id, removed.animation_id)
        self.assertIsNone(bpy.data.actions.get(name))

    def test_remove_generated_animation_deletes_owned_action(self):
        root, _ = self._rigged_human()
        action, _ = add_idle(root, bpy.context.scene)
        record = animation_record(action)
        name = action.name

        removed = remove_animation(root, record.animation_id)

        self.assertEqual(record.animation_id, removed.animation_id)
        self.assertNotIn(name, bpy.data.actions)

    def test_replace_preserves_stable_id_and_old_artist_action(self):
        root, rig = self._rigged_human()
        current = self._artist_action(root, "Original Artist Idle")
        first = register_animation_action(root, current, export_name="Idle", fps=24.0)
        current_name = current.name
        replacement = current.copy()
        replacement.name = "Replacement Artist Idle"
        for key in tuple(replacement.keys()):
            if str(key).startswith("asset_assistant_"):
                del replacement[key]
        rig.animation_data_create().action = current

        updated = replace_animation_action(
            root,
            first.animation_id,
            replacement,
            source=AnimationSource.IMPORTED,
            fps=30.0,
            looping=True,
            source_reference="replacement.fbx",
        )

        self.assertEqual(first.animation_id, updated.animation_id)
        self.assertEqual(AnimationSource.IMPORTED, updated.source)
        self.assertIs(rig.animation_data.action, replacement)
        self.assertIs(bpy.data.actions.get(current_name), current)
        self.assertFalse(has_animation_record(current))
        self.assertEqual(first.animation_id, animation_record(replacement).animation_id)

    def test_registration_rejects_action_assigned_to_another_object(self):
        root, _ = self._rigged_human()
        artist = self._artist_action(root, "Foreign Action")
        other_data = bpy.data.armatures.new("OtherRigData")
        other = bpy.data.objects.new("OtherRig", other_data)
        bpy.context.scene.collection.objects.link(other)
        other.animation_data_create().action = artist

        with self.assertRaisesRegex(ValueError, "another Blender object"):
            register_animation_action(root, artist, fps=24.0)


if __name__ == "__main__":
    unittest.main()
