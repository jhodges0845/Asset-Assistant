# Human V2 Topology Plan

Human V2 is a coordinated geometry, deformation, and motion quality pass. It is not a polygon-count increase.

## Phase 1 — topology/anatomy foundation

- Add intentional support topology around pelvis/hip transitions and shoulder/armpit transitions.
- Keep topology deterministic across supported Human proportions and body types.
- Preserve one connected editable body surface.
- Keep branch openings explicit rather than dependent on magic ring indices.
- Preserve current semantic editability and export behavior.

## Phase 2 — deformation rig and weights

- Improve pelvis/spine/clavicle articulation.
- Add twist/deformation support where needed.
- Keep export/deformation skeleton distinct from any future animator control rig.
- Replace purely distance-driven weighting in difficult anatomical zones with topology-aware weighting.

## Phase 3 — face topology

- Introduce intentional structures for eyelids/eyes, nose, lips/mouth, brow, cheeks, chin and jaw.
- Preserve procedural determinism and semantic face operations.

## Phase 4 — locomotion semantics

- Drive locomotion from contact/down/passing/up phases rather than sparse raw rotations.
- Add center-of-mass, pelvis, heel/toe, spine/clavicle and weight-transfer behavior.

## Guardrail

Architecture remains frozen unless Human V2 exposes a concrete boundary problem. Quality work should fit the existing provider/core/Blender-adapter model rather than reopening broad infrastructure cleanup.
