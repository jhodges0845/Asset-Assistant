# Documentation context index

Use this file to find the right source-of-truth document without loading the entire `docs/` tree.

Last structural rescan: 2026-09-15

## Architecture and maintainability

- `architecture.md` — current architecture overview.
- `architecture-maintainability-review-2026-09-13.md` — stabilization review, risks, and architecture-freeze rationale.
- `component-architecture.md` — component model and ownership boundaries.
- `animation-architecture.md` — animation architecture.

Architecture remains frozen during Human V2 unless implementation exposes a concrete boundary problem.

## Current Human quality milestone

- `human-v2-topology-plan.md` — **active source of truth** for Human V2 anatomy direction, pelvis-first construction, semantic-control requirements, sequencing, and visual acceptance gates.
- `deformation-quality.md` — deformation quality expectations; deeper rig/weight work follows topology evidence.
- `human-1.0-closeout-audit.md` — prior Human milestone closeout; historical context, not current target state.

Current Human V2 direction: anatomy-oriented neutral construction. The active experiment generates a standalone sex-neutral pelvis first, validates it in clay/silhouette/wireframe, then extends topology into torso and thighs. Older coarse-mesh-plus-refinement notes are historical when they conflict with the current plan.

## Model/LLM round-trip and Modify

- `model-json-roundtrip.md` — model inspection and safe modification round trip.
- `semantic-modify.md` — semantic modification behavior.
- `artist-control-contract.md` — artist-control/ownership expectations.
- `editable-asset-workflow.md` — editable asset workflow.

Human V2 must preserve these workflows. Base topology supplies credible neutral anatomy; semantic Modify and JSON round trips supply character identity. Do not interpret anatomy-oriented construction as permission to bypass or reduce Modify.

## Product and release state

- `roadmap.md` — roadmap and sequencing.
- `production-readiness-checklist.md` — production readiness criteria.
- `pre-release-scope-checkpoint.md` — pre-release scope checkpoint.
- `publish-readiness-audit.md` — publish-readiness audit.

## Export/engine behavior

- `targets.md` — destination behavior.
- `target-verification.md` — target verification evidence.
- `production-character-roundtrip.md` — production character round-trip expectations.

## UI/UX

- `ui-ux.md` — UI/UX direction.
- `post-modify-ui-audit.md` — UI audit after modification workflow.
- `ui-overhaul.md` and `ui-ux-create-components.md` — narrower historical UI work.

Final UI/UX polish remains behind the current Human quality gate unless a concrete workflow blocker requires otherwise.

## Reading rule

Prefer the current plan/audit over older milestone notes when they conflict. Historical docs remain useful for rationale, but should not silently override current implementation or tests.
