# Workflow and UI/UX acceptance audit

Started 2026-10-23 from main c911e37 after the Human rig/clip merge.
This is the current acceptance ledger, not release approval. Older UI audits
are historical: the current interface has Create, Animate, Components and Export.

## Evidence and remaining gates

| Workflow | Existing or new automated evidence | Remaining acceptance work |
| --- | --- | --- |
| Generated model Modify | Human/Canine/Avian Model JSON import, non-mutating preview, cancel/apply equality, parameter edits, component blocking, artist-geometry blocking and fresh-process persistence | Repeat the final edited silhouettes and continuous motion through the UI; extend representative edited exports beyond the existing Avian destination proofs |
| Animation Modify | Duration/strength preview and regeneration, stable IDs, other-clip preservation; tuning tests now cover all three providers; rename-only requests preserve manually edited keys | Operator-driven external JSON flow now covers all nine provider/clip pairs; manual-key/NLA continuity through save and destination remains open; timing/strength still explicitly regenerates owned curves |
| LOD | No generation, ownership, export grouping or LOD-specific tests found; target notes merely advise destination review | Define static and skinned LOD scope, then implement and verify reduction, silhouette, weights/UV/material preservation, clip playback, export and engine selection; not a completed feature |
| Export | GLB surface parity and switching for Human/Canine, Avian destination evidence, FBX clip staging/naming, static target and package smoke tests | Final-candidate Unity/Unreal/GLTF destination checks, edited-character exports, representative Human Cura slicing; no blanket engine certification |
| Import | GLB round-trip; asset boundary/rig/material/clip discovery; explicit adoption, component and checkpoint tests; previously skipped file-picker/preflight tests now run | Complete real-file .blend/GLB/GLTF/Unity-FBX/Unreal-FBX matrix through Modify, animation, save/reopen and re-export; new single-scene static .blend/GLB/GLTF/FBX fixtures pass actual inspection/adoption/re-export; this does not prove animated or multi-scene imports |
| UI/UX | Four-workspace navigation, imported Animate, rig placement, asset identity and Create controls now included in CI; Export and checkpoint controls precede verbose validation details | Live Blender review at narrow/normal sidebar widths, no-asset/blocked/success states, keyboard navigation, long names, generated/imported/manual-edit flows and error recovery |

## Defects found and repaired

1. The Blender runner used unittest discovery, silently omitting 40 function-based
   import/UI tests. It now uses pytest for both styles and disables unrelated
   plugin autoloading. CI installs test-only dependencies outside the add-on.
   The first enabled run exposed 11 failing tests and six teardown errors:
   outdated registry calls, mocks assigning read-only Blender properties, and
   fake NLA tracks without actual Action strips. Fixtures now exercise current
   registry composition and distinct-Action counting without weakening assertions.
2. Export and Validate + Save Checkpoint appeared after the detailed validation
   list. Actions now precede details and a blocked export has a visible next step.
   This is structurally tested; live spacing/scrolling approval is still open.
3. Animation Modify regenerated an Action for export-name-only requests, losing
   direct keyframe edits. Rename-only and no-op requests now preserve the Action
   and curves; duration/strength regeneration remains explicit in the UI summary.
   Cross-provider tests retain the edited key values and stable animation ID.

4. Imported GLB/GLTF seam-split surfaces were incorrectly required to be closed
   during game export, although game target profiles explicitly do not require
   manifold geometry. Inspection now honors that profile flag. Empty/non-finite,
   zero-area, loose-edge and over-shared-edge geometry checks remain; Cura keeps
   its evaluated print-geometry path and closed-surface requirement. Eighteen
   focused import/export/UI checks pass, including all four real static formats
   and independent open-print/degenerate-game negative cases.

## Validation and reproduction

Install test tooling (not a plugin runtime dependency):

```text
python -m pip install --target artifacts/test-dependencies pytest==8.4.2
blender --background --factory-startup --python-exit-code 1 --python scripts/test_blender.py
```

Optional pytest paths/options follow `--`. ASSET_ASSISTANT_TEST_DEPS can override
the dependency directory. Validation on Blender 5.2.1:

- Expanded Blender suite: 344 passed, 201 warnings in 1013.84 seconds.
- Formerly skipped UI/import tests: all 40 passed.
- Final focused real-file import/export, target and UI checks: 18 passed.
- Core target, architecture and release-package checks: 12 passed.
- Isolated packaged add-on smoke: passed (`PACKAGED_ADDON_OK`).

The full run started before the final target-validation and UI wording changes
and the new static-file tests. The 18 focused checks cover those final changes;
the 344 count is not a full rerun of the final snapshot. Warnings remain, including
Blender API deprecations. Logs are local artifacts, not release approval.

Live desktop review could not start: the computer-use Node helper failed during
Windows sandbox setup and failed again after reset. No screenshots or interactive
UI behavior were verified. Source/draw tests cannot certify visual usability.

## Additional import finding

A multi-scene GLB/GLTF fixture can create objects outside the active view layer;
`_import_external` then attempts to select a root from all new datablocks and
previously raised an error after leaving partial imported data behind. The
follow-up now rejects objects outside the original view layer with a request to
export one scene separately. Failure removes only newly created exchange-import
datablocks and restores the original scene, view layer, selection and active
object. Real two-scene GLB/GLTF fixtures verify rejection and exact datablock
preservation; an injected activation failure checks partial material/Action
cleanup. Single-scene imports remain supported. Scene selection and multi-scene
asset import remain unsupported; rejection is not broader import support.

Follow-up validation: 22 focused Blender tests passed (11 API deprecation
warnings), covering the static format matrix, multi-scene rejection, partial
activation failure, animated Human GLB round-trip and file-import UI helpers.

## Order of remaining work

1. Extend animation manual-edit/NLA preservation through save/reopen and destination playback; all-clip operator acceptance now passes.
2. Exercise real imported files and edited-model export/reimport matrices.
3. Define and implement the LOD workflow; do not label destination reminders support.
4. Complete live UI/UX and continuous visual review, then candidate package/install
   lifecycle and destination checks. Release/tag/publication remains a separate decision.


## Live UI/UX protocol (not yet executed)

Use a disposable copy at 280, 360 and 480 pixel sidebar widths. Cover no asset,
generated Human/Canine/Avian, imported static, imported rigged, and manually
edited states. Do not substitute screenshots of a mockup for the installed UI.

- Create: generation versus replacement is clear; imported properties do not
  masquerade as known generator inputs; cancelled previews restore the scene.
- Animate: rig access is discoverable before clips; ownership and regeneration
  effects are clear; selecting, tuning and renaming clips preserves unrelated
  Actions; imported/artist-owned curves are never presented as generated.
- Components: current base asset stays clear; selecting a child or accessory
  does not silently change which asset receives edits; unsupported regeneration
  explains the component blocker before application.
- Export: destination and static/animated intent are obvious; checkpoint and
  export buttons remain findable with many validation messages; disabled export
  explains the next action; long paths and names do not obscure primary controls.
- Across workspaces: inspect empty states, tooltips, focus/tab order, cancellation,
  stale preview recovery, error messages, undo, and saved-file reopening. Record
  screenshots and exact reproduction steps for defects; keep visual approval
  separate from API/operator assertions.


## Animation operator acceptance (2026-10-24)

`tests/blender/test_animation_operator_acceptance.py` runs registered Export
Inspection, Import Changes, Preview and Apply operators for Human and Canine
Idle/Walk/Run and Avian Idle/Walk/Flight. Three provider cases passed in 115.28
seconds, covering nine clips and both rename-only and timing/strength requests.

Preview leaves keys unchanged. Rename-only Apply preserves the Action, edited
key values, handles, interpolation and stable identity. Timing/strength Apply
produces the requested duration/strength with the same stable identity. Both
paths preserve unrelated clip Actions and their curves. This is operator-level
acceptance, not live UI or NLA/save/reopen/destination certification.
