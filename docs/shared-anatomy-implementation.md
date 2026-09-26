# Shared anatomy implementation checkpoint

The first implementation on `codex/shared-generation-system` adds the portable
contract in `object_core/anatomy/contracts.py` and the numeric baseline harness
in `scripts/anatomy_baseline.py`. Existing provider construction is unchanged.

The contract records recipe/version/parameter identity, model-space landmarks,
mesh-part-scoped region ownership, parented joint chains, bend directions,
region symmetry and declared connection boundaries. Inputs are copied into
immutable tuples. Resolution validates references and acyclic bone parents;
`validate_mesh` checks membership and boundary indices against output meshes.
It does not assert manifoldness, connected joins or anatomical quality.

There is no registry, generic body-part generator or second provider workflow.
Local frames and provider-owned construction payloads should be added only as
the Human and Quadruped proofs demonstrate their required shape.

## Reproduce the portable baseline

```powershell
python scripts/anatomy_baseline.py --output anatomy-baseline.json
python -m unittest discover -s tests/core -p test_anatomy_contracts.py -v
```

The recorded `anatomy-baseline-2026-09-26.json` includes the source commit,
working-tree changes, Python/platform identity, default and contrasting provider
parameters, mesh counts, bone counts, output SHA-256 fingerprints and measured
construction times. Each sample runs in a fresh process. Mesh, rig, skinning and
available animation outputs are fingerprinted; a warmed mesh call also checks
repeatability. Timings include the public provider call and its dependencies,
not serialization, and are observations rather than acceptance thresholds.
Do not sum them as independent subsystem costs. Compare fingerprints using the
same Python/runtime before interpreting a difference as a provider regression.

This is the **portable numeric baseline**, not complete visual acceptance.
Clay/silhouette/wireframe, representative deformation poses and Blender playback
timing still need capture before migration acceptance. The existing
`inspect_human_deformation.py` covers Human pose review. No geometry or rig
migration is included in this checkpoint.

## Next reviewable slices

1. Human shoulder/elbow/wrist proof using authored arm ownership.
2. Quadruped torso and one front-limb proof, with mesh and rig consuming the same
   resolved landmarks.
3. Review both uses for body-plan independence before full Human migration.
4. Build canine anatomy, then Avian anatomy, through the existing providers and
   Blender workflow as specified in `anatomy-recipe-contract.md`.

## Validation for this checkpoint

- Python 3.9.13: all 360 core tests passed, including six new anatomy tests.
- New Python sources compile; tracked-file whitespace checks pass.
- Baseline harness completed all six provider/sample combinations.
- Blender integration and visual reviews were not run for this metadata-only
  increment. Coverage tooling is not installed locally; the CI coverage gate
  remains to be checked.
