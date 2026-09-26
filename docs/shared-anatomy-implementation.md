# Shared anatomy implementation checkpoint

The foundation is committed as `381637d` on `codex/shared-generation-system`.
The next increment proves the same portable anatomy contract against Human arms
and a Quadruped torso/front-left limb. Full provider migration is still ahead.

## Code ownership

- `object_core/anatomy/contracts.py`: immutable recipe identity, landmarks,
  mesh-part-scoped regions, joint chains, bend directions, symmetry and declared
  connection boundaries. Validation checks references, bone-parent cycles and
  mesh index bounds; it does not establish anatomical or visual quality.
- `object_core/providers/human_anatomy.py`: `HumanArmRecipe` describes current
  shoulder/elbow/wrist/hand endpoints and both authored arm regions. Human
  skinning now reads those shared region records. Rest-rig and surface
  construction remain in their existing modules; this is not full Human
  source-of-truth migration.
- `object_core/providers/quadruped_anatomy.py`: `QuadrupedFrontRecipe` resolves
  torso/chest, shoulder, elbow, ankle, paw and existing rig-ground landmarks from
  provider-validated dimensions. The existing mesh and rig builders consume
  those resolved landmarks. Geometry binds region membership and shoulder
  boundaries from the actual rings it constructs, then validates bounds.
- `tests/core/test_anatomy_proofs.py`: actual provider proofs, boundary cases,
  authored bridge connectivity and a perturbed elbow that must drive both
  surface and bone endpoints. Other limbs remain outside this small proof.

Both providers retain their existing public interfaces and identities. Blender
still receives the same mesh, skeleton, weights and animation contracts.

## Two-body-plan architecture review

The shared anatomy types represent both proofs without species conditionals,
provider imports, a registry, or one rich object per vertex. Region ownership is
stored as integer indices and remains valid when vertices move. The Quadruped
shoulder declares a four-vertex torso opening and an eight-vertex limb boundary;
its authored bridge faces connect them. Human bilateral ownership comes directly
from the surface builder rather than a spatial classification.

The proof also exposes two existing Quadruped distinctions: surface and rig
centerlines are not identical, and the lower-leg bone ends at ground level while
the surface ankle/paw sit above it. The recipe names these separately to preserve
current behavior. Reconciling them and adding an articulated paw belong to the
canine quality migration, not this output-preserving extraction.

Quadruped membership is bound after construction because the constructor owns
vertex ordering. Empty regions/boundaries in the initial recipe resolution mean
pending authorship, not accepted topology. Full recipe orchestration should
return the bound result to skinning and semantics. Human's proof still derives
landmarks from its current rig; reversing that dependency is the next migration.
No local-frame or generic construction-payload abstraction was needed yet.

## Reproduce the portable baseline

```powershell
python scripts/anatomy_baseline.py --output anatomy-baseline.json
python -m unittest discover -s tests/core -p test_anatomy_proofs.py -v
```

`anatomy-baseline-2026-09-26.json` records pre-extraction commit, environment,
parameters, mesh/bone counts, output SHA-256 fingerprints and generation timings
for default and contrasting Human, Quadruped and Avian samples. Every sample uses
a fresh process. Timings are observations, not thresholds; each public provider
call includes its dependencies, so do not sum them as independent costs.
Compare fingerprints using the same Python/runtime.

The proof run is saved locally as `artifacts/shared-anatomy/proof-baseline.json`.
All six samples retain exactly matching mesh, skeleton, weights and animation
fingerprints. Four proof tests also exercise minimum/maximum Quadruped dimensions
and verify that an intentionally moved elbow updates both mesh and rig.

This is portable numeric evidence, not complete visual acceptance. Clay,
silhouette, wireframe, bend-pose review and playback timing remain required before
accepting anatomical quality changes. Current outputs are preserved exactly for
the recorded samples; no visual quality improvement is claimed.

## Validation

- Python 3.9.13: all 364 core tests pass.
- Focused Quadruped provider tests: all 10 pass.
- All six baseline output fingerprint sets match the recorded baseline.
- Blender 5.2.1: all 231 integration tests pass.
- Isolated installable ZIP check passes: generation, rigging, animation, validation
  and export. Built add-on: `dist/asset_assistant.zip`.
- Detailed logs: `artifacts/shared-anatomy/proof-core-tests.log`,
  `proof-blender-tests.log` and `proof-package-tests.log`.
- Coverage tooling is not installed in local Python; CI coverage remains pending.

## Next implementation slice

Move Human construction onto the reviewed seam while retaining controls,
semantic edits, authored region constraints and existing Blender behavior.
Then expand canine anatomy and later Avian through the same provider boundary.
Avoid treating a wing as a renamed arm or a canine hind limb as a Human leg.
