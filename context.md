# Asset Assistant context index

Purpose: fast project navigation for LLM/agent work. This file is an index, not the source of truth.

Last structural rescan: 2026-09-15

Read `docs/human-workflow.md` for the user workflow and code ownership map.

## Active pre-alpha direction (2026-09-21)

Plan: [docs/shared-anatomy-alpha-plan.md](docs/shared-anatomy-alpha-plan.md). Shared anatomy construction with Human, Quadruped and Avian recipes, then a cross-provider animation quality pass, precedes alpha release hardening. This is planned work; current providers still use separate anatomy implementations. The plan supersedes older Human-only milestone sequencing.

## Current Human V2 integration (2026-09-20)

Create > Human is the single Human UI path. `HumanProvider` uses key `human` and
composes the mathematical surface builder, rig and shared body-control mapping.
The former static study option and experimental provider identity are removed.
See `docs/human-workflow.md` for the workflow and code ownership map.

## Project map

- `object_core/` — host-independent asset model, providers, geometry, rigging, animation, modification contracts, validation.
- `blender_adapter/` — Blender-specific UI, lifecycle, persistence, import/export, components, rigging/material application, presentation composition.
- `tests/core/` — portable behavior, architecture boundaries, provider/geometry/rigging/animation contracts.
- `tests/blender/` — Blender integration and packaged add-on behavior.
- `docs/` — architecture, workflow, roadmap, quality checkpoints, and design decisions.
- `scripts/` — development/review/build helpers, including Human and standalone-pelvis visual review rendering.

## Current architecture mental model

`object_core + providers -> Blender adapter behavior -> PresentationRegistry -> workspace_panel_host -> Blender panel classes`

Performance seams such as `ui_fastpath` and `modify_fastpath` are optimizations, not alternate workflows.

Architecture is intentionally frozen during Human V2 unless a concrete feature or failing boundary test proves a change is required.

Read next when architecture matters:
- `docs/architecture.md`
- `docs/architecture-maintainability-review-2026-09-13.md`
- `blender_adapter/presentation_registry.py`
- `blender_adapter/workspace_panel_host.py`
- `tests/core/test_architecture_boundaries.py`

## Current product focus

Human V2 quality is active. `object_core/providers/human.py` composes the mathematical
surface, surface-aligned skeleton, cached skin weights and semantic controls.
The mathematical surface builder is internal; Human is the only Human UI option.

Read next:
- `object_core/context.md`
- `docs/visual-testing-integration.md` — current behavior, defects repaired, CI timing and limits.
- `scripts/inspect_human_deformation.py` — projected, independently verified pose cards.
- `docs/human-v2-topology-plan.md` — quality gates and earlier pelvis-first experiments.

Do not repeat the Maxine round trip until neutral anatomy/deformation quality advances.

## Modify / artist-control invariant

The anatomy-oriented constructor changes how the neutral Human is built; it does **not** replace or diminish Modify.

Preserve:
- semantic Modify operations;
- model JSON export/import round trip;
- preview/apply;
- artist ownership/preservation contracts;
- independent semantic anatomy controls where practical.

Base construction creates credible neutral anatomy. Modify creates the particular character the artist wants.

## High-value invariants

- Core/providers remain Blender-independent.
- Generated/imported/adopted ownership remains explicit; preserve artist work.
- Preview/apply and validation boundaries are intentional safety features.
- Do not casually change shared primitive assumptions such as global `RING_SIDES`; Human-specific anatomy constructors own deliberate topology migrations.
- Geometry quality work preserves deterministic generation and tested topology/UV/deformation contracts unless a change explicitly migrates them.
- A mathematically valid topology can still fail the visual quality gate; use clay, silhouette, and wireframe diagnostics after major anatomy regions.

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

## Human geometry

`object_core/geometry/surface_human_builder.py` builds and audits geometry for
`HumanProvider`. Standalone study scripts are development tools, not a second
plugin workflow. See `docs/human-workflow.md` for the current code map.
