# object_core context index

Scope: host-independent Asset Assistant behavior. Source code and tests are authoritative.

Last structural rescan: 2026-09-15

Read `docs/human-workflow.md` for the user workflow and code ownership map.

## Active pre-alpha direction (2026-09-21)

Plan: [../docs/shared-anatomy-alpha-plan.md](../docs/shared-anatomy-alpha-plan.md). Shared anatomy construction with Human, Quadruped and Avian recipes, then a cross-provider animation quality pass, precedes alpha release hardening. Human and Quadruped now resolve shared anatomy contracts; canine quality refinement and Avian migration remain in progress. The plan supersedes older Human-only milestone sequencing.

## Current Human V2 integration (2026-09-20)

Create > Human is the single Human UI path. `HumanProvider` uses key `human` and
composes the mathematical surface builder, rig and shared body-control mapping.
The former static study option and experimental provider identity are removed.
See `docs/human-workflow.md` for the workflow and code ownership map.

## Shared anatomy seam

`anatomy/contracts.py` owns immutable metadata. `providers/human_anatomy.py` resolves Human; `providers/quadruped_anatomy.py` resolves Quadruped as `CanineRecipe` (version 11: height-bounded front distal dimensions, forward shoulder placement, recipe-owned low-paw volume and forward projection, broader grounded soles, distinct muzzle, refined surface and ears, recipe-owned body sections, explicit knee/hock/paw hind chains, 17 bones). Geometry owns topology/membership; rig builders consume resolved chains. `providers/quadruped_refinement.py` refines the internal control cage and propagates region/connection ownership. Canine limbs use authored chains and a topology-distance blend across their declared attachment bridges; the remaining body uses axial bones and ears follow the head. `providers/quadruped_semantic.py` executes authored-region edits using `providers/semantic_geometry.py`, shared with Human/Avian. Canine quality refinement and Avian recipe migration remain ahead.
Tests: `test_anatomy_contracts.py`, `test_anatomy_proofs.py`, `test_human_recipe.py`, `test_canine_recipe.py`, `test_canine_refinement.py` under `tests/core`; `tests/blender/test_quadruped_semantic.py`. Baseline: `scripts/anatomy_baseline.py`. Status: `docs/shared-anatomy-implementation.md`.

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
