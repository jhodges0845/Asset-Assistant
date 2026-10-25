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

- Add artist-facing preview/apply/cancel and level inspection through the current
  workspace presentation registry, with selection and undo behavior verified.
- Add multi-mesh asset boundaries, quality/silhouette review and material/UV checks
  on representative generated and imported assets.
- Implement skinned LODs with explicit weight preservation/normalization and
  animated deformation validation; never silently apply this static path to rigs.
- Implement per-target export grouping and verify actual engine LOD selection.
- Run the release-roadmap visual, save/reopen, import/export and package gates.

No UI command or automatic engine LOD configuration is shipped by this slice.
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
5.2.1 and runs in CI. UI, undo interaction and visual quality remain unverified.
