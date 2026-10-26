# LOD workflow implementation

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
