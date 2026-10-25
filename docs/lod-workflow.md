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
