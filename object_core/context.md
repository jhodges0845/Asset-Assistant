# object_core context index

Scope: host-independent Asset Assistant behavior. Source code and tests are authoritative.

Last structural rescan: 2026-09-15

## Ownership by area

- `providers/` — provider capabilities and composition; Human enters through `providers/human.py`.
- `geometry/` — portable mesh generation, anatomy construction, topology, and refinement.
- `rigging/` — portable skeleton and skin-weight generation.
- `animation/` + `animations.py` — portable animation generation/contracts.
- `models/` — immutable portable data contracts.
- `modification.py`, `modify_exchange.py` — modification planning/exchange contracts.
- `validation/` — portable validation rules.

## Human V2 geometry direction

The older `generate_deformable_mesh` plus repeated cross-section-refinement description is historical and no longer the Human V2 target architecture. Human V2 is intentionally migrating toward **anatomy-oriented construction** while keeping shared workflow architecture frozen.

Current relevant geometry includes:

- `geometry/anatomical_human.py` — anatomy-oriented Human constructor/integration work;
- `geometry/anatomical_pelvis.py` — semantic pelvic landmarks and paths;
- `geometry/anatomical_pelvis_patch.py` — earlier integrated pelvis surface experiment retained as current Human behavior while the replacement is evaluated;
- `geometry/neutral_pelvis.py` — standalone sex-neutral pelvis prototype from #283 with semantic shape controls and three named attachment boundaries;
- legacy/refinement modules remain relevant where active Human generation still uses them, but they are not the desired long-term construction strategy.

Always verify the exact active composition in `providers/human.py` and `geometry/anatomical_human.py` before editing it.

## Active pelvis checkpoint

The current blocker is pelvic topology, not mesh density. Diagnostics rejected both radial torso-to-thigh fans and stacked circumferential thigh-opening belts.

The replacement strategy is pelvis-first:

`standalone neutral pelvis -> extend upward into lower torso -> extend downward into left/right thighs`

The standalone pelvis owns three intentional open interfaces: torso, left thigh, and right thigh. It is intentionally not integrated into the active Human until its clay/silhouette/wireframe review passes.

Important constraints:

- neutral construction does not assume male or female genital anatomy;
- inner-thigh/crotch origin should remain close to centerline while outer hip/trochanter carries width;
- prefer structured anatomical longitudinal flow over conversion belts;
- preserve deterministic output and bilateral symmetry in the neutral default;
- structural tests protect manifoldness/boundaries/orientation; visual renders decide anatomy quality.

## Semantic shaping / Modify

Human V2 must preserve the current Modify and model JSON round-trip workflow. Anatomy construction creates a credible neutral Human; semantic operations create character identity.

`geometry/neutral_pelvis.py` exposes independent semantic controls including pelvis/waist dimensions, hip fullness, glute projection, crotch dimensions/drop, thigh-opening dimensions, and thigh spacing. Do not couple independent controls merely to satisfy a test or visual default.

`providers/human_semantic.py` remains the Human semantic-operation layer. Future constructor integration should provide stable anatomy-aware seams for semantic changes rather than bypassing Modify.

## Rig/deformation

- `rigging/deforming.py` owns Human deformation skeleton/weights.
- Current quality work has softened major-joint blending without introducing a separate animator control rig.
- Keep export/deformation concerns distinct from future animator-control abstractions.
- Deeper rig/weight changes follow topology evidence rather than speculative skeleton expansion.

## Architecture boundary

Nothing under `object_core` should depend on `bpy` or `blender_adapter`.

Do not reopen broad architecture cleanup during Human V2 unless a concrete feature cannot fit the current provider/core/adapter model or a test exposes a real boundary failure.

Fast checks:
- `python -m unittest discover -s tests/core -v`
- boundary tests in `tests/core/test_architecture_boundaries.py` and `tests/core/test_provider_boundaries.py`
