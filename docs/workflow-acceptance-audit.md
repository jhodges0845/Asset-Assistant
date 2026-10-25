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


## NLA preservation and preview boundary (2026-10-24)

Timing/strength regeneration already rejected rigs with NLA tracks or drivers at
Apply, but Preview incorrectly accepted those requests. Preview now shares the
same artist-animation validation as generation. Rename-only requests remain
available and preserve the original Action and NLA arrangement. The workflow
does not retime or replace artist-arranged NLA strips automatically.

New regressions reproduced the missing Preview blocker on all three providers.
`scripts/test_animation_nla_reopen.py` passes separate Blender-process checks for
Human, Canine and Avian: stable animation identity, renamed export name, keys,
NLA Action reference, placement, repeat and influence survive save/reopen. The
script is included in CI. These checks cover arranged Idle clips; destination
playback and arbitrary edited multi-track arrangements remain open.

Validation: 21 tuning/operator tests passed in 139.94 seconds; all three
fresh-process NLA checks and five architecture-boundary tests passed.


## Animated exchange matrix (2026-10-24)

Human Idle/Walk exports now have Blender reimport checks for GLB, separate GLTF,
Unity FBX and Unreal FBX. GLB/GLTF/Unity retain a mesh, one rig, materials and both
clips. Unreal intentionally writes a model without animation plus one file per
clip; both Idle and Walk files reimport with one rig and one clip each.

The first run passed three formats and exposed an incorrect single-file Unreal
test assumption. After matching the documented exporter package contract, the
focused Unreal check passed (38.85 seconds). This proves structural reimport,
not engine playback, exact skin/pose parity, all providers or the complete
imported-asset Modify/checkpoint/re-export workflow. Those remain release gates
in [the roadmap](shared-anatomy-alpha-plan.md#required-workflow-release-gates-2026-10-24).


## Edited Human/Canine GLB skin parity (2026-10-24)

`tests/blender/test_edited_glb_playback.py` applies broad shoulders to Human and
broad chest to Canine (amount 0.6) through the semantic modification planner.
Both edits change geometry while preserving skin weights and generated ownership.
The resulting Idle/Walk/Run library then uses the actual GLB export/import path.

Both provider cases passed in 179.05 seconds (six Blender API deprecation
warnings). At 34 phase samples per Walk/Idle/Run/Idle segment, a fixed vertex
correspondence keeps imported evaluated skin within 0.002 cm of the edited
source. The shared harness also checks exported names/fractional durations,
exclusion of unrelated Actions, loop closure and sampled gait ground clearance.

This is Blender reimport parity for two default-proportion edits, not independent
engine playback or artistic approval. Edited FBX, other supported shapes and
arbitrary artist-authored geometry remain part of the release matrix.


## Edited Human exchange structure (2026-10-24)

`tests/blender/test_edited_exchange_structure.py` applies broad shoulders (0.6)
before generating Idle/Walk, then exports/reimports GLB, separate GLTF, Unity FBX
and the Unreal model-plus-per-clip FBX package. All four tests passed in 68.56
seconds, with 24 Blender API deprecation warnings.

For every imported rig, the test requires a bound mesh, rest dimensions matching
the edited source within 0.0001 Blender units (0.1 mm in the metre-scale fixture),
and per-vertex bone-weight sums within 0.001 of one. Existing exchange assertions
also require materials and the target-specific clip counts. The test confirms
that the semantic operation actually changed the source geometry first.

This extends edited-model structural acceptance; it does not establish FBX posed
skin parity, engine playback, arbitrary manual edits or all provider shapes.
Those remain open release gates.


## Edited Human FBX sampled motion parity (2026-10-24)

The edited exchange test now compares Unity and Unreal FBX evaluated skin against
the source Idle/Walk clips at five integer baked-frame offsets per clip, using
one fixed rest-pose vertex correspondence. Both paths stay below 0.002 cm error;
imported duration may differ by up to one frame because FBX endpoints are rounded.
The final four-format run passed in 73.36 seconds (24 API deprecation warnings).

Initial failures were test-harness assumptions: Unity FBX Actions contain separate
root-object and rig slots, while Unreal per-clip Actions can use generic scene
names. The test now selects the slot belonging to each imported rig and uses the
Unreal clip file's identity. Tolerance and correspondence were not relaxed.

This covers one edited Human and two clips at sampled baked frames, not subframe
interpolation, all providers, engine runtime playback or visual approval.


## Edited Godot destination probes (2026-10-24)

Blender 5.2.1 and Godot 4.7.2 probes now cover default Canine broad chest and
Human broad shoulders, both amount 0.6. They compare Walk/Idle/Run/Idle at 34
phases across three cycles, with unchanged 0.002 cm tolerance. The skin probe
uses fixed neutral correspondence and verifies coverage of every source vertex.

| Fixture | Import mode | Skeletal/skin result |
| --- | --- | --- |
| Edited Canine | Verified authored grid | Both pass; skin maximum 0.000788 cm, all 17,218 source vertices covered |
| Edited Human | 800 fps diagnostic | Both fail for Walk/Run; Idle passes; all 42,186 source vertices covered |

Human maximum bone-head errors are 0.005955 cm (Walk) and 0.039657 cm (Run).
Skin errors are 0.007865 cm (Walk), 0.053513 cm (Run), and 0.000281 cm (Idle).
Rest geometry matches. These are open destination-fidelity failures, not visual
approval or a reason to raise the tolerance. Human contact keys are nonuniform,
so the fixture deliberately has no authored-grid import rate. Diagnostic 800 fps
is not a production import setting. Next isolate Godot resampling/interpolation
from exporter behavior; do not claim the cause is established.

Reproduction (fresh output directories; commands after Blender's `--`):

- `scripts/export_canine_godot_review.py --edit-amount .6 --posed-surface --output artifacts/workflow-godot-canine-edited`
- `scripts/export_human_godot_review.py --edit-amount .6 --posed-surface --output artifacts/workflow-godot-human-diagnostic`
- Godot Canine: `--headless --path <fixture> --script review.gd -- --source-aligned`
- Godot Human: `--headless --path <fixture> --script review.gd`
- Renderer-backed skin: `--path <fixture> --script skin.gd --rendering-method gl_compatibility`; add `-- --diagnostic-import` for Human.

Each fixture holds `expected.json`, `godot-report.json` and
`godot-skin-report.json`; generated assets are local artifacts. The scripts retain
historical canine/avian filenames. Dense probes now index tolerance-near rest
vertices in spatial cells, preserving distance and coverage checks; the
bidirectional geometry check retains a full search for out-of-tolerance points.
Godot used ANGLE on this host after an OpenGL-driver warning.


## Human quaternion export repair (2026-10-24)

Increasing the original Godot diagnostic import from 800 to 3,200 fps left Run
bone-head error essentially unchanged (0.039657 versus 0.039652 cm). A focused
quaternion regression reproduced the difference between Blender's normalized
linear component curves and glTF spherical rotation interpolation.

The glTF staging path now densifies linear quaternion curves only on temporary
export Action copies, evaluating the original components along small rotation
intervals (0.005 radians). Editable Actions, fractional endpoints and FBX behavior
are preserved. Nonlinear keys and non-Cycles modifiers are outside this repair.
The regression checks source preservation and spherical-vs-component agreement
at 128 samples; existing edited Human/Canine playback and target checks also pass.

Validation so far: 11 focused Blender tests (39 API warnings) and five architecture
checks passed. With the revised GLB at 800 fps, Godot skeleton checks pass, Walk
skin error is 0.001435 cm, Idle is 0.000281 cm, and Run remains just outside the
unchanged limit at 0.002117 cm. The separate 1,600 fps skin experiment passes all clips: Walk 0.000780 cm,
Idle 0.000281 cm and Run 0.001235 cm. This isolates an additional sampling
contribution after the quaternion export repair. Neither diagnostic rate is a production
memory/performance recommendation.

The edited Human fixture grows from 9,876,068 to 9,943,036 bytes (about 0.7%).
Evidence: `artifacts/workflow-godot-human-dense/`; the 800 fps skin report is
preserved as `godot-skin-report-800.json`. Reproduce with the existing Human
fixture command and add `-- --diagnostic-import --bake-fps=1600` to `skin.gd`
for the higher-rate comparison.


Final repair evidence: the focused interpolation regression passes after proving
the original sparse mismatch; source keys remain unchanged. Two Godot diagnostic
argument guards also pass. The fixture was generated from the repair working
tree; its `commit` field names the pre-repair base, so use this change's PR/commit
for candidate provenance. Production Godot import settings, performance and live
visual acceptance remain open; the 800 fps skin Run case is retained as a failure.
