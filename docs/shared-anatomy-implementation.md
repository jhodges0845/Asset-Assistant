# Shared anatomy implementation checkpoint

Branch: `codex/shared-generation-system`. Foundation: `381637d`; initial two-body
proof: `bfecc5e`; Human migration: `36cd967`. Canine migration: `be3d778`. That increment migrates
the entire existing Quadruped construction and enables semantic Modify. Canine
anatomical quality refinement and Avian recipe migration remain ahead.

## Current construction layers

`provider validation -> recipe resolution -> surface + bound regions -> rest rig -> weights / Modify -> existing Blender workflow`

Providers remain the public compatibility boundary. The `human` and `quadruped`
identities, generation controls, animations and export contracts are preserved.
There is no new registry, discovery UI or alternative generation pipeline.

- `object_core/anatomy/contracts.py` owns immutable, body-plan-independent recipe
  identity, landmarks, regions, chains, symmetry and attachment declarations.
- `providers/human_anatomy.py` resolves Human controls and all rest landmarks.
  Its compact immutable payload contains proportions and the shape reference.
- `geometry/surface_human.py` owns authored topology and limb membership;
  `surface_human_builder.py` audits it; `human_shaping.py` applies recipe controls.
  `rigging/surface_human.py` converts resolved chains directly to bones.
- `providers/quadruped_anatomy.py` owns `CanineRecipe`: complete torso/head/tail
  and four-limb centerlines, all 15 current bones, bilateral roles and four
  torso/limb attachment declarations. It replaces the front-limb proof class.
- `providers/quadruped_geometry.py` consumes resolved landmarks and dimensions,
  then binds region indices and four/eight-vertex attachment loops from the
  rings it actually constructs. `quadruped_rigging.py` consumes resolved chains.
- `providers/quadruped.py` caches mesh plus bound anatomy by recipe ID/version
  and every validated dimension. Skinning uses authored limb chain ownership,
  so moving a limb across the centerline or over another limb cannot transfer its
  weights. Only the declared limb attachment loop may blend to the chain parent.
- `providers/semantic_geometry.py` provides the existing numeric validation and
  indexed transforms shared by Human, Quadruped and Avian semantic executors.
  Body-specific profiles remain in their respective providers.

Human mesh, rig and weight caches normalize call style and include recipe
identity/version and all controls. Edited meshes recompute weights. Topology
changes are rejected before applying indexed ownership.

## Executable Quadruped Modify

Shape/scale operations now execute for body, torso, chest, waist, head, muzzle,
tail and all four limbs. They use authored membership, including after vertices
move, and preserve topology/UVs. Profiles include broad chest/head, tucked waist,
long muzzle/tail and sturdy limbs. Independent x/y/z scaling and offsets use the
same validated transformation contract as Human and Avian.

Ear, coat and accessory operations are not advertised as executable geometry
capabilities. The current surface does not yet have constructed ears. The generic
planner blocks those unsupported operations. The Blender integration tests prove
that planning does not mutate the mesh, explicit apply retains a deforming rig,
and manual artist edits block procedural replacement.

## Intentional behavior and quality limits

Human limb operations use authored membership and the rig's labels (+X is left
for this Human), correcting the previous spatial selection's reversed sign and
nearby-region leakage. The Human reference-height rounding correction preserves
valid input at the range endpoints. All five body types and both height/weight
limits are tested. Saved artist work is never silently regenerated.

The canine migration preserves the existing 280-vertex/274-face neutral mesh,
15-bone rig and motion. Its current surface/rig centerlines remain distinct, and
lower-leg bones end at ground level while surface ankle/paw landmarks are above
it. The coarse current form is not a completed canine anatomy quality milestone.

Canine recipe version 2 restricts each limb to its resolved chain, plus the parent
at the authored attachment loop. The existing distance/local-hierarchy weighting
operates within those candidates. Torso/head/tail weighting remains spatial and
needs refinement alongside the upcoming rest-anatomy work. This intentionally
changes canine weights; neutral geometry, rig and clip data remain unchanged.

Human attachment declarations do not yet contain local boundary loops; the
whole-surface connectivity/winding audit remains the topology gate. Quadruped
loops are bound and tested against actual bridge faces. Region membership uses
integer indices, not rich per-vertex objects; body deliberately contains its
subregions. No generic local-frame machinery was needed for this extraction.

## Validation and reproducibility

```powershell
python -m unittest discover -s tests/core -v
python scripts/anatomy_baseline.py --output anatomy-baseline.json
```

The recorded `anatomy-baseline-2026-09-26.json` contains pre-migration defaults and
contrasting parameter samples for Human, Quadruped and Avian. Each sample uses a
fresh process; timings are observations, not acceptance thresholds. Compare
fingerprints on the same Python/runtime.

Canine extraction checkpoint (`be3d778`) evidence, Python 3.9.13 / Blender 5.2.1:

- All 378 core tests pass; all 233 Blender integration tests pass.
- All six mesh/skeleton/weights/animation fingerprint sets match the baseline.
- Packaged add-on verification passes in Blender 5.2.1.
- Python compilation and whitespace checks pass.

Logs/report: `artifacts/shared-anatomy/canine-core-tests.log`,
`canine-blender-tests.log`, `canine-package-tests.log`, `canine-baseline.json`.
The installable build is `dist/asset_assistant.zip`. CI coverage remains pending
because coverage tooling is not installed in local Python.

The prior Human checkpoint also passed real Human/component save-reopen and all
seven pose checks; its rendered diagnostic was inspected. Evidence is under the
same artifact directory with the `human-` prefix. Neutral baseline parity does
not establish final anatomical quality. New canine profile quality still needs
clay, silhouette, wireframe and deformation review alongside the body refinement.

## Localized canine limb weights (recipe version 2)

A front leg moved over a hind leg previously acquired hind weights on all 48
vertices. Core regressions now cover every limb moved across front/hind, side,
head and tail positions, attachment-parent blending, influence limits and
parameter endpoints. A Blender regression applies the move through Modify,
evaluates the armature, and proves the moved front limb ignores a hind rotation
while still deforming under its own joint. Artist-edit protection remains tested.

The six-sample comparison confirms that only Quadruped weights changed; Human,
Avian, all neutral meshes, skeletons and clips are identical to the baseline.
All 381 core tests, 234 Blender integration tests and the isolated packaged
add-on check pass. Compilation and whitespace checks pass. Reports use the
`artifacts/shared-anatomy/canine-local-weights-` prefix.

This is a deformation isolation checkpoint, not final canine visual acceptance.
No saved scene is automatically regenerated; new weights are used when the
existing workflow explicitly creates, rigs or applies a generated modification.

## Next work

Refine the canine recipe into a convincing reference body: chest/scapula/pelvis,
neck/muzzle/ears, digitigrade hind-limb chain and paws, then localized weights and
pose review. Make geometry/rig changes deliberately with baseline comparisons;
do not represent that quality milestone as completed by the preserved coarse
mesh. After that, migrate Avian through the same layer using bird-specific rules.
