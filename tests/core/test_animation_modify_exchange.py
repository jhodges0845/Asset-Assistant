# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from object_core.modification import AnimationSnapshot, AssetSnapshot
from object_core.modify_exchange import inspection_document
from object_core.objects import get_provider


class AnimationModifyExchangeTests(unittest.TestCase):
    def test_inspection_exposes_first_class_animation_metadata(self):
        provider = get_provider("human")
        clip = AnimationSnapshot(
            clip_id="animation-123",
            export_name="Walk",
            display_name="Artist Walk",
            source="artist",
            rig_signature="sha256:abc",
            frame_start=1.0,
            frame_end=25.0,
            fps=24.0,
            looping=True,
            root_motion="in_place",
            owns_curves=False,
            source_reference="walk.fbx",
        )
        snapshot = AssetSnapshot(
            asset_id="asset-1",
            provider_key=provider.key,
            provider_label=provider.label,
            parameters=tuple((field.key, field.default) for field in provider.parameters),
            animations=(clip,),
            has_animations=True,
        )

        document = inspection_document(snapshot)
        animation = document["asset"]["animations"][0]

        self.assertEqual("animation-123", animation["clip_id"])
        self.assertEqual("Artist Walk", animation["display_name"])
        self.assertEqual("artist", animation["source"])
        self.assertEqual("sha256:abc", animation["rig_signature"])
        self.assertEqual(1.0, animation["frame_start"])
        self.assertEqual(25.0, animation["frame_end"])
        self.assertEqual(24.0, animation["fps"])
        self.assertTrue(animation["looping"])
        self.assertEqual("in_place", animation["root_motion"])
        self.assertFalse(animation["owns_curves"])
        self.assertEqual("walk.fbx", animation["source_reference"])

    def test_legacy_animation_snapshot_keeps_compact_shape(self):
        provider = get_provider("human")
        snapshot = AssetSnapshot(
            asset_id="asset-1",
            provider_key=provider.key,
            provider_label=provider.label,
            parameters=tuple((field.key, field.default) for field in provider.parameters),
            animations=(AnimationSnapshot("Idle", "Idle"),),
            has_animations=True,
        )

        animation = inspection_document(snapshot)["asset"]["animations"][0]

        self.assertEqual({"clip_id": "Idle", "export_name": "Idle"}, animation)


if __name__ == "__main__":
    unittest.main()
