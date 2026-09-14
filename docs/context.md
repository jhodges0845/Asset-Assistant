# Documentation context index

Use this file to find the right source-of-truth document without loading the entire `docs/` tree.

## Architecture and maintainability

- `architecture.md` — current architecture overview.
- `architecture-maintainability-review-2026-09-13.md` — stabilization review, risks, and architecture freeze rationale.
- `component-architecture.md` — component model and ownership boundaries.
- `animation-architecture.md` — animation architecture.

## Current Human quality milestone

- `human-v2-topology-plan.md` — active Human V2 quality plan and visual acceptance gate.
- `deformation-quality.md` — deformation quality expectations.
- `human-1.0-closeout-audit.md` — prior Human milestone closeout; historical context, not current target state.

## Model/LLM round-trip

- `model-json-roundtrip.md` — model inspection and safe modification round-trip.
- `semantic-modify.md` — semantic modification behavior.
- `artist-control-contract.md` — artist-control/ownership expectations.
- `editable-asset-workflow.md` — editable asset workflow.

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

## Reading rule

Prefer the current plan/audit over older milestone notes when they conflict. Historical docs remain useful for rationale, but should not silently override current implementation or tests.
