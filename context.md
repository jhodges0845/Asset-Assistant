# Asset Assistant context index

Purpose: fast project navigation for LLM/agent work. This file is an index, not the source of truth.

Last structural rescan: 2026-09-15

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

Human V2 neutral-mesh quality is the active depth milestone. The current direction is **anatomy-oriented construction**, not the older coarse mannequin plus repeated refinement strategy.

The active blocker is the pelvis/hip/crotch surface. Diagnostic renders independently confirmed that mesh density is not the main problem; anatomical topology organization is.

PR #283 established a standalone, sex-neutral pelvis prototype with three open interfaces (torso, left thigh, right thigh) and independent semantic shape controls. The prototype is deliberately evaluated outside active Human generation first. Once it passes clay/silhouette/wireframe review, topology should grow upward into the lower torso and downward into each thigh.

Current sequence:

`standalone pelvis -> lower torso/ribcage -> thighs -> shoulder girdle/neck -> anatomical limbs/joints -> feet/hands -> skull/face`

Do not repeat the Maxine round trip yet. Preserve it as a later character-quality checkpoint after the neutral constructor has materially advanced.

Read next for Human V2 work:
- `object_core/context.md`
- `docs/human-v2-topology-plan.md`
- `object_core/geometry/neutral_pelvis.py`
- `object_core/geometry/anatomical_human.py`
- `scripts/render_pelvis_review.py`
- `scripts/render_human_review.py`

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

## Mathematical Human plugin option

- `human_surface_study` is registered as Mathematical Human in Create; static,
  no rig/animation/UV support. Existing Human stays compatible.
- `object_core/geometry/surface_human.py` and `surface_pelvis.py`: mathematical
  geometry, rounded pelvis and bounded fairing; no imported anatomical assets.
- `blender_adapter/surface_human_runtime.py`: normal asset creation with the same
  collision gate as the standalone study, before replacing the current asset.
- `scripts/render_human_review.py --provider human_surface_study --height-cm 175`
  creates clay/silhouette/wireframe visual checks; CI uploads them on main and
  visual-testing. Visual approval remains manual.
- See `docs/mathematical-human-plugin.md` and the mathematical-human development
  journal for usage, limitations, and reproducible standalone studies.
