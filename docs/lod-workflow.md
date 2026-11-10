# LOD workflow implementation

## Current completion checkpoint (2026-11-09)

Target: complete the LOD release gates by November 30, 2026. This is a target,
not an acceptance claim. Earlier dated sections below are historical evidence;
use this checkpoint and source/tests to choose the next work.

Implemented: separate-copy static and skinned preview/apply, saved recovery,
multi-mesh static boundaries, GLB bundles, small-weight preservation through the
enabled add-on export hook, and default/contrasting Godot playback probes.
The old blanket small-weight export limitation is superseded by the supported
hook; disabled add-ons still fail closed for affected weights.

Package checkpoint (November 9): the isolated ZIP check now exercises registered
static Preview/Apply/Export operators and reimports LOD0/1/2 independently. It
checks manifest/import triangle agreement, decreasing counts, UV-layer and
material presence, source signature preservation, and export selection/staging
cleanup. The existing packaged skinned cancellation and tiny-weight hook checks
also pass on Blender 5.2.1. This small sphere fixture does not establish visual
UV/material fidelity, live keyboard undo or the full provider/import matrix.

Persistence checkpoint (November 9): `scripts/test_skin_lod_reopen.py` now
saves and reopens five skinned cases in a fresh Blender process. Unchanged
Apply/Discard pass; edits to source geometry, reduced geometry or rest bones
reject Apply without changing saved signatures. Discard remains available and
preserves the edited source/rig. Blender 5.2.1 passes all five cases. This is
backend persistence evidence, not live UI or arbitrary imported-rig acceptance.

Remaining completion gates:
- [ ] Resolve Human LOD UV cell mixing and animated thigh/knee surface artifacts;
  verify silhouette, UV/material and deformation quality on representative
  Human, Canine, Avian and imported assets. Normal transfer and global
  weight-gradient protection experiments were rejected; do not repeat them
  without a new hypothesis and a bounded comparison.
- [ ] Validate actual engine LOD selection, including level transitions and
  animated playback. Exchange bundles alone do not configure engine switching.
- [ ] Complete live Export workspace layout, preview/apply/discard and keyboard
  undo/redo acceptance. Background undo snapshots are supporting evidence only.
- [ ] Recheck saved/reopened and edited assets, import/export ownership and
  isolated packaged workflows for the final implementation.
- [ ] Record the precision policy and final evidence against the release roadmap;
  do not close artistic/manual gates based solely on CI.

Working schedule (adjust based on evidence; report slippage):
- November 9-15: resolve or isolate the UV/deformation blockers with bounded
  experiments, and implement/test engine selection independently where possible.
- November 16-22: integrate fixes, verify provider/import coverage and perform
  live UI/undo acceptance.
- November 23-30: regression, persistence, package and final acceptance review.

Hourly continuation checks account usage before substantive work, discovers the
current branch/PR rather than using a fixed historical branch, and advances the
next uncompleted gate. Batch findings with substantive changes instead of opening
one documentation-only PR per experiment. Required checks must pass before merge;
no release/tag publication is authorized by this milestone plan.

GitHub issue review: open issues #208, #220, #225, #228, #231 and #236 cover
import normalization, production readiness, glTF and model/animation workflows.
Their requirements inform integration testing, but are not evidence that an LOD
gate is complete. In particular #220 requires manual Blender evidence.

## Static preview backend (2026-10-24)

The first implementation slice is a backend, not a completed artist-facing LOD
feature. `object_core/lod.py` defines decreasing triangle budgets without Blender
imports. `blender_adapter/lod.py` builds separate reduced copies in an independent
collection. Source objects and meshes are not replaced or parented into LOD sets.

`preview_static_lods(mesh_object, active_scene, ratios=(0.5, 0.25))` returns a
persisted preview with explicit `apply()` and `cancel()`. Apply verifies the
source and preview geometry, world transform, UV data and material slots have not
changed, then retains the copies. Cancel removes only that preview's objects,
meshes and collection. Generation failures clean up staging data. Existing artist
materials are referenced, not rewritten or duplicated.

This slice supports one static mesh with at least eight source triangles and one
to four strictly decreasing budgets. It rejects modifiers, constraints, animation,
shape keys, skin groups and animated/constrained parent hierarchies. Mesh-level
animation is also rejected, and preview/apply require Object Mode so pending
Edit Mode geometry cannot bypass the checks. Each result
must meet its triangle budget, pass geometry inspection and retain UV layers and
material slots. Preserving layers/slots is not proof of visual UV/material quality.

Eleven Blender checks pass: source preservation/cancel cleanup, explicit apply,
stale-source rejection, unsupported-state rejection, edited-preview preservation,
failure rollback, mesh-level animation rejection, and Edit Mode preview/apply
blocking, renamed-reference recovery, foreign-content rejection and replaced-mesh
preservation. Seven core/architecture checks pass. A UV sphere with an
artist material exercises actual Blender reduction. These tests do not establish
arbitrary-topology, silhouette, texture or skinned-LOD acceptance.

## Remaining release work

- Validate the Export workspace controls visually and verify interactive undo.
  Operator selection preservation is tested.
- Add multi-mesh asset boundaries, quality/silhouette review and material/UV checks
  on representative generated and imported assets.
- Implement skinned LODs with explicit weight preservation/normalization and
  animated deformation validation; never silently apply this static path to rigs.
- Implement per-target export grouping and verify actual engine LOD selection.
- Run the release-roadmap visual, save/reopen, import/export and package gates.

Export workspace controls are available; automatic engine LOD configuration is not.
The LOD release gate remains open.

## Saved-preview recovery (2026-10-24)

Preview collections store a versioned manifest and Blender ID references to the
source, level objects and original level meshes. `recover_static_lod_preview`
reconstructs the handle after reopening, including renamed objects. Apply still
checks geometry signatures. Signatures use material names/library paths rather
than process-local pointers; renaming a material conservatively blocks apply.
Material node content is not fingerprinted.

Missing metadata, changed collection contents, relinked objects or replaced meshes
block recovery/mutation without deleting artist data. A handle cannot cancel a
preview applied through another handle. Unsupported old previews must be preserved
and rebuilt explicitly. Recovery never automatically applies or deletes objects.

`scripts/test_lod_reopen.py` saves material-bearing previews and verifies apply and
cancel in a fresh Blender process, preserving both sources. It passed on Blender
5.2.1 and runs in CI. Live UI, undo interaction and visual quality remain unverified.

## Export workspace controls (2026-10-25)

Select an unrigged static mesh, then use Export > Static LODs > Preview Static
LODs. The dialog offers one to four decreasing triangle ratios, defaulting to
50% and 25%. A ratio of 0.5 retains half the source triangle budget. Separate copies
retain the source selection. Each active scene preview shows its level triangle
counts and explicit Apply / Discard Preview controls, including recovered saved
previews. Discard asks for confirmation because edits to preview copies are lost.
A second preview for the same source is blocked until the first is resolved.

`lod_ui.py` decorates `workspace.export` through the presentation registry and
calls the existing validated backend. Operators declare Blender undo support;
interactive undo correctness still needs live validation. Thirteen focused Blender
tests pass, including actual preview/apply/discard operator calls, duplicate and
stale-source rejection, and selection preservation. Five architecture checks and
two full add-on registration/unregistration cycles pass. These checks do not
establish narrow-panel layout quality or engine export support.

## Undo snapshot evidence (2026-10-25)

`scripts/test_lod_undo.py` invokes the LOD operators and exercises Blender undo /
redo across Apply and Discard. Restored previews recover their source and level
references; source geometry remains unchanged. The isolated Blender 5.2.1 check
passes and runs as a separate CI step. Background scripts explicitly push undo
snapshots, so this does not certify automatic UI event pushes or Ctrl-Z behavior.

Fourteen focused Blender tests pass. Discard now rejects level meshes in Edit
Mode before deleting anything. Live UI review remains blocked locally: the
computer-use Node runtime failed initialization twice with a Windows sandbox
helper setup error. Layout, confirmation-dialog interaction and keyboard undo
still need live acceptance; they are not counted as passed by these tests.

## Configurable budgets (2026-10-25)

The preview dialog exposes level count and per-level source triangle ratios.
It calls the same core budget planner as the backend; increasing or duplicate
budgets are rejected before staging data. Sixteen focused Blender tests pass,
including a three-level operator preview and rollback-free invalid-input rejection.
Live dialog layout and keyboard interaction still require visual acceptance.

## Material overrides and UV coverage (2026-10-25)

Static LOD copies now use effective object material slots, including OBJECT-linked
material overrides. Only the independent LOD mesh receives those references;
source slot links and shared source meshes remain unchanged. Source/preview
signatures also inspect effective materials, so changing an override blocks Apply.
Existing previews whose override was previously ignored must be rebuilt explicitly.

Nineteen focused Blender tests pass, including shared-mesh override preservation,
stale override rejection and two UV layers with multiple face material assignments.
The fresh-process save/reopen check also passes with object-overridden materials.
These checks establish data preservation, not visual texture or silhouette quality.

## Surface deviation diagnostics (2026-10-25)

Each active preview level offers Measure Surface Deviation. The read-only action
samples vertices and triangle centroids from both source and level against the
opposite triangle surface using BVH nearest-point queries. It reports maximum
and RMS distances in world-space Blender units, plus sample count. Measurements
use current geometry, including edits; Apply still enforces stale-preview guards.

This is a finite sample diagnostic, not a Hausdorff bound, silhouette check,
texture assessment or automatic acceptance threshold. Unsampled detail may be
missed, and large meshes can take longer to inspect. No diagnostic work runs in
the panel draw callback. Twenty-two focused Blender tests pass, including equal
surfaces, translated surfaces, reduced spheres and non-mutating operator inspection.

## Static multi-mesh orchestration (2026-10-25)

`lod_sets.preview_static_lod_set` accepts an explicit list of distinct static
meshes in the active scene. It reuses the existing reduction and validation path,
applying budgets per mesh. Invalid members are rejected before staging; a failed
member removes completed staged previews. Apply and Cancel preflight every member
before changing any member, preventing partial completion on validation failures.

Twenty-six focused Blender tests pass, including second-member failure cleanup,
stale-source apply blocking, cancellation ownership blocking and source preservation.
This is backend orchestration: explicit member references now persist in a
separate record collection, and no asset membership is inferred.
Live multi-mesh UI acceptance, skinned LODs and export grouping remain
open. It does not yet implement an engine LOD hierarchy or whole-asset budget.

## Saved multi-mesh groups (2026-10-25)

`recover_static_lod_set` restores group membership using versioned collection ID
references. Renames are supported; missing/duplicate members and resolved records
are rejected without mutation. Group record collections must remain empty of
artist objects and child collections before Apply/Cancel. Individual preview
recovery remains available, but resolving a member independently blocks subsequent
group operations rather than partially completing the rest.

Twenty-eight focused Blender tests pass. `scripts/test_lod_set_reopen.py` also
passes in a fresh Blender 5.2.1 process: two two-mesh groups recover and complete
Apply/Cancel while preserving all four sources. This check is included in CI.

## Multi-mesh workspace controls (2026-10-25)

Enable All Selected Meshes in the preview dialog to create one group from the
explicit selection. Every selected object must satisfy the static mesh contract;
non-mesh selections are rejected rather than silently omitted. Ratios apply per
mesh, not to a pooled asset budget. Active-mesh mode remains the default.

The Export workspace lists group Apply/Discard controls and member diagnostics.
Individual member completion is blocked while its group is active. Group Discard
uses the existing confirmation flow. Thirty focused Blender tests pass, including
real selected-mesh operators, selection preservation, member blocking and group
cleanup. Live dialog layout and interactive undo acceptance remain open.

## Multi-mesh undo and selection checks (2026-10-25)

The existing CI undo script now covers group Apply and Discard as well as single
previews. Undo restores both members and their source references; redo restores
completion/removal, preserving source signatures and the explicit selection.
These Blender 5.2.1 snapshot checks pass; they still use explicit background undo
pushes and do not certify interactive keyboard dispatch.

Thirty-two focused Blender tests pass. Selected groups reject non-mesh helpers
without staging data and reject sources already carrying a preview. Live UI
acceptance, skinned reduction and destination/export support remain open.

## Skinned source admission (2026-10-25)

`lod_skin.inspect_skin_lod_source` reads normalized deform-bone weights and the
single enabled Armature binding without altering source data or pose. It rejects
missing/unnormalized weights, non-deform artist groups, envelope/masked deformation,
extra modifiers, mesh animation and shape keys. Four focused Blender tests pass.
This is admission validation only: skinned reduction, weight transfer, pose/clip
comparison and UI integration remain unimplemented.

## Packaged core resolution repair (2026-10-25)

PR #318 CI exposed a direct `object_core` import that failed when the add-on was
loaded from its isolated ZIP. LOD contracts now resolve through `core_gateway`,
including the multi-mesh backend. The repaired single-mesh branch passed the full
isolated package generation/rigging/animation/validation/export test locally; seven
core/architecture checks also passed. Remote CI must pass before merging.

## Rest-surface weight transfer planning (2026-10-25)

`lod_skin.plan_skin_lod_weights` computes normalized weights for an independent
static target without mutating either mesh. For each target vertex it locates the
nearest source triangle in world-space rest geometry, interpolates the triangle's
authored bone weights, and normalizes the result. The live armature pose is not
baked into the correspondence. Non-finite geometry and degenerate correspondence
triangles are rejected.

Six focused skinned-LOD checks pass, including analytically known two-bone weights
and source-pose/data preservation. This remains a planning API: it does not bind
or reduce the target, enforce a maximum correspondence distance, or establish
articulated motion quality. Closely adjacent surfaces may need constrained
correspondence before this can be accepted for character LODs.

## Bound skin candidates (2026-10-25)

`build_skin_lod_candidate` creates a new mesh/object from an independent static
derivative, transfers normalized weights, and binds it to the original armature.
It preserves effective target materials and the source preserve-volume setting.
Both inputs remain unchanged. The caller must provide a finite nonnegative
maximum rest-surface transfer distance; out-of-range targets fail before staging.
Construction failures clean up the new candidate only.

Eight focused Blender tests pass, including identical single-bone deformation at
three poses and distant-target rejection without leftover objects/meshes. This is
an internal candidate builder, not a completed preview/apply workflow. Actual
reduction, multi-bone character deformation, saved ownership, UI, and destination
acceptance remain open; nearby opposing surfaces can still need correspondence
constraints beyond distance alone.

## Reduced skinned candidates (2026-10-25)

`build_reduced_skin_lod_candidates` builds independent rest proxies, calls the
existing validated static reduction pipeline, and binds separate candidates using
the bounded transfer planner. Temporary proxies/previews are removed on success
or failure; a failed later level also removes completed candidates. Source mesh,
weights and rig remain artist-owned and unchanged.

The combined focused suite passes 43 tests (11 skin, 32 static/group). Actual
reduced candidates meet triangle budgets; a two-bone blended fixture matches
analytical linear-blend deformation at three poses within 1e-5 Blender units.
This checks binding mathematics, not fidelity to the unreduced animated surface.
Generated Human/Canine/Avian motion comparisons, persistent candidate preview/apply,
UI, visual acceptance and destination exports remain open.

## Generated-character Walk diagnostics (2026-10-25)

`scripts/review_skinned_lod.py -- <report.json>` generates default Human, Canine
and Avian assets, builds a 50% skinned candidate, and compares both posed triangle
surfaces at five Walk phases. Blender 5.2.1 completed all three cases:

| Provider | Source / reduced triangles | Largest sampled distance (Blender units) |
| --- | --- | --- |
| Human | 84,368 / 42,184 | 0.0158981 |
| Canine | 34,432 / 17,216 | 0.00391644 |
| Avian | 620 / 310 | 0.00926770 |

These are diagnostic observations, not accepted quality limits. Five sampled
phases do not prove continuous motion fidelity, contact preservation, silhouettes,
UV quality or other clips. The script records per-phase max/RMS values and reports
provider failures explicitly. Broader shapes/clips and visual review remain open.
After merging validated main, all 43 focused Blender and seven core/architecture
checks passed. PR #318 is merged; this branch preserves its packaged-import fix.

## Persistent skinned preview lifecycle (2026-10-25)

`lod_skin_preview.preview_skin_lods` stages candidates in an independent collection
with explicit Apply/Cancel and recoverable source/rig/object/mesh references.
Apply checks geometry, effective materials, normalized weights, armature identity,
rest-bone definitions, world transforms and preserve-volume mode. Pose changes are
allowed for inspection; rest-rig or weight edits block Apply. The lifecycle reuses
static preview ownership/cleanup checks and never replaces the source.

Fourteen skinned tests pass. `scripts/test_skin_lod_reopen.py` passes Apply/Cancel
in a fresh Blender process and is included in CI. Experimental skinned collections
use dedicated controls, separate from the static preview list. Animation
curve edits are not fingerprinted; this is a derivative workflow, not ownership of
the shared rig/actions. Live UI, broader clip quality and export gates remain open.

## Experimental skinned workspace controls (2026-10-25)

Export now offers Preview Skinned LOD for the active mesh. The dialog exposes a
single triangle ratio and maximum rest-transfer distance in Blender world units.
Candidates remain bound to the original rig so artists can inspect motion before
explicit Apply or confirmed Discard. Duplicate previews for the same source are
blocked. The static path remains separate and still rejects skinned meshes.

The combined focused suite passes 48 tests, including operator Apply/Discard,
selection preservation, duplicate blocking and wrong-selection rejection without
staged data. UI layout, confirmation interaction and keyboard undo are still
unverified live. Experimental controls do not close the motion/visual or export
release gates.

## Skinned undo, packaging and nine-clip diagnostics (2026-10-25)

The CI undo snapshot script now covers skinned operator Apply/Discard, recovering
valid rig references after undo and preserving the source skin signature after
redo. The isolated ZIP skinned preview/discard smoke test passes and has its own
CI step after package creation. Neither check certifies live UI keyboard behavior.

The diagnostic report schema is now version 2 with `clip_samples`. At 50%
triangles, five phases per clip completed for all nine default provider/clip pairs.
Largest sampled distances in world-space Blender units:

| Provider | Idle | Walk | Run / Flight |
| --- | --- | --- | --- |
| Human | 0.00206146 | 0.0158981 | Run 0.0188531 |
| Canine | 0.00231071 | 0.00391644 | Run 0.00391644 |
| Avian | 0.00789842 | 0.00926770 | Flight 0.0125554 |

These measurements are diagnostic, not pass/fail quality thresholds. Additional
shapes, denser sampling, contact/UV/silhouette review and engine playback remain
required. The generated report is local at artifacts/skinned-lod-all-clips.json.

## Current-pose inspection (2026-10-25)

Skinned preview levels offer Measure Pose, reusing the sampled surface-distance
calculation on evaluated source/candidate meshes at the current animation frame.
Both must bind to the same rig. The action does not change frame, pose, action or
geometry. It reports maximum/RMS distance in world-space Blender units; samples
are not continuous surface or motion bounds. Forty-nine focused Blender tests
pass after integrating main, including operator inspection with source/pose/frame
preservation. PR #321 passed all six checks and is merged.

## Explicit export scopes (2026-10-25)

`lod_export.plan_lod_export` reads applied single-mesh, grouped static and skinned
records into separate LOD0/source and reduced-level scopes. Each scope lists its
meshes, required armatures and current triangle count. Reduced scopes exclude
source meshes; multi-mesh groups combine matching level indices. No objects are
reparented and no files are written by this planning stage.

The planner requires current scene membership, intact saved references, applied
state, unchanged source/level signatures, supported geometry/skin bindings and
valid ordering/budgets. Artist edits are preserved but conservatively block this
path until the set is rebuilt/reviewed; no silent regeneration is performed.
Fifty-two focused Blender tests pass, covering group source exclusion, skinned rig
inclusion and edited-applied-data rejection. Destination serialization, engine LOD
thresholds/selection and artist-facing export controls remain open.

## Static GLB exchange bundles (2026-10-25)

`export_static_lod_bundle` writes LOD0 and each reduced scope as separate GLBs plus
`lod-manifest.json`. Temporary independent meshes use the existing Godot/static
adapter validation and export path; no hierarchy/metadata from the source is
reused to broaden the scope. Selection and active object are restored and staging
objects/meshes are removed. All files are staged before publishing into a new
directory; existing destinations are rejected. Failed writes remove only files
created by the operation. Skinned scopes are explicitly blocked for now.

Thirty-six static/group tests pass. Serialized GLB mesh and index-accessor counts
match each planned level, proving reduced files exclude the full-resolution source.
Injected export failure leaves no scene staging or destination directory. This is
an exchange bundle, not engine LOD configuration: the manifest explicitly records
`engine_lod_configured: false`. UI, destination import/selection, and skinned
animation export remain open.

## Bundle export controls and Blender reimport (2026-10-25)

Applied static previews/groups expose Export Static LOD Bundle. Choose an existing
parent directory and a new bundle folder name; existing destinations and path
traversal are rejected. Group members are listed through their group export entry.
The operator uses the same validated bundle backend and keeps skinned export blocked.

Thirty-nine static/group tests pass. Actual GLB reimport of all three levels
preserves mesh counts, triangle counts and translated world bounds within 1e-5
Blender units. The existing unapplied-scale export guard remains enforced and
leaves source transforms unchanged. These checks do not establish engine LOD
selection or live file-dialog acceptance; both remain open.

## Godot static exchange probe (2026-10-26)

PR #323 passed all six checks and is merged. The repeatable fixture script
`scripts/export_static_lod_review.py` runs in Blender background mode with
`-- OUTPUT_DIRECTORY` (a new directory). It exports an applied two-mesh group
through the production bundle writer and adds a minimal Godot project.
Run Godot headless with `--path OUTPUT_DIRECTORY --script` followed by the
absolute path to `scripts/review_static_lod_godot.gd`.

Blender 5.2.1 / Godot 4.7.2 completed all three levels: two meshes per level,
1,056 / 528 / 264 triangles. Direct GLTFDocument scene ingestion matches the
manifest; intentionally changing the expected LOD1 triangle count fails with
exit code 1. The probe removes any old success report before running and writes
`godot-lod-report.json` only after all levels pass.

This validates direct GLB ingestion, not Godot editor import settings, automatic
LOD selection, screen thresholds, materials/UV appearance or visual acceptance.
Skinned bundle export and live UI review remain open.

## Skinned export staging (2026-10-26)

`lod_skin_export.stage_skin_lod_level` creates temporary independent mesh and rig
data for one validated export scope. Armature modifiers target the copied rig;
weights and current-pose evaluated geometry are preserved. The source hierarchy
and data remain unchanged, and temporary datablocks are removed on success or
failure. Rigs with parents, constraints or drivers are conservatively rejected
because their external dependencies need an explicit export policy.

This is an internal staging helper, not a skinned bundle exporter. Active actions
and NLA are deliberately cleared on the temporary rig; clip selection and
serialization remain unimplemented here. Twenty focused skinned tests pass,
including posed-geometry parity, injected-failure cleanup and dependency rejection.

## Single-level generated clip serialization (2026-10-26)

`export_skin_lod_level` uses the existing Godot ANIMATED adapter to serialize one
staged skinned scope. Opt-in generated-clip staging retains only stable rig-ID
association, activates a generated action on the copy for normal validation,
and reuses the existing multi-clip staging/export path. Artist active actions,
NLA, drivers and unsupported rig dependencies are blocked rather than discarded.

Twenty-one focused tests pass. The serialized GLB contains one reduced mesh,
one skin, joint/weight attributes and both generated test clips. Source action,
slot, NLA and datablock sets are preserved. One run emitted a Windows access
violation diagnostic while still completing; a fresh repeat passed cleanly.

This is a single-level internal API. Bundle publication, generated rigs with
parent dependencies, playback parity, UI exposure and engine switching remain
open. It does not complete the skinned export release gate.

## Skinned bundle publication (2026-10-26)

`export_skin_lod_bundle` now routes each validated level through the generated-clip
serializer and shares static export staging/publication. Each level receives its
own GLB plus the existing manifest. Existing destinations are rejected and a
serializer failure, including one that writes a partial staged file, publishes
nothing. PR #324 passed all six checks and is merged.

The combined static/skinned suite passes 61 tests. Both source and reduced GLBs
contain the two expected test clips, skin joint/weight attributes, one mesh and
the exact manifest triangle count. Source action/slot/NLA and datablock sets are
preserved. Static export regression tests continue to pass.

This remains an internal API: parented rigs, engine playback parity, live UI and
artist-facing skinned export are not yet accepted. The manifest still reports
`engine_lod_configured: false`; separate files do not configure LOD switching.

## Static-parent skinned export support (2026-10-26)

A single rig may now have a chain of static Empty object parents. Export staging
places the effective parent transform (including the rig parent-inverse matrix)
on the temporary root and keeps the rig's local animation space unchanged.
Animated/constrained parents, non-Empty parents, bone parenting and multiple
parented rigs remain blocked. Source parent links are not changed.

Twenty-three focused skinned tests pass. A translated/rotated parent with a
nonidentity parent inverse preserves rig world matrices and evaluated mesh
vertices at five root-motion frames (1e-6 / 1e-5 tolerances). Both source/reduced
GLBs also export through the production bundle writer. An animated parent is
rejected. These checks establish staging parity and successful serialization,
not downstream engine playback parity; that remains open with UI acceptance.

## Skinned Blender playback round trip (2026-10-26)

The parented fixture now reimports its reduced GLB and compares evaluated
world-space vertex positions in both directions at five aligned clip frames.
Linear bone translation passes within 1e-5, including static parent rotation,
translation and parent-inverse offsets. Imported bone-display meshes are excluded
by selecting the mesh with an Armature modifier. Twenty-three skinned tests pass.

This test exposed a real armature-object animation mismatch: serialized object
motion can move imported skin differently from the unparented Blender source
mesh. Generated skinned LOD export now rejects non-bone action channels until an
explicit playback policy exists. Source actions remain untouched. The earlier
static-parent staging evidence alone did not prove this serialization behavior.

Bezier bone interpolation also differed at intermediate samples (about 0.00564
world units in this fixture); the passing test uses linear keys, matching the
intended generated-clip path. Bezier parity, additional rotation/scale clips,
Godot playback and live UI acceptance remain open; no broad playback acceptance
is claimed.

## Dense rotation round trip and interpolation admission (2026-10-26)

Skinned LOD clip admission now requires LINEAR or CONSTANT keys and rejects
non-CYCLES curve modifiers. Bezier keys are explicitly blocked following the
observed intermediate playback difference; the source interpolation remains
unchanged. This restriction applies to this internal LOD path, not the general
animation exporter. Non-bone channels remain blocked.

The parented reduced-level GLB round trip now combines linear bone translation
with quaternion rotation and checks 49 fractional-frame samples. Bidirectional
nearest-vertex distances remain below 1e-5 world units after reimport, allowing
GLB seam splits without assuming identical vertex indexing. The shared exporter
continues to provide quaternion densification; no alternative serializer was
introduced. All 62 combined static/skinned tests pass.

This fixture does not establish arbitrary-clip, scale-animation, Godot playback,
visual or UI acceptance. Bezier support requires a verified interpolation policy
before it can be enabled.

## Godot skinned bone-head probe (2026-10-26)

Run Blender background with `--python scripts/export_skin_lod_review.py -- NEW_DIR`
to create a two-level animated fixture, world-space oracle and minimal project.
Run Godot headless with `--path NEW_DIR --script` and the absolute path to
`scripts/review_skin_lod_godot.gd`. The probe uses direct GLTFDocument ingestion
with an explicit 800 Hz animation bake and retained reset tracks.

Blender 5.2.1 / Godot 4.7.2 pass 49 sample times on each of LOD0 and LOD1.
Maximum bone-head error is 2.4575624e-7 world units against a 1e-5 tolerance.
A deliberately displaced oracle head fails with exit code 1; restoring the oracle
passes. Old success reports are removed before each run.

The result covers one translated/rotated static-parent fixture and bone-head
playback only. It does not verify bone orientation, evaluated skin, arbitrary
providers/clips, editor import defaults, looping or visual quality. Those remain
separate release acceptance work.

## Godot orientation probe (2026-10-26)

PR #325 is merged; main is integrated into the follow-up branch. The skinned
fixture now records world-space bone basis columns converted from Blender world
axes into Godot axes, retaining the bone-local coordinate basis. The Godot probe
compares all three basis vectors as well as heads at 49 samples per level.
Both LOD0 and LOD1 pass: maximum head error 2.4575624e-7 world units and basis
vector error 6.3309113e-7, against 1e-5 tolerances.

An attempted evaluated-skin bake in this headless runtime fails because Godot
cannot register the mesh skin with a valid rendering skeleton. No skin success
is claimed and the committed probe remains skeletal only. Use the established
rendering-enabled skin workflow for that remaining acceptance gate.

## Rendering-enabled Godot skin probe (2026-11-01)

PR #326 passed all six checks and is merged. The fixture exporter now records
world-space evaluated vertices for each level and all 49 sample times. Run the
Godot probe with `-- --skin`, omit `--headless`, and use
`--rendering-method gl_compatibility` for the tested rendering path. A hidden,
off-screen process was used locally. Skin mode explicitly rejects headless mode.

The probe waits for render synchronization, bakes the current skeleton pose and
compares vertex clouds in both directions, tolerating seam duplicates. Blender
5.2.1 / Godot 4.7.2 with ANGLE pass both levels: maximum skin distances are
1.80494828e-6 (LOD0) and 1.69008342e-6 (LOD1), below 1e-5 world units.
Head and axis checks also pass. The local surface report is
artifacts/lod-skin-render-review/godot-skin-lod-surface-report.json.

This closes the previously blocked small-fixture rendered-skin probe, not the
broader release gate: additional providers/clips, fixed vertex correspondence,
between-sample behavior, visual review, UI acceptance and LOD switching remain
open. Vertex-cloud distance alone is not proof of topology or vertex identity.

## Fixed skin correspondence (2026-11-01)

The rendering-enabled probe establishes imported-to-source vertex correspondence
at the initial sample and reuses it throughout playback. Initial matches must be
within tolerance and cover every source vertex; changing vertex counts fails.
GLB seam duplicates may map to the same source vertex. Ambiguous/coincident source
vertices are conservatively rejected if full coverage cannot be established.

All 114 LOD0 and 58 LOD1 source vertices are covered across 49 samples. Maximum
fixed-correspondence errors remain 1.80494828e-6 / 1.69008342e-6 world units.
Swapping two reference vertex identities at sample 20 preserves the point cloud
but correctly reports a 1.41421-unit skin mismatch. Restoring the oracle passes.
This strengthens the previous nearest-cloud check without changing the tolerance.
The fixture still does not establish broad provider/clip or artistic acceptance.

## Two-bone blended-weight diagnostic (2026-11-01)

The fixture exporter accepts `--two-bones` after the output directory. It creates
a connected child bone with independent quaternion motion and two normalized
weights per vertex (root/child blend varying across the mesh). The existing
single-bone fixture remains the default. The Godot probe logs imported weight-sum
ranges and reports the file and measured initial correspondence failure.

The two-bone fixture is NOT accepted at the unchanged 1e-5 tolerance: LOD0 initial
correspondence error is 3.50925111e-5 world units. Godot mesh weight sums are
0.9999847114..0.9999847412, whereas serialized GLB float weights sum to approximately
1.0. This suggests destination weight quantization contributes to the error; it
is a diagnostic finding, not a completed root-cause fix. Source weights and
acceptance tolerances were not changed. Follow-up must establish destination
weight precision/normalization behavior before broad skinned export acceptance.

## Weight-sum isolation experiment (2026-11-01)

The probe accepts `--skin --normalize-baked-diagnostic` solely to isolate the
impact of imported weight sums. It divides each baked local vertex by its
imported weight sum before comparison, leaving mesh resources, GLBs, source
weights and the 1e-5 acceptance tolerance unchanged. Output is explicitly marked
diagnostic and uses a separate report filename; it must not be cited as export
acceptance or an import repair.

The two-bone initial mismatch falls from 3.50925111e-5 to 1.537857679e-5 world
units, still failing. Weight-sum deficit contributes but is not sufficient to
explain or repair the discrepancy. Further work must separate per-influence
quantization, bind transforms and the evaluated-mesh baking implementation.
No destination normalization or production exporter change is enabled.

## Corrected displacement-normalization diagnostic (2026-11-01)

`--identity-parent` removes the fixture parent translation/rotation to isolate
that contribution. The previous whole-position normalization still failed at
1.525878906e-5 in this configuration; the parent transform was not the sole cause.

Inspection of upstream Godot 4.5 mesh_instance_3d.cpp shows its bake algorithm
accumulating weighted displacement from each original vertex (lines 733-754):
https://github.com/godotengine/godot/blob/4.5/scene/3d/mesh_instance_3d.cpp#L733
This historical source is explanatory, not proof of the installed 4.7.2 build.
The diagnostic was corrected to use rest + (baked - rest) / weight_sum. The prior
whole-position experiment must not be interpreted as a valid normalization fix.

With corrected displacement normalization, the transformed-parent two-bone LOD0
passes initial correspondence and evaluates all 49 samples, but maximum skin
error is 1.841889571e-5, still above 1e-5. This narrows the remaining investigation
to per-influence precision and baking behavior; it does not certify acceptance.
No source weights, normal export behavior or tolerance were changed.

## Destination packing isolated (2026-11-01)

Run Godot headless against a generated bundle with the absolute script path to
`scripts/review_lod_weight_packing.gd`. It compares GLTFDocument ImporterMesh
weights with the resulting packed ArrayMesh and first requires identical vertex
and bone-index ordering. No meshes, weights or tolerances are modified.

Godot 4.7.2 two-bone results:

| Level | Imported vertices (including seam splits) | Maximum weight change | Error versus floor(w*65535)/65535 |
| --- | ---: | ---: | ---: |
| LOD0 | 480 | 1.356005669e-5 | 2.924252e-8 |
| LOD1 | 336 | 1.519918442e-5 | 2.964452e-8 |

ImporterMesh weight sums differ from 1 by at most 2.980232e-8; ArrayMesh minimum
sum is 0.9999847114. The single-bone control has zero weight change and unit sums.
This directly locates the precision loss at destination mesh packing and matches
16-bit downward quantization within float precision. It does not prove every
remaining playback error has that cause or define a production workaround.
The two-bone acceptance failure remains open at the unchanged 1e-5 tolerance.

## Sum-preserving destination packing experiment (2026-11-01)

`--skin --balanced-pack-diagnostic` constructs an in-memory ArrayMesh from the
original ImporterMesh floats, distributing 65,535 integer weight units by largest
remainder per vertex. It preserves the packed sum and uses a small interior-bin
float offset to survive downward packing. Source GLBs and Blender weights are
unchanged. This fixture-only replacement does not preserve the full production
material/blendshape contract and is not an import feature or acceptance mode.
It is mutually exclusive with normalized-bake diagnostics and writes a separate
report if it passes.

LOD0 packed sums improve to 0.9999999702..1.0, but maximum 49-sample fixed-vertex
error remains 1.50501437e-5 versus the unchanged 1e-5 tolerance. A unit weight sum
alone is therefore insufficient for this fixture. Per-influence rounding remains
a constraint; a production solution needs an explicit destination error budget
or a verified packing strategy. Two-bone acceptance remains open. Do not apply
this diagnostic replacement to artist assets.

## Complete per-level failure reports (2026-11-01)

PR #327 passed all six checks and is merged. The probe now writes explicit overall
and per-level pass flags, failure reasons and completed sample counts. Initial
correspondence tolerance failures stop that level without treating an uncertain
mapping as valid; remaining levels still run. Structural errors still abort.
Both success and measured-failure reports are written, with exit status reflecting
the overall result.

The balanced-packing diagnostic evaluates all 49 samples for both levels and
fails unchanged tolerance: LOD0 1.50501437e-5; LOD1 1.48916215e-5. Headless skeletal
control passes both levels. These reports preserve the distinction between a
completed diagnostic and accepted skin playback. No release gate was relaxed.

## Packing-only error bound (2026-11-01)

The weight-packing probe now records the maximum per-vertex sum of absolute
weight changes. For identical linear-blend transforms, the packing contribution
is bounded by `sum(abs(delta_weight)) * D`, where D is the maximum magnitude of
a bone-induced vertex displacement in the same coordinate space. This follows
from the triangle inequality applied to weighted displacements. It excludes
transform, interpolation and arithmetic errors and does not redefine acceptance.

Both two-bone levels have maximum L1 weight change 1.528859138e-5. Thus a uniform
D <= 0.654082495 world units would bound this contribution alone by 1e-5; no claim
is made that the actual fixture satisfies that displacement condition. Larger D
makes this conservative bound insufficient, not proof of failure. The single-bone
control has zero coefficient and reports a null displacement limit rather than
dividing by zero. Both fixtures ran successfully through the packing probe.

Next validation should measure actual per-influence displacement/packing error
alongside the Godot bake, separating it from residual transform or interpolation
error. The production two-bone gate remains unresolved and unchanged.

## Motion-level packing isolation (2026-11-01)

`scripts/review_lod_packing_motion.gd` is a rendering-enabled diagnostic against
an exported fixture directory. At every sample it reads the actual rendering
skeleton transforms and computes weighted displacements using both ImporterMesh
float weights and packed ArrayMesh weights, without editing either. It compares
the packed prediction with Godot's baked mesh and the float prediction with the
Blender oracle using fixed initial vertex correspondence.

Two-bone results across 49 samples:

| Level | Packing-only difference | Triangle-inequality bound | Bake/model residual | Float-weight/Blender error |
| --- | ---: | ---: | ---: | ---: |
| LOD0 | 4.46832928e-5 | 4.567492699e-5 | 2.731428e-7 | 2.05095421e-6 |
| LOD1 | 4.46832928e-5 | 4.567492699e-5 | 3.4240264e-7 | 1.93049141e-6 |

This isolates destination weight packing as the dominant observed error for this
fixture: the same transforms with original float weights are below 1e-5, while
the packing difference exceeds it and remains inside the calculated bound.
The single-bone control has zero packing difference. This is diagnostic evidence,
not a new rendering/export implementation or a relaxed acceptance threshold.
Production two-bone playback remains unaccepted; destination precision handling
or an explicitly justified error policy is still required.

## Four-influence coverage (2026-11-02)

The fixture exporter accepts `--four-bones` to build a connected four-bone chain,
four normalized weights per vertex and independent quaternion rotations on the
child joints. Existing one/two-bone options remain available. The interrupted
run's completed results were inspected after resuming. PR #328 passed all six
checks and is merged.

Across 49 samples, LOD0/LOD1 packing-only differences are 1.2454130047e-4 /
1.2462936866e-4 world units, within bounds of 1.3252036595e-4 / 1.3339605504e-4.
Bake/model residuals remain below 4.92e-7; original-weight/Blender errors remain
below 2.34e-6. ArrayMesh minimum weight sums are about 0.9999542, compared with
ImporterMesh sum errors below 2.99e-8. These results extend the evidence that
packing dominates this synthetic skin discrepancy; they do not accept the
four-bone result at the unchanged 1e-5 production gate.

Do not continue treating this as an unidentified Blender bind/animation defect.
Remaining destination work is a documented precision policy or verified packing
solution, followed by actual provider/clip and visual validation. No source
weights or acceptance thresholds were modified by these probes.

## Precision classification without acceptance relaxation (2026-11-02)

Motion diagnostic schema 2 separates `strict_passed` from `precision_explained`.
It measures the observed baked-minus-reference error vector and subtracts the
predicted packed-minus-original-weight vector at each corresponding vertex.
Unexplained residual, bake/model residual and the conservative packing bound
must meet their checks for the explanation result. Initial original-weight
correspondence must meet the existing tolerance; nonfinite vectors fail.

The four-bone levels retain strict failure at 1.252051734e-4 / 1.257806580e-4,
while unexplained residuals are 2.32395723e-6 / 2.38245866e-6. Both explanations
pass without changing the strict 1e-5 gate. Moving all LOD0 reference vertices
by 0.01 at sample 20 correctly makes its explanation fail; LOD1 stays explained.
The command exit status represents explanation validity, explicitly NOT release
acceptance. Reports retain the strict result so downstream review cannot treat
an explained loss as an accepted export. Source weights and rendering stay intact.

## Generated Avian fixture and influence preservation (2026-11-02)

`scripts/export_avian_lod_review.py` builds the default generated Avian with its
Flight action, a 50% LOD and per-level 49-sample skin oracle. The Godot probes
now read the oracle clip name, retaining ProbeMotion as the synthetic fallback.

The first real-provider export exposed Blender glTF warnings: vertices with more
than four influences were silently reduced to the four largest and normalized.
The internal skinned LOD export path now rejects positive influence counts above
four before staging that level. No authored weights are altered. All 24 focused
skinned tests pass, including unchanged weights/datablocks after rejection.
Re-running the Avian fixture now fails explicitly and publishes no bundle.

The earlier unguarded local Avian bundle is diagnostic only and must not be used
as accepted playback evidence. The next provider gate is an explicit higher-
influence destination policy or artist-reviewed weight reduction, followed by
Flight playback. This is separate from packed-weight numerical precision.

## Eight-influence preservation and Avian Flight (2026-11-02)

The skinned LOD-specific Godot adapter now requests Blender's all-influences
serialization and rejects more than eight positive weights before staging.
General export defaults are unchanged. The standard validation/export path is
reused; no silent truncation or source weight edits occur. Twenty-five focused
Blender tests pass, covering eight serialized joints plus JOINTS_1/WEIGHTS_1,
source preservation and rejection above eight influences.

The generated default Avian Flight bundle exports successfully. Godot confirms
four slots on LOD0 and eight slots on LOD1 with unchanged vertex/bone ordering
and influence-array sizes. Both levels pass the unchanged strict 1e-5 criterion
across 49 samples: observed errors 5.29300178e-6 / 5.39134317e-6; unexplained
residuals 3.8857473e-7 / 2.76401488e-6. This resolves the default Avian truncation
blocker and validates this clip/sample only. The synthetic multi-bone precision
limits, broader provider/clip coverage and visual/UI acceptance remain open.


## Default provider clip matrix (2026-11-02)

The fixture exporter now accepts `--provider avian|human|quadruped` and
`--clip Idle|Walk|Run|Flight`, keeping Avian Flight as its existing default.
Unsupported combinations fail before creating a bundle. Each fresh fixture uses
24 fps, the generated clip's explicit duration (Idle 4s, Walk/Flight 1.2s, Run
0.72s), strength 1, a 50% LOD and 49 evenly spaced evaluated samples. The rest
transfer bound remains 2% of the source bounding-box diagonal. Example:

```text
blender --background --factory-startup --python-exit-code 1 --python scripts/export_avian_lod_review.py -- artifacts/lod-human-walk --provider human --clip Walk
godot --path artifacts/lod-human-walk --rendering-method gl_compatibility --script /absolute/path/scripts/review_skin_lod_godot.gd -- --skin
```

Blender 5.2.1 / rendering-enabled Godot 4.7.2 (ANGLE) results, with the unchanged
1e-5 world-unit gate:

| Default fixture | LOD0 skin error | LOD1 skin error | Result |
| --- | ---: | ---: | --- |
| Avian Idle | 6.96463121e-6 | 7.00741248e-6 | Both pass all 49 samples |
| Avian Walk | 6.95263316e-6 | 6.98780241e-6 | Both pass all 49 samples |
| Human Idle | 2.80626136e-6 | 3.48528738e-6 | Both pass all 49 samples |
| Human Walk | 7.76472007e-6 | 7.65825462e-6 | Both pass all 49 samples |
| Human Run | 1.114901625e-5 | 1.067110406e-5 | Both fail initial correspondence |
| Canine Idle | 8.1742752e-7 | 8.1742752e-7 | Both pass all 49 samples |
| Canine Walk | 6.73262502e-6 | 1.261931448e-5 | LOD0 passes; LOD1 fails initial correspondence |
| Canine Run | 7.84810345e-6 | 1.202715703e-5 | LOD0 passes; LOD1 fails initial correspondence |

Pass rows report maximum sampled error. Initial-failure values are the first
rejected correspondence distance, not a maximum over the clip; those levels
have zero completed samples and must not be treated as playback acceptance.
The earlier default Avian Flight result remains documented above. Successful
correspondence covers every source vertex (Avian 312/157, Human 42186/21094,
Canine 17218/8610 for LOD0/LOD1). Each level is compared with its own Blender
oracle; this does not measure reduced-mesh visual fidelity against LOD0.

The original-float-weight motion diagnostic also rejects initial correspondence
for Human Run and Canine Walk/Run. These failures cannot be classified solely as
Godot packed-weight loss. Investigate source-to-export/import pose precision
and LOD skin transfer before choosing any precision policy; the strict gate is
unchanged and these clips remain unaccepted.

### Correspondence review performance and safeguards

The strict review now indexes reference points in tolerance-sized spatial cells
and searches all 27 neighboring cells. It retains nearest-distance selection,
lowest-index ties, fixed correspondence throughout playback, full source-vertex
coverage and the original tolerance. Scalar double-precision cell division
avoids premature Vector3 rounding. On rejection only, an exhaustive fallback
retains the exact distance diagnostic. The motion packing diagnostic reuses
the same lookup. This removes the quadratic successful initial search that
required roughly 1.8 billion comparisons for the default Human LOD0.

`scripts/test_lod_correspondence.gd` compares the lookup with exhaustive search
on 916 deterministic queries, including ties, duplicate points, negative cell
boundaries and rejected points. Run with Godot `--headless --script` and the
absolute script path. It passes; repeated Avian results are numerically identical.
The synthetic four-bone motion diagnostic also reproduces its prior numerical
results and strict-fail/precision-explained classification exactly.
A copied Avian Idle oracle shifted by 0.01 on LOD0 correctly fails initial
correspondence while untouched LOD1 passes. Production meshes, weights and
export tolerances are unchanged. Remaining gates include these failed clips,
contrasting shapes, material/UV inspection, live UI/undo and visual acceptance.


## Small-weight export guard (2026-11-02)

Historical guard baseline; the supported preservation path below supersedes
unconditional rejection when the add-on extension is enabled.

Blender 5.2.1's bundled glTF `PrimitiveCreator.__get_bone_data` hard-codes
`min_influence = 0.0001` and skips weights at or below it. The all-influences
option does not disable that cutoff. The preceding investigation in
[PR #335](https://github.com/jhodges0845/Asset-Assistant/pull/335) reproduced the
initial-pose failures through Blender reimport and isolated the cutoff using
unchanged GLBs with separately regenerated, cutoff-adjusted references.
Original-float-weight residuals across 49 samples fell below 2.20e-6 for Human
Run and 4.34e-7 for Canine Walk/Run. Those altered references were diagnostics,
not acceptance of the original assets.

The generated-clip LOD staging path now rejects any positive source/LOD weight
at or below 0.0001 before allocating that level's temporary hierarchy. The error
identifies the LOD, mesh, vertex, bone and weight. The existing bundle transaction
discards earlier staged levels and publishes no bundle. Neither weights nor
artist data are normalized, clamped or pruned by this guard. Non-serialized
preview/pose staging continues to retain small weights.

Twenty-nine focused Blender tests and seven core/architecture tests pass.
Regressions cover weights 1e-8, 5e-5 and 1e-4, unchanged data/selection after
rejection, no published files, and real GLB preservation just above the cutoff
(1.000001e-4), alongside existing one/eight-influence serialization checks.
Fresh default Avian Flight and Human Run fixtures fail explicitly and leave no
bundle: Avian first reports a LOD1 spine weight about 8.24e-7; Human first reports
a LOD0 upper-leg weight about 1.10e-5. Fresh Canine Walk and Run likewise
fail at LOD0 on a hind-lower-leg weight about 8.88e-6, without publishing.

This is prevention of silent loss, not a weight-preserving serializer. Even
previously passing sampled clips may be blocked if they contain such weights.
Next work must establish a supported preservation route (or an explicit,
reviewable weight-preparation workflow) and rerun the original provider/clip
oracles. Do not patch the user's Blender installation, silently edit authored
weights, or relax the 1e-5 playback threshold to bypass this limitation.


## Supported small-weight preservation (2026-11-03)

`blender_adapter/lod_weight_export.py` uses Blender's supported glTF
`gather_mesh_hook`, discovered through the enabled add-on's lazy
`glTF2ExportUserExtension` factory. It runs only inside skinned LOD exports that
contain positive weights <= 0.0001. Ordinary exports retain their defaults.
The existing source checks, generated-animation preparation, Godot adapter and
transactional bundle publication still run.

Temporary copied meshes receive a unique vertex-index attribute. The hook uses
that index after material/normal/UV splitting to restore every validated
influence through Blender's normal accessor writer, mapping names to exported
skin joints. Weights are normalized for serialization without pruning or
changing artist data. The marker is removed from the output; other custom
attributes remain disabled by default. At most eight influences are supported.
Invalid mapping, unsupported accessors, missing surface coverage, unrepresentable
weights, a missing hook or a critical hook error rejects the bundle. With the
add-on disabled, the original pre-staging small-weight guard remains active.
No Blender installation code or user preferences are patched by production export.

Regression coverage includes 1e-8/5e-5/1e-4 weights, eight distinct per-vertex
influences across two materials, disabled/missing/failing hooks, damaged
provenance, no partial publication and unchanged source data. The isolated
release ZIP test enables `humanoid_blender` and checks actual GLB tiny weights;
the provider review script enables the source add-on in its factory runtime.

Fresh Blender 5.2.1 bundles pass rendering-enabled Godot 4.7.2 review against
original, unmodified Blender oracles. Each row covers all 49 samples at each
level, fixed correspondence and every source vertex. The tolerance stays 1e-5.

| Default fixture | LOD0 maximum skin error | LOD1 maximum skin error |
| --- | ---: | ---: |
| Human Idle | 2.13571911e-6 | 2.14286774e-6 |
| Human Walk | 7.76472007e-6 | 7.65825462e-6 |
| Human Run | 9.73212354e-6 | 9.58019518e-6 |
| Canine Idle | 8.1742752e-7 | 8.1742752e-7 |
| Canine Walk | 3.80570077e-6 | 4.05355559e-6 |
| Canine Run | 4.43025829e-6 | 4.74942817e-6 |
| Avian Idle | 6.96463121e-6 | 7.00741248e-6 |
| Avian Walk | 6.95263316e-6 | 6.98780241e-6 |
| Avian Flight | 5.29300178e-6 | 5.39134317e-6 |

All nine default provider/clip pairs pass. Local evidence is under
`artifacts/lod-<provider>-<clip>-hook` (Canine uses `quadruped`).
Validation also passed 81 focused Blender LOD/target tests, seven core/architecture
tests and the isolated release ZIP weight-export check.
These results resolve the cutoff-related default-clip failures above. They do
not establish broad shape coverage or reduced-mesh visual fidelity. Synthetic
multi-bone Godot weight-packing failures remain a separate precision-policy gate.
Next: contrasting shapes and material/UV review; live UI/undo and actual engine
LOD switching remain required release gates.


## Contrasting-shape playback and surface inventory (2026-11-03)

`export_avian_lod_review.py --sample contrasting` now reuses the established
`SAMPLES` in `scripts/anatomy_baseline.py`; `--sample default` retains the prior
behavior. `expected.json` records the selected sample and all resolved provider
parameters, making each oracle reproducible without inferring shape from a name.

Fresh Blender 5.2.1 / rendering-enabled Godot 4.7.2 probes pass both LOD levels,
all 49 samples, fixed correspondence and full source-vertex coverage at 1e-5:

| Contrasting fixture | Review parameters | LOD0 maximum skin error | LOD1 maximum skin error |
| --- | --- | ---: | ---: |
| Human Run | height 155 cm, weight 65 kg, average body | 8.38695814e-6 | 8.45033810e-6 |
| Canine Run | body length 95 cm, shoulder height 40 cm, width 28 cm, head 30 cm, tail 50 cm | 3.23242739e-6 | 3.37832694e-6 |
| Avian Flight | body length 55 cm, width 22 cm, height 28 cm, wingspan 140 cm, tail 35 cm | 7.98457859e-6 | 7.73053762e-6 |

Evidence: `artifacts/lod-{human-contrasting-run,quadruped-contrasting-run,avian-contrasting-flight}`.
This is three contrasting provider/clip cases, not a complete contrasting clip
matrix or parameter-range certification. No production mesh, rig, clip,
export behavior or acceptance tolerance changed in this review step.

The script also writes `surface-inventory.json` with source/LOD vertex and
triangle counts, UV-layer names, material slots and per-material triangle
counts. It reads each generated GLB and requires matching per-material triangle
counts, triangle primitives, material references and finite, nonempty FLOAT
VEC2 UV accessors matching the position count and staying inside their buffer
views. It records exported UV bounds. All six contrasting surfaces pass these
structural checks; all retain one UVMap and their generated base material.

Five focused Blender diagnostic tests pass, including rejection of missing UVs,
non-finite UVs, mismatched counts and truncated UV buffer views. A fresh final
Avian CLI export and the three actual fixture bundles pass the inventory check.
The checks detect missing/malformed export data; they do **not** compare UV
corner correspondence, texture appearance, seam distortion, or source-to-LOD
silhouette quality. Those visual/fidelity gates remain open, alongside the
remaining contrasting clips, synthetic packed-weight policy, live UI/undo and
engine LOD switching.


## Paired imported-LOD visual review (2026-11-03)

`scripts/render_lod_review.py` imports each level of an existing two-level
skinned GLB bundle into a disposable Blender scene. It freezes both at the
same normalized clip phase (or rest pose when `--clip` is omitted), preserving
imported UV layers, and renders front, side and three-quarter views. Each
LOD0/LOD1 pair shares its scale and positional offsets so the sheet does not
normalize away silhouette differences. Clay, UV-checker and silhouette sheets
use diagnostic material overrides; they do not validate original material or
texture appearance. `review.json` records file hashes, sampled frames, imported
triangle counts, UV layers and original material names.

Example (run in a separate factory-startup process; the script clears its scene):

```powershell
blender --background --factory-startup --python-exit-code 1 `
  --python scripts/render_lod_review.py -- `
  artifacts/lod-avian-contrasting-flight `
  --output artifacts/lod-visual-avian-flight-review --clip Flight --phase .25 --samples 8
```

The output directory must be new. The script rejects missing/ambiguous clips,
missing UVs, imported triangle counts differing from the manifest, unexpected
level layouts, and off-camera geometry. This is a sampled diagnostic, not an
automatic artistic quality score or proof of UV corner correspondence.


The contrasting Avian Flight sample at phase 0.25 (620 to 310 triangles) retains
its broad wing/body/tail outline. Paired clay and silhouette sheets show visible
changes around wing roots and body contours; the checker sheet shows uneven
cell scale and local changes around those transitions. These observations do
not establish whether a difference originated in decimation or source UVs;
corner-level comparisons and closer seam review remain required. Evidence:
`artifacts/lod-visual-avian-flight-v2/{clay,checker,silhouette}.png` and
`review.json` (Blender 5.2.1, Cycles CPU, eight samples).

Two focused real-GLB regression checks verify rest-pose snapshot world-space
geometry, UV coordinates, input-file hash preservation, imported-object cleanup,
and missing-clip rejection. They and the five structural surface-inventory
checks pass (seven tests). No production mesh, rig, export behavior, or quality
tolerance changed.


Contrasting Human Run at phase 0.25 (84,368 to 42,184 triangles) is **not visually
accepted**. The paired clay sheet exposes pronounced jagged shading around the
LOD1 thighs/knees; the checker sheet shows substantial pattern changes over the
torso and limbs. The LOD0 checker already has strongly uneven cell aspect ratios,
so both source UV quality and reduction/export fidelity need separate review.
Evidence: `artifacts/lod-visual-human-run/{clay,checker}.png`. Passing per-level
skin-oracle checks does not establish visual equivalence to LOD0. Next diagnosis:
compare rest/posed surface normals and UV corners before/after reduction and
GLB round-trip; isolate shading from geometry with the silhouette sheet before
changing rig/weight behavior. Keep Human LOD artistic acceptance blocked.


### Uniform-lighting follow-up (2026-11-04)

The review renderer now uses directional lights with cast shadows disabled so
LOD0 and LOD1 receive the same illumination regardless of their row position.
This removes the earlier area-light distance/direction bias. `--width` controls
output resolution (default 1800, minimum 512); width, samples and lighting are
recorded in `review.json`. Use `--width 1000 --samples 8` for a faster overview,
then larger sheets for close inspection. This changes diagnostic rendering only.

Completed clay, checker and silhouette sheets for contrasting Human Run, Canine
Run and Avian Flight at phase 0.25, using Blender 5.2.1 and width 1000. Evidence:
`artifacts/lod-visual-{human-run,quadruped-run,avian-flight}-uniform/`.
Human thigh/knee shading artifacts and substantial checker-pattern changes
persist with uniform lighting; Human visual acceptance remains blocked. Its
broad silhouettes remain close at this sampled pose, so normals and UV handling
are the next investigation before changing skin behavior. Canine and Avian
retain their broad outlines with local contour/checker differences; this is
not close-up seam approval, continuous-playback acceptance or original-material
validation. All existing release gates remain in force.


A fresh contrasting Human reconstruction localizes this sample further. At rest,
all 84,368 LOD0 and 42,184 LOD1 triangles matched their imported GLB triangles by
centroid and vertex positions (no unmatched triangles). Maximum matched position
error was 4.09e-7 m and UV-coordinate error 2.99e-8 at both levels. Maximum corner
normal-vector differences were 0.00197 (LOD0) and 0.000540 (LOD1). Evidence:
`artifacts/diagnose_human_lod_stages.py`, `artifacts/lod-human-stage-diagnosis.json`.
This is a diagnostic for these exact fixtures, not a new acceptance tolerance.

Both fresh source levels have zero smooth polygons and no custom normals.
HumanProvider deliberately calls `_generate_face_atlas_uvs` in
`object_core/geometry/deformable.py`: each polygon has its own padded island,
intended as a portable foundation rather than continuous production UVs. LOD
collapse therefore operates on an already discontinuous atlas and flat-shaded
surface. The observed checker changes must not be labeled GLB UV corruption;
these rest-pose checks preserve the source/LOD corners through export/import.
Next work is a Human-specific UV continuity and shading policy, plus reduction
fidelity checks against that policy. Preserve existing artist UVs and explicit
preview/apply behavior; do not silently enable smoothing or re-unwrap saved
assets. Rigs/skin tolerances do not need speculative changes for this finding.


### Human atlas reduction measurements (2026-11-05)

`scripts/review_human_lod_atlas.py` now reproduces the atlas diagnosis on fresh
Human geometry through the same static reduction path used by skinned rest
proxies. It verifies the source polygon-index atlas layout before interpreting
cells, then reports triangles whose corners occupy different original cells,
triangles outside the padded atlas's [0,1) domain, exactly zero UV-area triangles,
and smooth-polygon counts. It never changes source UVs or smoothing.

```powershell
blender --background --factory-startup --python-exit-code 1 `
  --python scripts/review_human_lod_atlas.py -- `
  --output artifacts/human-lod-atlas-review.json --sample contrasting
```

Fresh Blender 5.2.1 results (each cell lists default / contrasting counts):

| Budget | Triangles | Cross-cell triangles | Outside-atlas triangles | Zero UV-area triangles |
| --- | ---: | ---: | ---: | ---: |
| Source | 84,368 | 0 / 0 | 0 / 0 | 2 / 2 |
| 50% | 42,184 | 701 / 700 | 0 / 0 | 2 / 2 |
| 25% | 21,092 | 1,021 / 1,020 | 2 / 2 | 2 / 2 |

All levels remain flat-shaded. Evidence:
`artifacts/human-lod-atlas-{default,contrasting}-final.json`.
Nine focused diagnostic regressions and seven related visual/inventory checks
pass. Tests cover input preservation, crossed cells, out-of-domain coordinates,
collapsed UVs, invalid grids, missing/nonfinite UVs and a repacked source atlas
that must not be interpreted using the generated face-index layout.

These are measurements, not new quality tolerances. A triangle staying within
one cell can still be distorted, moved to the wrong cell, or overlap another UV
triangle; this metric cannot certify UV fidelity. The two zero-area source UV
triangles predate reduction. The next repair must address source atlas quality
and reduction fidelity separately, preserving artist-authored UVs and explicit
preview/apply ownership. Human LOD visual acceptance remains blocked; no rig,
weight, production geometry or export change is included in this diagnostic.


### Human source projection repair (2026-11-05)

Fresh current-Human generation now opts into a projection fallback when a
face's two widest axes collapse a possible triangle. It tests normalized areas
for all corner triplets (covering either quad diagonal), and uses an alternate
axis pair only when that pair is nondegenerate. Unaffected projections retain
bit-identical UVs; unrepairable geometry retains its existing mapping rather
than being silently reshaped. Legacy Human generators retain the old default.
This is not a general-purpose unwrap or smoothing change.

Only atlas polygons 35564 and 42481 change in the neutral Human surface. All
vertices, faces and other UV islands remain identical. Both reference shapes
now have zero exactly collapsed UV triangles in Blender float32 storage, at
source, 50% and 25% budgets. Cell-crossing counts remain 701/700 at 50% and
1,021/1,020 at 25%; the two outside-atlas triangles at 25% remain. Evidence:
`artifacts/human-lod-atlas-{default,contrasting}-fixed.json`.

Six core UV tests and 15 focused Blender UV/atlas/parameter-regeneration tests
pass. Regressions cover scale independence, valid/unrepairable projections,
legacy behavior, exactly two changed islands and actual Blender triangulation.
Existing saved meshes are not migrated or rewritten on load; the corrected UVs
are produced by fresh generation or explicit geometry regeneration. Rig, skin,
shading and export behavior are unchanged. Human LOD artistic acceptance stays
open pending cell-mixing, out-of-atlas and shading repairs.

### LOD shading ownership (2026-11-06)

Static and skinned LOD fingerprints now include sharp-edge flags and custom
corner normals. Editing either the source or a preview after preview creation
blocks Apply without changing the edited data. Unchanged custom normals survive
save/reopen and recovered-preview application. Meshes without authored shading
retain their historical fingerprints; older previews with sharp edges or custom
normals must be explicitly rebuilt because their old fingerprints cannot certify
that shading remained unchanged.

Validation: 83 focused static/skinned LOD tests pass in Blender 5.2.1. A real
save/reopen probe also verifies fingerprint stability, rejection of an old shaded
preview fingerprint, and source preservation. Local evidence:
`artifacts/lod-shading-ownership-tests.log` and
`artifacts/lod-shading-persistence.log`.

A separate reduction experiment toggled collapse triangulation and the UV
delimiter at 50% and 25% budgets. Neither changed the measured atlas damage:
701/1,021 crossed-cell triangles and 0/2 outside-atlas triangles for default
Human. Evidence: `artifacts/lod-uv-settings-probe.json`. These settings do not
resolve the current UV defect. Source-to-LOD normal transfer remains an
experiment to evaluate visually; this ownership change does not introduce
smoothing or establish Human LOD artistic acceptance.

### Human LOD normal-transfer experiment (2026-11-07)

PR #345 merged with all six checks passing. A subsequent disposable experiment
transferred nearest-rest-surface corner normals onto a fresh contrasting Human
50% candidate before preview fingerprints were captured. The existing candidate
builder, preview/apply validation and GLB exporter remained in use. Assertions
verified unchanged source fingerprint and unchanged candidate positions,
topology, UVs and skin weights. This experiment is not production behavior.

The imported GLB confirms that normal changes survived export: all 42,184
triangles matched the earlier LOD geometry; 94,265 of 126,552 corner normals
changed by more than one degree (median 4.47 degrees, p95 12.33 degrees).
Nevertheless, the paired Run render at phase 0.25 still shows pronounced thigh
streaks. The neutral clay render does not show the same pronounced streaking.
Normal transfer alone therefore does not resolve this sampled motion defect.

A nearest-rest-surface displacement interpolation diagnostic found only three
triangles with normal-direction differences above 30 degrees, all above 90
degrees and extremely thin in rest geometry. This correspondence is not ground
truth and does not explain the broad visible defect by itself. Next investigate
how reduced triangles span the deforming thigh/knee surface, including evaluated
normals, rather than accepting a rest-only normal-transfer correction. UV cell
mixing remains independently unresolved; no quality thresholds were relaxed.

Local reproduction/evidence:
- `artifacts/probe_lod_normal_transfer.py` creates the experimental bundle using
  the current provider/export helper sequence and a temporary candidate wrapper.
- `artifacts/lod-normal-transfer-export.log` records preservation assertions.
- `artifacts/compare_lod_normal_transfer.py` and
  `artifacts/lod-normal-transfer-comparison.json` compare imported rest normals.
- `artifacts/lod-visual-human-normal-transfer/` contains Run review sheets;
  `artifacts/lod-visual-human-normal-transfer-rest/clay.png` is the neutral review.
- `artifacts/probe_lod_triangle_deformation.py` and
  `artifacts/lod-triangle-deformation.json` record the interpolation diagnostic.

These ignored local artifacts are investigation evidence, not portable CI
fixtures or an artistic acceptance claim.

### Evaluated LOD normal review (2026-11-07)

`scripts/review_lod_normals.py` compares imported evaluated corner normals with
geometric triangle normals. It reports angular median/p95, opposing corners,
degenerate triangles and the 20 largest triangle discrepancies. It reads bundle
GLBs without rewriting them and records their hashes. This is a diagnostic,
not a shading-quality threshold; smooth normals need not match face normals.

Run in a disposable Blender process:
```
blender --background --factory-startup --python scripts/review_lod_normals.py -- BUNDLE --clip Run --phase .25 --output NEW.json
```
Omit `--clip` for neutral geometry. Existing output files are rejected.

On the contrasting Human baseline, LOD1 corner normals closely follow triangle
faces in both neutral and Run phase .25 (p95 about .026 degrees; no opposing
corners). The temporary nearest-surface transfer instead introduces 354 opposing
corners in neutral and 356 during Run. It must not be adopted as a production
repair. Local measurements: `artifacts/lod-corner-face-normal-review.json`;
the new CLI was also exercised against the actual transferred Human GLBs.

A separate diagnostic averaged area-weighted normals at coincident evaluated
positions (rounded to six decimal places), leaving positions and UVs unchanged.
The resulting Run clay view reduces fine thigh streaking but retains broader
thigh grooves. This is sampled visual evidence, not a general smoothing policy:
coordinate grouping can cross authored hard boundaries. The next repair still
needs to address reduced-surface deformation and preserve source shading intent.
Evidence: `artifacts/probe_lod_posed_normals.py`,
`artifacts/lod-visual-posed-normal-average/clay.png`.

Six focused normal/snapshot tests pass in Blender 5.2.1, including aligned,
opposing and tilted authored normals, unchanged input mesh data, and degenerate
triangles reported separately from measured agreement. No production geometry,
weights, UVs, normals or acceptance tolerances change in this diagnostic addition.

### Weight-gradient reduction experiment (2026-11-07)

A disposable contrasting-Human Run experiment assigned Decimate importance from
adjacent source skin-weight differences: each vertex used its largest incident
edge L1 weight difference, multiplied by five and clamped to one, with modifier
vertex-group factor 100. Temporary groups were removed from the evaluated copy
before existing static/candidate validation. Source fingerprints and skin
weights were asserted unchanged; preview/apply and export validation remained
active. Both baseline and candidate contain exactly 42,184 triangles.

The phase-.25 clay comparison reduces some thigh streaking but introduces more
visible neck/elbow artifacts. Imported UV measurements also regress: crossed
atlas-cell triangles increase from 700 to 918, and outside-atlas triangles from
zero to two; neither candidate has exactly collapsed UV triangles. The baseline
UV comparison uses the earlier normal-transfer bundle, whose UVs and geometry
were independently verified unchanged. Imported polygon smoothing flags are not
source shading-policy measurements.

Do not adopt this weighting scheme or relax quality checks. Skin-weight change
alone is insufficient to allocate the reduction budget across the whole body.
Further work needs to assess posed surface error alongside UV preservation;
protecting one region must not simply move visible damage elsewhere. Human LOD
visual acceptance remains open.

Local evidence: `artifacts/probe_lod_weighted_reduction.py`,
`artifacts/lod-weighted-reduction.log`,
`artifacts/lod-weighted-uv-comparison.json`, and
`artifacts/lod-visual-human-weighted-reduction/clay.png`. This experiment changes
only disposable process-local reduction settings and generated artifact copies;
production reduction remains unchanged. PR #347's normal diagnostic is merged
with all six CI checks passing.

### Rendered Godot level selection (2026-11-09)

`scripts/review_lod_selection_godot.gd` imports a two-level bundle into a
rendering-enabled diagnostic viewport and configures Godot visibility ranges.
It gives each level a distinct unshaded color, moves an orthographic camera
near/far/near/far, and counts rendered pixels to require the expected level and
exclude the other. A common world-space AABB keeps selection distances consistent
across meshes. Imported mesh/triangle counts must match the manifest; GLBs and
the exchange manifest are never rewritten. Existing reports are rejected.

Run against a disposable bundle copy containing a Godot project:
```
Godot --path BUNDLE_COPY --script /absolute/review_lod_selection_godot.gd --rendering-method gl_compatibility --resolution 128x128 --quit-after 600
```
Use a real rendering driver, not the headless dummy renderer. Success produces
`godot-lod-selection.json`; a process exit alone is not proof of success.
The report records the Godot version and pixel counts for each camera position.

Contrasting Human, Canine and Avian bundles pass on Godot 4.7.2 using ANGLE.
A negative control hiding LOD1 fails at the far sample with no colored pixels,
confirming that the probe detects a missing level. Local evidence is under
`artifacts/lod-selection-{human,canine,avian}/` and the corresponding logs;
`artifacts/lod-selection-negative-stderr.log` records the expected failure.

This closes only the sampled rest-pose selection proof. The probe configures a
temporary scene; exported bundles still advertise `engine_lod_configured: false`.
A persistent artist-facing engine setup, animated level transitions, boundary
behavior and visual transition acceptance remain open. Production geometry,
materials and skinning are unchanged. Visibility-range semantics follow the
[Godot documentation](https://docs.godotengine.org/en/stable/tutorials/3d/visibility_ranges.html).

### Animated phase and boundary selection (2026-11-09)

The Godot selection probe accepts an optional exact clip name after `--`, e.g.
`-- Run` or `-- Flight`. Each imported level must have one skeleton and one
AnimationPlayer containing that clip. Players use manual evaluation at normalized
phases 0, .25, .5 and .75, and sampled bone poses must change on both levels.
At every phase, the camera approaches and retreats through distance multipliers
.8, .99, 1.01, 1.2, 1.01, .99 and .8 relative to the shared selection boundary.
The existing rendered-color check requires exactly the expected level.

Contrasting Human Run, Canine Run and Avian Flight each pass all 28 rendered
samples on Godot 4.7.2/ANGLE. Rest mode still passes seven distance samples.
A missing clip fails admission; a diagnostic frozen-seek control fails because
bone poses do not change. Reports and logs are under
`artifacts/lod-animated-selection-{human,canine,avian,rest,frozen,missing}`.
The frozen/missing controls intentionally produce no success report.

This is synchronized sampled-phase selection, not continuous playback,
frame-perfect visual continuity, hysteresis/fade acceptance or persistent engine
configuration. Different levels are sampled at the same normalized phase; this
does not certify their clip durations or skin parity. Existing playback parity
probes remain required. Exact-boundary tie behavior is not asserted. PR #349
passed all six CI checks and was merged before this extension.

### Saved Godot selection scene (2026-11-09)

The selection probe now saves `lod-selection-review.tscn`, reloads it with the
PackedScene cache bypassed, discards the original instantiated nodes, and performs
all rendered selection checks on the restored nodes. Recursive scene ownership
retains imported descendants; stored node paths recover meshes, skeletons and
players. Missing nodes/clips and changed visibility begin/end values fail before
render review. Existing scene or report files block the run rather than being
overwritten. The GLBs and exchange manifest remain unchanged.

Human Run, Canine Run and Avian Flight each pass 28 rendered checks after reload;
rest mode passes seven. A negative control that changes LOD1's saved begin range
fails with `Saved LOD visibility ranges changed`. Evidence:
`artifacts/lod-persisted-selection-{human,canine,avian,rest}/` and the corresponding
logs; `artifacts/lod-persisted-selection-negative-stderr.log` records rejection.

This is same-process disk reload evidence, not a fresh-process or packaged runtime
proof. The saved scene deliberately contains red/green diagnostic material
substitutions and is not an artist-facing production export. Persistent production
setup, continuous transition quality and release visual gates remain open.
PR #350 passed all six required checks and was merged before this extension.

### Fresh-process Godot selection (2026-11-09)

Saved review scenes now include versioned metadata for the clip, camera bounds
and level/rig/player paths. `scripts/reopen_lod_selection_godot.gd` loads that
scene in a new rendering-enabled Godot process and calls the same verification
routine as scene creation. It requires only `project.godot` and
`lod-selection-review.tscn`; it does not read the source GLBs or bundle manifest.
Run it with the same rendering options as the selection probe, without clip
arguments. Success writes a new `godot-lod-selection-reopened.json`.

Fresh-process Human Run, Canine Run and Avian Flight each pass 28 samples. Their
per-sample pixel counts exactly match the scene-creation run. The isolated test
directories contain no GLBs. A legacy scene without review metadata fails clearly
rather than guessing clip or level identities. Evidence:
`artifacts/lod-selection-stage-{human,canine,avian}/`,
`artifacts/lod-selection-fresh-{human,canine,avian}/` and
`artifacts/lod-selection-legacy-stderr.log`.

This establishes fresh-process persistence of the configured diagnostic setup,
not a packaged game or artist-facing engine exporter. Diagnostic color overrides
remain intentional; production material preservation, continuous transitions,
UV/deformation acceptance and live UI remain open. PR #351 passed all six checks
and was merged before this extension.

### Material-preserving Godot scene export (2026-11-09)

`scripts/prepare_lod_engine_scene.gd` writes a new `lod-engine.tscn` from an
existing two-level bundle using the same validated scene builder as the selection
probe. The caller supplies a finite positive switching distance in Godot units
and may supply an exact clip name:
```
Godot --headless --path BUNDLE --script /absolute/prepare_lod_engine_scene.gd -- 8 Run --bounds-margin=0.5
```
The scene retains imported surface materials without diagnostic overrides,
configures both levels' visibility ranges around shared bounds, and stores the
rigs/clips. With a clip, both levels require matching durations and configure
idle-process autoplay on load. Without a clip, the setup remains at rest. Existing
scene files are rejected. Original GLBs and their exchange manifest are unchanged;
the latter still describes the exchange bundle, not the separately created scene.
Instance `lod-engine.tscn` into a Godot world containing the artist's camera and
lighting. This developer CLI is not yet a Blender Export workspace integration.

Verify in a fresh rendering-enabled process with the existing reopen script and
`-- --engine`. The verifier checks autoplay has started before switching to manual
sampled evaluation. Diagnostic colors are applied only to the loaded verification
instance, never saved to the engine scene. Success writes
`godot-lod-engine-verified.json`.

Human Run, Canine Run and Avian Flight each pass 28 rendered checks at an explicit
8-unit boundary. Saved scenes contain no material overrides; original GLBs and
manifests compare byte-for-byte unchanged. Overwrite and zero-distance attempts
exit with failure, preserving the existing scene hash. The original diagnostic
Human Run path still passes. Evidence is in
`artifacts/lod-engine-final-{human,canine,avian}/` and the corresponding prepare,
verify and negative-control logs.

This provides a persistent engine scene with original materials and configured
selection. Continuous animation synchronization, transition visual quality,
animated culling bounds, more than two levels and artist-facing integration remain
unverified/unsupported as applicable. UV/deformation and live UI gates remain open.
PR #352 is merged with all six checks passing.

### Explicit loop export and continuous playback (2026-11-09)

The engine-scene CLI accepts `-- DISTANCE CLIP --loop` to opt into linear looping
on the copied Godot animations. Without `--loop`, imported loop semantics remain
unchanged. Looping without a named clip is rejected. Source GLBs are never changed.
The earlier imported fixtures play once by default; autoplay alone does not imply
looping, and artists must explicitly choose repetition for the engine scene.

`scripts/review_lod_continuous_godot.gd` observes actual idle-process autoplay in a
fresh rendering-enabled process, without seeking or manually advancing clocks.
Run with `--fixed-fps 60`. It switches camera distance every 12 frames, checks the
rendered level every frame, requires both clocks to stay within one microsecond,
and requires at least two loop wraps and both levels to be rendered. Diagnostic
colors are applied only to the loaded scene instance. The one-microsecond check
compares clocks within the same engine process; it is not a skin-error tolerance.

Explicitly looping Human Run and Canine Run each pass 152 frames; Avian Flight
passes 252. Each records three wraps and zero maximum clock difference. A control
slowing LOD1 to half speed fails with `LOD animation clocks diverged`; nonlooping
fixtures fail the continuous-loop test when playback stops. Looping without a
clip fails admission. Evidence: `artifacts/lod-continuous-loop-{human,canine,avian}/`,
`artifacts/lod-clock-negative-stderr.log`, and `artifacts/lod-loop-no-clip.log`.

This verifies continuous clock synchronization and rendered selection for these
fixtures. It does not certify perceptual popping, skin equality between levels,
animated culling bounds or Blender UI acceptance. PR #353 passed all six checks
and was merged before this change.

### Animated culling bounds (2026-11-09)

The evaluated-skin review found rest bounds insufficient for the tested clips:
maximum local-axis overflow was 0.340732 for Human Run, 0.341475 for Avian Flight
and 0.001490 for Canine Run. The new `review_lod_culling_godot.gd` samples 49 phases
per level, bakes evaluated skin with the rendering server, and reports vertex
containment against the saved custom AABB. It records measurements rather than
claiming a continuous conservative bound or changing the scene.

Animated engine export now requires explicit `--bounds-margin=VALUE`, finite and
nonnegative. The builder symmetrically grows the shared world bounds before
converting to each mesh's local AABB, retaining the original selection center.
Zero is accepted only as an explicit caller choice; it is not safe for the tested
clips. Static export continues to default to zero. Duplicate, negative and missing
animated margins are rejected. Larger bounds reduce culling efficiency, so choose
and verify the margin for the actual clips instead of treating an example as a
universal default.

With an explicitly selected 0.5-unit margin, all three fixtures have zero sampled
overflow across both levels. Padded Avian still passes 28 phase/distance rendered
selection checks. Evidence: `artifacts/lod-culling-{human,avian,canine}/`,
`artifacts/lod-culling-padded-{human,avian,canine}/`, and margin negative-control
logs. Source geometry, clips and materials are unchanged. Between-sample extrema,
other clips and other assets still need validation; no general culling acceptance
is claimed. PR #354 passed all six checks and was merged before this change.

### Packed engine playback (2026-11-10)

Human Run, Canine Run and Avian Flight padded/looping engine scenes were each
loaded through `--main-pack` in fresh rendering-enabled Godot 4.7.2 processes.
Each PCK contained only `project.godot`, the self-contained `lod-engine.tscn`,
`review_lod_continuous_godot.gd` and its shared base script. No GLBs or manifest
were included. Runs used an independent working directory, Compatibility/ANGLE
and `--fixed-fps 60`.

All 556 frames passed rendered near/far selection (152 Human, 152 Canine,
252 Avian); each fixture wrapped three times with zero measured inter-level
clock difference. Evidence and the local pack-building helper are in
`artifacts/lod-packed-runtime/` and `artifacts/pack_lod_review.gd`.
The probe accepts `-- --output=WRITABLE_PATH` so report output can live outside
read-only resource packs; omitted output retains the project-local default.
Existing reports and empty output arguments reject with exit 1; the existing
report hash was unchanged. Failed file creation now reports an error and exits
instead of calling a method on a null file handle.

This establishes resource-pack loading and sampled rendered switching for these
fixtures, not an exported standalone game, visual transition quality or final
engine acceptance. The separate temporary UV-seam splitting experiment was
rejected: it removed atlas crossings but produced 21,584 disconnected face
components at half budget and 10,790 at quarter budget. Do not promote that
experiment to the reducer; results remain in `artifacts/lod-uv-split-experiment.json`.
