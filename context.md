# Asset Assistant context index

Purpose: fast project navigation for LLM/agent work. This file is an index, not the source of truth.

Last structural rescan: 2026-09-15

Read `docs/human-workflow.md` for the user workflow and code ownership map.

## LOD implementation (2026-10-24)

Static LOD budgets and a separate-copy preview/apply/cancel backend are implemented. Saved-preview recovery, explicit multi-mesh groups and Export workspace controls are implemented; live UI/undo validation, skinned levels and engine export remain open. See [docs/lod-workflow.md](docs/lod-workflow.md).

## Current workflow and UI audit (2026-10-23)

See [docs/workflow-acceptance-audit.md](docs/workflow-acceptance-audit.md) for model/animation Modify, LOD, import/export and UI acceptance evidence. Human rig/clip work is merged; workflow and UX validation are active. LOD support and live UI review remain open. Required release gates are listed in docs/shared-anatomy-alpha-plan.md (Required workflow release gates). Blender tests use pytest so function-based UI tests run alongside unittest classes.

## Active pre-alpha direction (2026-09-21)

Plan: [docs/shared-anatomy-alpha-plan.md](docs/shared-anatomy-alpha-plan.md). Shared anatomy construction with Human, Quadruped and Avian recipes, then a cross-provider animation quality pass, precedes alpha release hardening. Human, Quadruped and Avian now resolve shared anatomy contracts; Avian implementation is complete for the documented review shapes; artistic review and final canine visual acceptance remain open. The plan supersedes older Human-only milestone sequencing.

## Shared anatomy implementation checkpoint

Human and Quadruped use resolved recipes. Canine recipe 16 retains the recipe 14 surface and extends the rest rig to 19 bones with independent forepaw articulation. Distal sole weights follow each paw bone. Existing 17-bone rigs require explicit rebuilding; artist-owned data is preserved. Final canine motion/visual sign-off remains open; Avian recipe 17 implementation and documented motion validation are complete on the active branch. See [docs/shared-anatomy-implementation.md](docs/shared-anatomy-implementation.md) for ownership, evidence and next work.

Paw-review baseline: `scripts/canine_review_metrics.py` measures per-limb ground clearance and near-ground footprint hulls; `scripts/render_canine_review.py` records neutral and evaluated pose results and supports pose-stable `front-paw` / `hind-paw` close-ups. `scripts/review_canine_gait.py` samples actual walk/run actions in an isolated scene; the original baseline exposed gait penetration; contact-solved clips now pass the documented sampled checks. See the implementation checkpoint for values, limits and next priorities.

Canine contact gait: `object_core/animation/contact.py` supplies stance/swing targets; `object_core/providers/quadruped_gait.py` solves joint rotations against the weighted sole, with editable root crouch and bounded vertical compression synchronized to the footfalls. Walk uses four footfalls; Run is a diagonal trot. The three documented shapes have no penetration in Blender samples over 127 intervals, with fixed-toe drift below 0.00156 cm for forepaws and 0.00006 cm for hind paws in the toe-off checkpoint. Gait reports track fixed sole/toe vertices and contiguous near-ground episodes (schema 5), separating lifted-point movement from sampled ground proximity; these remain diagnostics rather than physical contact-slip proof. The three-cycle review helper is `scripts/create_canine_motion_review.py`. All four paws add late-stance heel lift about a fixed forward toe target, then curl during swing. Reports distinguish expected sole roll from fixed-toe drift. Walk now adds bounded lateral sway toward stance support, counter-translated at the upper limbs to preserve paw contact; Idle and Run explicitly reset those offsets. Godot skeletal playback passes with diagnostic and source-grid imports; four-view renders and sampled canonical skin-contact checks pass; saved-scene skin checks and isolated resource-pack playback also pass; see `docs/canine-godot-playback.md`. Final multi-shape motion/visual acceptance remains open.

Short-wide Canine diagnosis: current-main neutral and Walk renders confirm the disk-like torso originates in extreme independent width/height inputs, before rigging. This remains a robustness sample, not an accepted canine reference. See the final section of docs/canine-godot-playback.md for reproduction and limits.

## Active Avian work

Avian recipe 17 completes the current bird implementation pass: tapered beak, thin tail fan, grounded clawed feet, folded Idle/Walk wings and articulated Flight. Walk has reach-bounded stride, bounded lift/body compression and head/tail response. Flight caps wing excursion and uses 64 intervals. All 72 shape/clip/strength cases pass sampled crossing/contact/closure checks; canonical folded-to-Flight blends pass. Both reference shapes have three-cycle review artifacts and Godot skeletal playback proofs. See `docs/avian-review.md` for metrics, explicit regeneration and limits. Artistic review, cross-provider Modify acceptance and release hardening remain separate gates. Human quality work is active; see `docs/human-review-notes.md`.

## Cross-provider acceptance

External Model JSON preview/apply, ownership blocking, parameter/semantic integration, component preservation and fresh-process persistence have operator proofs for Human, Canine and Avian. Human/Canine boundary blending and Avian body-owned chest selection are implemented; legacy incompatible edits remain preserved and blocked from regeneration.

Edited Avian validation covers 144 action cases and four Godot fixtures through rest, skeletal, posed-skin and saved-scene checks. The local gallery contains 48 phase sheets and 12 verified three-cycle videos. Final artistic acceptance remains open; Human baseline weight leakage is repaired below; silhouette feedback remains open. See [docs/cross-provider-acceptance.md](docs/cross-provider-acceptance.md) for evidence, limits and reproduction commands.

Packaged acceptance: `scripts/test_blender_package.py` covers isolated ZIP Human/Box workflows plus Avian external chest preview/apply, rig preservation and Idle/Walk/Flight. Remaining candidate lifecycle and publication gates are in `docs/publish-readiness-audit.md`.

## Human contact motion and recipe 6 (2026-10-22)

Human now has parameter-aware Walk/Run contact solving plus continuous neck, shoulder, elbow, wrist and knee weights. Geometry/rest bones remain recipe-5 compatible; saved rigs/clips require explicit rebuilding/regeneration. Eight dense actual-action cases pass contact, closure and deformation screens; core/Blender suites, final focused checks, isolated ZIP smoke and fresh-process preservation pass. Human Idle explicitly resets contact root compression when switching clips; scripts/create_human_clip_library.py builds a fresh editable three-clip library. Artistic review remains open. See docs/human-review-notes.md for evidence and limits; scripts/review_human_motion.py measures actual contact/deformation and scripts/create_human_motion_review.py creates editable three-cycle review scenes.

## Human foot refinement (2026-10-21)

Recipe 5 shares the foot surface/toe profile, shortens default feet by 13.45%, raises instep/heel volume and adds a local ankle weight blend. Heel/ball grounding, unchanged body topology, toe-bone alignment, ankle poses and legacy-mesh preservation have focused regressions. Explicit fresh generation/rebuilding is required; saved artist assets are preserved. Review: docs/human-review-notes.md; scripts/render_human_review.py supports --region left-foot and --foot-bend. Final artistic/continuous-motion approval remains open.

## Human hip-weight repair (2026-10-21)

Recipe 4 replaces abrupt pelvis side/radius weight switches with a local continuous torso/thigh field. Absolute hip-edge ratios improve from up to 34.91x stretching to 0.529..1.442 across 12 reference poses; neutral geometry, rest bones, authored arms and distal weights are preserved. Existing saved weights require explicit rebuilding. Evidence and remaining foot/motion work: docs/human-review-notes.md; regression tool: scripts/review_human_hip_deformation.py.

## Human glute control and hip review (2026-10-21)

Modify exposes glutes/full through Model JSON preview/apply, preserving neutral generation and independent waist/width/arm ownership. The 16-pose relative screen passes, but paired renders reveal severe pre-existing hip-junction folding in the unedited baseline. The hip defect is repaired in recipe 4 above; final anatomy/motion acceptance remains open. See docs/human-review-notes.md and scripts/review_semantic_deformation.py --human-target glutes.

## Human shoulder refinement (2026-10-21)

Recipe 3 builds on the recipe-2 lower-body isolation repair: authored arm weights now exclude distant elbow influence near shoulders. The broad shoulder profile smoothly bounds displacement gradients while retaining its selected region and monotonic strength. All 16 paired shoulder poses pass the unchanged screen; 25 core and 14 focused Blender tests pass. Old saved profiles/weights are preserved; incompatible old edits cannot be automatically reconstructed. See docs/human-review-notes.md (root-relative) and tests/blender/test_deformation_review.py.

## Human deformation repair (2026-10-20)

Human recipe 2 localizes neck/upper-arm influence below their attachments using a smooth weight transfer to torso; authored arm weights remain unchanged. Fresh Blender poses reproduce and eliminate the reported lower-body pulling. Existing saved weights require explicit rebuilding. Glute/foot silhouette feedback remains open. See docs/human-review-notes.md (root-relative) and object_core/rigging/surface_human.py; regression: tests/blender/test_deformation_review.py.

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

Human glute/foot silhouette feedback remains open; the reproduced upper-body weight leakage is repaired.
`object_core/providers/human.py` composes the mathematical
surface, surface-aligned skeleton, cached skin weights and semantic controls.
The mathematical surface builder is internal; Human is the only Human UI option.

Read next:
- `docs/human-review-notes.md` � user feedback on glute fullness, foot shape and neck/glute deformation.
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
