# object_core context index

Scope: host-independent Asset Assistant behavior. Source code and tests are authoritative.

## Ownership by area

- `providers/` — provider capabilities and composition. Human V2 enters through `providers/human.py`.
- `geometry/` — portable mesh generation/refinement/topology.
- `rigging/` — portable skeleton and skin-weight generation.
- `animation/` + `animations.py` — portable animation generation/contracts.
- `models/` — immutable portable data contracts.
- `modification.py`, `modify_exchange.py` — modification planning/exchange contracts.
- `validation/` — portable validation rules.

## Human V2 geometry pipeline

Current `HumanExperimentalProvider.mesh()` composes:

1. `generate_deformable_mesh`
2. `refine_human_torso_cross_sections`
3. Human-specific shoulder/deltoid refinement
4. `refine_human_limb_cross_sections`
5. `refine_human_facial_topology`
6. `refine_human_cranium_cross_sections`

Verify the exact call order in `providers/human.py` before editing it.

Relevant Human geometry modules/tests:
- `geometry/deformable.py`
- `geometry/body_refinement.py`
- `geometry/shoulder_refinement.py`
- `geometry/limb_refinement.py`
- `geometry/facial_refinement.py`
- `geometry/cranium_refinement.py`
- `tests/core/geometry/test_human_*`

## Important geometry constraints

- Shared primitive ring resolution currently comes from `geometry/primitives.py`; Human branch stitching assumes the existing ring structure in `geometry/deformable.py`.
- Human-specific refinement is the preferred seam for anatomy improvements until a deliberate topology migration is planned.
- Preserve deterministic output, symmetry where intended, UV face-corner alignment, manifoldness, and standing-height contracts unless intentionally migrating them.
- More polygons are acceptable when they add anatomical/deformation value; generic subdivision alone is not the quality goal.

## Rig/deformation

- `rigging/deforming.py` owns Human deformation skeleton/weights.
- Current quality work has softened major-joint blending without introducing a separate animator control rig.
- Keep export/deformation concerns distinct from any future animator-control abstraction.

## Semantic shaping

- `providers/human_semantic.py` applies semantic Human operations.
- The semantic system should create identity from a credible neutral base, not compensate for missing basic anatomy.

## Architecture boundary

Nothing under `object_core` should depend on `bpy` or `blender_adapter`.

Fast checks:
- `python -m unittest discover -s tests/core -v`
- boundary tests in `tests/core/test_architecture_boundaries.py` and `tests/core/test_provider_boundaries.py`
