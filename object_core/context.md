# object_core context index

Scope: host-independent Asset Assistant behavior. Source code and tests are authoritative.

Last structural rescan: 2026-09-15

Read `docs/human-workflow.md` for the user workflow and code ownership map.

## Active pre-alpha direction (2026-09-21)

Plan: [../docs/shared-anatomy-alpha-plan.md](../docs/shared-anatomy-alpha-plan.md). Shared anatomy construction with Human, Quadruped and Avian recipes, then a cross-provider animation quality pass, precedes alpha release hardening. Human and Quadruped now resolve shared anatomy contracts; canine motion acceptance and Avian migration remain in progress. The plan supersedes older Human-only milestone sequencing.

## Current Human V2 integration (2026-09-20)

Create > Human is the single Human UI path. `HumanProvider` uses key `human` and
composes the mathematical surface builder, rig and shared body-control mapping.
The former static study option and experimental provider identity are removed.
See `docs/human-workflow.md` for the workflow and code ownership map.

## Shared anatomy seam

`anatomy/contracts.py` owns immutable metadata. Human and Quadruped resolve shared recipes. `providers/quadruped_anatomy.py` owns Canine recipe 16, including body/paw profiles, toe endpoints, knee/hock/paw chains and a 19-bone rest rig with independent forepaw joints (older rigs require explicit rebuilding). `quadruped_geometry.py` owns connected cage topology and grounded paw shaping; `quadruped_refinement.py` propagates regions and boundary loops through global/local refinement; `quadruped_detail.py` adds connected face and pad/claw relief. `quadruped_rigging.py` keeps authored limb-chain ownership and attachment collar fades, with smooth distal paw ownership to prevent sole shear. `quadruped_semantic.py` executes authored-region edits through `semantic_geometry.py`. Final canine motion acceptance and Avian migration remain ahead.
Tests: `test_anatomy_contracts.py`, `test_anatomy_proofs.py`, `test_human_recipe.py`, `test_canine_recipe.py`, `test_canine_refinement.py` under `tests/core`; `tests/blender/test_quadruped_semantic.py`. Baseline: `scripts/anatomy_baseline.py`. Status: `docs/shared-anatomy-implementation.md`. Actual-action walk/run ground diagnostics live in `scripts/review_canine_gait.py`; contact-solved clips pass the documented sampled contact checks; final motion quality remains open.

Canine contact gait: `object_core/animation/contact.py` supplies stance/swing targets; `object_core/providers/quadruped_gait.py` solves joint rotations against the weighted sole, with editable root crouch and bounded vertical compression synchronized to the footfalls. Walk uses four footfalls; Run is a diagonal trot. The three documented shapes have no penetration in Blender samples over 127 intervals, with fixed-toe drift below 0.00156 cm for forepaws and 0.00006 cm for hind paws in the toe-off checkpoint. Gait reports track fixed sole/toe vertices and contiguous near-ground episodes (schema 5), separating lifted-point movement from sampled ground proximity; these remain diagnostics rather than physical contact-slip proof. The three-cycle review helper is `scripts/create_canine_motion_review.py`. All four paws add late-stance heel lift about a fixed forward toe target, then curl during swing. Reports distinguish expected sole roll from fixed-toe drift. Walk now adds bounded lateral sway toward stance support, counter-translated at the upper limbs to preserve paw contact; Idle and Run explicitly reset those offsets. Godot skeletal playback passes with diagnostic and source-grid imports; four-view render sequences are available; see `docs/canine-godot-playback.md`. Final multi-shape motion/visual acceptance remains open.

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
