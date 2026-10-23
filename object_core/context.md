# object_core context index

Scope: host-independent Asset Assistant behavior. Source code and tests are authoritative.

Last structural rescan: 2026-09-15

Read `docs/human-workflow.md` for the user workflow and code ownership map.

## Active pre-alpha direction (2026-09-21)

Plan: [../docs/shared-anatomy-alpha-plan.md](../docs/shared-anatomy-alpha-plan.md). Shared anatomy construction with Human, Quadruped and Avian recipes, then a cross-provider animation quality pass, precedes alpha release hardening. Human, Quadruped and Avian now resolve shared anatomy contracts; Avian implementation is complete for the documented review shapes; artistic review and final canine visual acceptance remain open. The plan supersedes older Human-only milestone sequencing.

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

## Shared anatomy seam

`anatomy/contracts.py` owns immutable metadata. Human, Quadruped and Avian resolve shared recipes. Avian recipe 17 (`providers/avian_anatomy.py`) owns shared surface/rest landmarks, clawed feet, height-aware shoulders, tapered beak and thin tail fan. `avian_geometry.py` binds topology; `avian_rigging.py` preserves authored ownership with spine-anchored collars and rigid sole weights. `avian_gait.py` uses the shared weighted contact solver with reach-bounded stride and bounded lift/body response; Walk adds head/tail response. `avian_posture.py` owns folded local-space wings; `avian_animation.py` owns Idle/Flight, with bounded 64-interval Flight. All 72 documented shape/clip/strength cases pass sampled crossings/contact/closure. Review tools, destination proof and explicit rebuilding requirements are indexed in `docs/avian-review.md`. Tests: Avian core/Blender suites; no Blender imports in providers. `providers/quadruped_anatomy.py` owns Canine recipe 16, including body/paw profiles, toe endpoints, knee/hock/paw chains and a 19-bone rest rig with independent forepaw joints (older rigs require explicit rebuilding). `quadruped_geometry.py` owns connected cage topology and grounded paw shaping; `quadruped_refinement.py` propagates regions and boundary loops through global/local refinement; `quadruped_detail.py` adds connected face and pad/claw relief. `quadruped_rigging.py` keeps authored limb-chain ownership and attachment collar fades, with smooth distal paw ownership to prevent sole shear. `quadruped_semantic.py` executes authored-region edits through `semantic_geometry.py`. Final artistic review and cross-provider acceptance remain ahead.
Tests: `test_anatomy_contracts.py`, `test_anatomy_proofs.py`, `test_human_recipe.py`, `test_canine_recipe.py`, `test_canine_refinement.py` under `tests/core`; `tests/blender/test_quadruped_semantic.py`. Baseline: `scripts/anatomy_baseline.py`. Status: `docs/shared-anatomy-implementation.md`. Actual-action walk/run ground diagnostics live in `scripts/review_canine_gait.py`; contact-solved clips pass the documented sampled contact checks; final motion quality remains open.

Canine contact gait: `object_core/animation/contact.py` supplies stance/swing targets; `object_core/providers/quadruped_gait.py` solves joint rotations against the weighted sole, with editable root crouch and bounded vertical compression synchronized to the footfalls. Walk uses four footfalls; Run is a diagonal trot. The three documented shapes have no penetration in Blender samples over 127 intervals, with fixed-toe drift below 0.00156 cm for forepaws and 0.00006 cm for hind paws in the toe-off checkpoint. Gait reports track fixed sole/toe vertices and contiguous near-ground episodes (schema 5), separating lifted-point movement from sampled ground proximity; these remain diagnostics rather than physical contact-slip proof. The three-cycle review helper is `scripts/create_canine_motion_review.py`. All four paws add late-stance heel lift about a fixed forward toe target, then curl during swing. Reports distinguish expected sole roll from fixed-toe drift. Walk now adds bounded lateral sway toward stance support, counter-translated at the upper limbs to preserve paw contact; Idle and Run explicitly reset those offsets. Godot skeletal playback passes with diagnostic and source-grid imports; four-view renders are available and sampled canonical skin-contact checks pass; see `docs/canine-godot-playback.md`. Final multi-shape motion/visual acceptance remains open.

## Ownership by area

- `providers/` — provider capabilities and composition; Human enters through `providers/human.py`.
- `geometry/` — portable mesh generation, anatomy construction, topology, and refinement.
- `rigging/` — portable skeleton and skin-weight generation.
- `animation/` + `animations.py` — portable animation generation/contracts.
- `models/` — immutable portable data contracts.
- `modification.py`, `modify_exchange.py` — modification planning/exchange contracts.
- `validation/` — portable validation rules.

## Active Human V2 composition

- `providers/human.py` — Human plugin provider; validates legacy controls, caches a
  neutral surface plus provisional UVs, and keys shaped meshes/weights by all controls.
- `geometry/surface_human.py` + `surface_pelvis.py` — mathematical surface geometry.
- `geometry/human_shaping.py` — body-control mapping; `rigging/surface_human.py` converts resolved Human chains into bones.
- `providers/human_semantic.py` — topology-preserving Modify using resolved landmarks and authored limb ownership.
- `geometry/neutral_pelvis.py` — earlier standalone pelvis experiment, separate from Human.

Keep surface rest landmarks synchronized with authored geometry centerlines. Preserve
bone names/parents used by existing animations and recompute weights for edited meshes.
Tests: `tests/core/test_provider_boundaries.py`, `tests/core/test_human_semantic.py`,
`tests/blender/test_deformation_review.py`; the full Blender suite protects plugin workflows.
The surface generator optionally returns authored arm and leg indices; Human skinning
uses them to keep wrist/forearm weights off the body, including after semantic
edits. Shared weighting remains in `rigging/deforming.py` through its optional
bone filter. Pose displacement and manifold tests do not establish anatomical
visual acceptance.

## Semantic shaping / Modify

Human V2 must preserve the current Modify and model JSON round-trip workflow. Anatomy construction creates a credible neutral Human; semantic operations create character identity.

`geometry/neutral_pelvis.py` exposes independent semantic controls including pelvis/waist dimensions, hip fullness, glute projection, crotch dimensions/drop, thigh-opening dimensions, and thigh spacing. Do not couple independent controls merely to satisfy a test or visual default.

`providers/human_semantic.py` remains the Human semantic-operation layer. Provider integration must provide stable anatomy-aware seams for semantic changes rather than bypassing Modify.

## Rig/deformation

- `rigging/deforming.py` owns shared skin weights and the legacy skeleton;
  `providers/human_anatomy.py` resolves Human rest anatomy and `rigging/surface_human.py` constructs its skeleton.
- Current quality work has softened major-joint blending without introducing a separate animator control rig.
- Keep export/deformation concerns distinct from future animator-control abstractions.
- Deeper rig/weight changes follow topology evidence rather than speculative skeleton expansion.

## Architecture boundary

Nothing under `object_core` should depend on `bpy` or `blender_adapter`.

Do not reopen broad architecture cleanup during Human V2 unless a concrete feature cannot fit the current provider/core/adapter model or a test exposes a real boundary failure.

Fast checks:
- `python -m unittest discover -s tests/core -v`
- boundary tests in `tests/core/test_architecture_boundaries.py` and `tests/core/test_provider_boundaries.py`

### Lower-pelvis transition review

The standalone prototype now distributes the lower-hip turn across cubic longitudinal rows, carries those rows into the existing crotch rails, and preserves three 16-vertex attachment boundaries. `tests/core/geometry/test_neutral_pelvis.py` guards the lateral taper, face folding, winding, and declared boundaries.
## Human geometry

`object_core/geometry/surface_human_builder.py` builds and audits geometry for
`HumanProvider`. Standalone study scripts are development tools, not a second
plugin workflow. See `docs/human-workflow.md` for the current code map.

## Semantic boundary refinement

`providers/semantic_geometry.py::_blend_region_transform` tapers profile displacement
along mesh-edge distance from authored region seams. Only Human shoulders/broad and
Canine chest/broad opt in. Other profile/explicit scale behavior is unchanged.
Tests: `tests/core/test_semantic_boundaries.py`, Human/Avian semantic suites and
`tests/blender/test_model_json_acceptance.py` (including old-profile protection).
Saved hard-region edits are preserved but fail reconstruction ownership checks;
see `docs/cross-provider-acceptance.md` for the explicit fresh-asset workflow.

Avian `chest/powerful` intersects its coordinate bounds with authored body ownership
and validates topology before indexing. Wings/legs remain unchanged. Other Avian
profiles retain prior selection. Saved old chest profiles are preserved but blocked
by reconstruction ownership checks. See the cross-provider acceptance document.
