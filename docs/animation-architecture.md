# Animation architecture

Animations are first-class reusable assets in Asset Assistant. Their portable identity and ownership contract lives in `object_core`; Blender Actions, NLA data, keyframes, and target-export details remain adapter concerns.

## Portable animation record

`AnimationRecord` establishes the host-independent metadata needed to inspect and safely manage a clip:

- stable `animation_id` independent of the host action/datablock name;
- artist-facing `display_name` and destination-facing `export_name`;
- `AnimationSource` provenance: generated, imported, or artist-authored;
- portable `rig_signature` compatibility identity;
- finite frame start/end and FPS;
- loop intent;
- `RootMotionIntent` (`none`, `in_place`, or `root`);
- explicit `owns_curves` ownership boundary;
- optional source reference, provider key, and capability identity.

The record intentionally contains no Blender Action name, slot, FCurve, NLA, object pointer, or engine-specific field.

Generated records must own their generated curves. Imported or artist-authored records remain unowned so lifecycle and Modify work cannot silently overwrite artist animation.

## Serialization boundary

`animation_document()` produces strict JSON-safe portable state. `animation_from_document()` rejects missing and unknown fields instead of silently accepting host-specific metadata or schema drift.

## Blender persistence and inspection

New Asset Assistant-generated Blender Actions persist the portable record as Action metadata while retaining the existing generated clip, rig ownership, and export-name properties used by current UI/export code.

The adapter assigns a stable animation ID, records provider/capability provenance, and computes a deterministic rig signature from the generated armature's bone names, parent relationships, and deform flags. Inspection rejects mismatched IDs, incompatible rig signatures, generated records attached to non-generated Actions, and export-name drift.

Generated and adopted first-class Actions are also scoped to the owning Asset Assistant rig identity. Rig signature alone is not sufficient because two characters can legitimately share the same skeleton topology. This prevents an Action belonging to one Human from being mistaken for an Action belonging to another Human with the same rig structure.

The existing animation export-name workflow updates the portable record and the legacy Action property together. Legacy generated Actions from older `.blend` files that do not yet carry animation-record metadata remain usable and renameable; malformed new record metadata is not silently ignored.

Current generated Idle/Walk-or-locomotion/Flight/Run clips are recorded as looping, in-place animations with no accumulated root travel. Contact gaits can include cyclic root compression or sway; these offsets return to their starting values at the loop boundary.

## Action registration and lifecycle

Existing Blender Actions can be explicitly registered as `artist` or `imported` animation assets for one Asset Assistant rig. Registration adds stable portable identity, current-rig compatibility, frame/FPS metadata, loop/root-motion intent, and an engine-facing export name without changing the Action's curves or claiming curve ownership.

Registration refuses generated Actions, Actions already carrying Asset Assistant animation identity, and Actions actively assigned to another Blender object. This keeps adoption explicit and prevents a shared or unrelated Action from being silently claimed.

Lifecycle operations preserve ownership:

- removing an artist/imported registration removes Asset Assistant identity but leaves the Action and its curves intact;
- removing a generated record may delete the generated Action because Asset Assistant owns those curves;
- replacing a managed animation preserves its stable `animation_id` while moving that identity to the replacement Action;
- replacing an artist/imported clip leaves the prior Action intact and merely stops managing it;
- an active replaced clip moves the rig's active Action to the validated replacement.

`managed_actions()` discovers first-class records owned by and compatible with the current rig. `exportable_actions()` additionally retains legacy generated Actions so old editable checkpoints remain discoverable while export staging is migrated to the first-class lifecycle.

## External animation Modify

The dedicated external animation workflow is now implemented in the Animations panel:

`Export Animation Inspection -> external edit -> Import Animation Changes -> Preview Animation Changes -> Apply / Save Animation Changes -> re-inspect/play`

Inspection exports stable animation identity, provider/capability, timing, saved generation strength, ownership, and the changes that are currently safe to execute. Returned requests are validated against the current asset and animation before mutation. Preview is non-mutating.

The first executable tuning surface intentionally stays reproducible and narrow:

- cycle duration/speed;
- overall generated motion strength; and
- export name.

For an owned generated clip, Apply regenerates only that clip from its provider capability, preserves the stable `animation_id`, and preserves every other generated or artist Action. Artist/imported Actions remain curve-unowned and cannot be regenerated by this path.

This approach deliberately avoids arbitrary quaternion-curve surgery. Richer semantics such as torso lean, arm swing, knee lift, contact timing, root-motion generation, and provider-specific gait controls should be added through provider/capability-specific contracts when they can be reproduced safely.

## Editable continuity

Animation state is part of the authoritative `.blend` editable checkpoint. The supported production flow is:

`Generate/open asset -> model Modify -> save checkpoint -> reopen -> generate/select animation -> animation inspection/refinement -> preview/play -> save checkpoint -> destination export`

Automated coverage now chains Human semantic body refinement, generated animation refinement, editable checkpoint save, and Godot export while preserving asset and animation identity. A real Blender save/reopen/visual-preview pass remains the final manual checkpoint before the editable-continuity phase is closed.

## Next animation work after the checkpoint

After the manual continuity checkpoint passes, animation work should expand only where production use demonstrates a need. Likely next candidates are provider-specific gait/body-language controls, root-motion support, and richer imported-animation workflows. These should not block starting real hair/clothing/accessory component providers.