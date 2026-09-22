# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from object_core.animations import (
    AnimationRecord,
    AnimationSource,
    RootMotionIntent,
    animation_document,
    animation_from_document,
    validate_animation,
)


class AnimationRecordTests(unittest.TestCase):
    def _record(self, **changes):
        values = dict(
            animation_id="anim-idle-001",
            display_name="Idle",
            export_name="Idle",
            source=AnimationSource.GENERATED,
            rig_signature="bones:root,torso,head",
            frame_start=1.0,
            frame_end=96.0,
            fps=24.0,
            looping=True,
            root_motion=RootMotionIntent.IN_PLACE,
            owns_curves=True,
            source_reference="human:idle",
            provider_key="human",
            capability="idle",
        )
        values.update(changes)
        return AnimationRecord(**values)

    def test_document_round_trip_preserves_identity_and_ownership(self):
        record = self._record()
        document = animation_document(record)

        self.assertEqual(record, animation_from_document(document))
        self.assertEqual("anim-idle-001", document["animation_id"])
        self.assertTrue(document["owns_curves"])
        self.assertEqual("in_place", document["root_motion"])

    def test_imported_artist_animation_can_remain_unowned(self):
        record = self._record(
            animation_id="anim-import-001",
            source=AnimationSource.IMPORTED,
            owns_curves=False,
            source_reference="walk.fbx#Take 001",
            provider_key=None,
            capability=None,
        )

        self.assertIs(record, validate_animation(record))
        self.assertFalse(animation_document(record)["owns_curves"])

    def test_generated_animation_requires_curve_ownership(self):
        with self.assertRaisesRegex(ValueError, "must own"):
            validate_animation(self._record(owns_curves=False))

    def test_frame_and_fps_contracts_are_strict(self):
        with self.assertRaisesRegex(ValueError, "frame_end"):
            validate_animation(self._record(frame_start=10, frame_end=9))
        with self.assertRaisesRegex(ValueError, "fps"):
            validate_animation(self._record(fps=0))
        with self.assertRaisesRegex(ValueError, "frame_start"):
            validate_animation(self._record(frame_start=float("nan")))
        with self.assertRaisesRegex(ValueError, "frame_end"):
            validate_animation(self._record(frame_end=float("inf")))
        with self.assertRaisesRegex(ValueError, "fps"):
            validate_animation(self._record(fps=float("inf")))

    def test_unknown_document_fields_are_rejected(self):
        document = animation_document(self._record())
        document["blender_action"] = "IdleAction"
        with self.assertRaisesRegex(ValueError, "unknown animation fields"):
            animation_from_document(document)

    def test_host_specific_identity_is_not_required(self):
        record = self._record(source_reference=None)
        document = animation_document(record)
        self.assertNotIn("source_reference", document)
        self.assertNotIn("action_name", document)


if __name__ == "__main__":
    unittest.main()
