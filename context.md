# Asset Assistant context index

Purpose: fast project navigation for LLM/agent work. This file is an index, not the source of truth.

Last structural rescan: 2026-09-14

## Project map

- `object_core/` — host-independent asset model, providers, geometry, rigging, animation, modification contracts, validation.
- `blender_adapter/` — Blender-specific UI, lifecycle, persistence, import/export, components, rigging/material application, presentation composition.
- `tests/core/` — portable behavior, architecture boundaries, provider/geometry/rigging/animation contracts.
- `tests/blender/` — Blender integration and packaged add-on behavior.
- `docs/` — architecture, workflow, roadmap, quality checkpoints, and design decisions.
- `scripts/` — development/review/build helpers, including Human visual review rendering.

## Current architecture mental model

`object_core + providers -> Blender adapter behavior -> PresentationRegistry -> workspace_panel_host -> Blender panel classes`

Performance seams such as `ui_fastpath` and `modify_fastpath` are optimizations, not alternate workflows.

Read next when architecture matters:
- `docs/architecture.md`
- `docs/architecture-maintainability-review-2026-09-13.md`
- `blender_adapter/presentation_registry.py`
- `blender_adapter/workspace_panel_host.py`
- `tests/core/test_architecture_boundaries.py`

## Current product focus

Human V2 quality is the active depth milestone. The neutral Human should look recognizably human before semantic/LLM shaping is expected to create character identity.

Current Human pipeline is composed through `object_core/providers/human.py` and Human-specific geometry refinement modules under `object_core/geometry/`.

Read next for Human V2 work:
- `object_core/context.md`
- `docs/human-v2-topology-plan.md`
- `scripts/render_human_review.py`

## High-value invariants

- Core/providers remain Blender-independent.
- Generated/imported/adopted ownership must remain explicit; preserve artist work.
- Preview/apply and validation boundaries are intentional safety features.
- Do not casually change shared `RING_SIDES`/blockout primitive assumptions to improve Human quality; prefer Human-specific refinement unless a deliberate topology migration is justified.
- Geometry quality work should preserve deterministic generation and tested topology/UV/deformation contracts unless the change explicitly migrates them.

## Context loading strategy

For most tasks:
1. Read this file.
2. Read the nearest scoped `context.md` for the subsystem being changed.
3. Open only the named implementation/tests/docs needed for the task.

Do not recursively read every linked file unless the task requires it.

## Index commands

- `CONTEXT RESCAN` — scan current repo state and synchronize context indexes.
- `CONTEXT STATUS` — check index freshness/drift without automatically rewriting.
- `CONTEXT BYPASS` — ignore `context.md` summaries for the current task and inspect primary sources directly.

See `AGENTS.md` for command semantics and scanner responsibilities.
