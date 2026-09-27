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
  and four-limb centerlines, validated body cross-sections, all 17 current bones,
  bilateral roles and four
  torso/limb attachment declarations. It replaces the front-limb proof class.
- `providers/quadruped_geometry.py` consumes resolved landmarks/body sections and
  limb dimensions,
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

The initial canine migration preserved the 280-vertex/274-face neutral mesh and
15-bone rig. Recipe version 3 deliberately changes those to 312 vertices,
306 faces and 17 bones by adding a raised hock and distal segment to each hind
leg. Hind surface and rig joint centers now share the same landmarks. Front
limbs retain their earlier surface/rig differences. The coarse current form is
not a completed canine anatomy quality milestone.

Canine recipe version 2 restricts each limb to its resolved chain, plus the parent
at the authored attachment loop. The existing distance/local-hierarchy weighting
operates within those candidates. Torso/head/tail weighting remains spatial and
needs refinement alongside the upcoming rest-anatomy work. This intentionally
changed canine weights while preserving neutral geometry, rig and clip data
at that checkpoint. Version 3 additionally changes hind geometry and rest rig.

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

## Hind-leg stance (recipe version 3)

Each hind chain now resolves hip -> knee -> hock -> paw. Existing `hind_upper`
and `hind_lower` bone names remain, with a new `hind_pastern` child starting at
the hock. The knee is forward of the hip and the raised hock is behind it; the
paw endpoint is forward of the hock. These proportions are an authored neutral
reference, not breed-specific anatomical measurements. The distinction between
stifle and hock is informed by the [University of Illinois rear-limb anatomy
reference](https://vetmed.illinois.edu/demo-sa-orthopedics/orthopedic-exam-rearlimb/).

Hind tubes now have eight rings (64 vertices per limb), fuller upper sections
and support near the hock. A consistent sagittal frame prevents the old tangent
rule from flipping a ring when the leg changes direction. Interior hind rings
use the angle bisector of incoming/outgoing segments; this prevents an inner
fold found at the longest-body/shortest-height parameter corner. Front-limb and body
construction are unchanged. Existing motion tracks still resolve; new distal
bones inherit their parent motion. Dedicated gait/hock tuning remains ahead.

Core tests check connected, consistently wound topology, outward local hind-tube
faces and mirrored, ordered hind landmarks at all 32 parameter corners, plus independent hock movement
through both geometry and rig. Blender checks actual distal articulation and
other-limb isolation. `tests/fixtures/canine_v2_default.json` is a frozen previous
surface from `ce279f6`, used to prove incompatible saved geometry is preserved
and procedural Modify is blocked. To use version 3 on an older asset, explicitly
create a new Quadruped; there is no automatic topology, weight or Action migration.

Reproduce four-view clay/silhouette/wireframe sheets:

```powershell
blender --background --factory-startup --python scripts/render_canine_review.py -- --output artifacts/shared-anatomy/canine-hind-final-default.png
```

Use `--sample contrasting` for the second proportion set and `--pose knee` or
`--pose hock` for evaluated joint diagnostics. The renderer uses the real provider
and Blender adapter; it also checks pose movement and other-limb isolation. Each
sheet has adjacent JSON recording recipe/version, parameters, commit, landmarks,
counts and pose measurements. It reuses the existing camera/material helpers.

Before/after neutral clay, silhouette and wireframe views were inspected: the
hind bend is now readable and the rings remain continuous. This is a rest-chain
checkpoint, not acceptance of the complete canine. The torso/head remain coarse;
front legs, actual paw shape and ground contact still need refinement. The
contrasting neutral and bent knee/hock clay/wireframe sheets were also inspected:
limbs remain attached and the joints move independently; coarse body transitions
and broad joint blending still limit the result. Diagnostic movements are not
proof of final gait or ground-contact quality.

All 383 core tests, 236 Blender integration tests, actual canine plugin
save/reopen and the isolated packaged add-on check pass on the final surface. The six
baseline samples show only intended Quadruped mesh/rig/weight changes; Human,
Avian and all clip data are unchanged. Logs use the `canine-hock-` prefix and
final images use `canine-hind-final-` under `artifacts/shared-anatomy/`. The save/reopen script
is also wired into CI; CI coverage remains unverified locally.

## Torso recipe (version 4)

`ResolvedCanineAnatomy` now carries immutable, validated `CanineBodySection`
records alongside the shared anatomy contract, following the existing Human
payload pattern. Species-specific body widths/depths live in the recipe; the
surface builder consumes them and retains ownership of topology and region
membership. Tests demonstrate that changing one section width moves only its
ring without changing the rest rig. No generic recipe language or registry was
introduced.

The neutral profile has a narrower, raised abdominal section and a fuller,
deeper chest. The front-limb attachment flares into the shoulder. The neck center
also stays behind the head across supported proportions. Body rings use the
same stable sagittal frame as the hind construction. Mesh counts remain
312 vertices/306 faces and the rest skeleton remains 17 bones with the same
endpoints as version 3. Geometry and weights change intentionally; existing
saved versions still require explicit replacement to adopt the new shape.

Default/contrasting clay, silhouette and wireframe sheets were inspected and
show the intended waist/chest separation. Local body faces point outward on
both samples. The renderer now supports `--pose shoulder`; the evaluated clay
and wireframe views were inspected, with no displacement of other limbs. The
shoulder transition remains coarse and needs further shaping/deformation work.
All 385 core tests pass. The six-sample baseline comparison confirms that only
Quadruped geometry/weights change from version 3; all rigs, clip data, Human and
Avian output remain unchanged. All 236 Blender integration tests, real canine
save/reopen, the rebuilt package check, compilation and whitespace checks pass.
Evidence uses the
`artifacts/shared-anatomy/canine-torso-` prefix.

This remains a coarse canine reference. Detailed scapular anatomy, front-joint
stance, paws/contact, head/ears and final animation quality remain unfinished.

## Refined canine surface (version 5)

The single construction pipeline now builds an internal control cage and applies
two portable Catmull-Clark passes (`quadruped_refinement.py`). The generated
surface has 6,146 vertices and 6,144 quads. UVs are projected after refinement;
authored region indices and ordered connection loops propagate at each pass.
Open, non-manifold or inconsistently wound cages are rejected. The cage is an
intermediate construction step, not another provider or a Blender modifier.

Connected ears support shape/scale Modify and retain head-bone ownership after
edits. Head edits include the ears. The skull is fuller, the muzzle narrower,
and limb/paw sections fuller. Body openings now match the correct lateral side;
fore openings sit beside the shoulders. Branch surfaces start at their openings
rather than folding up to the rig pivot and back down. Symmetric bridges avoid
introducing lateral differences during refinement.

The 17-bone rest rig and animation data are unchanged. Older saved geometry is
preserved and requires explicit replacement to adopt this surface. Ring-center
landmark tests cover the cage; final-surface tests cover topology, mirrored limbs,
region ownership, real boundary edges, UVs and skinning. All 32 parameter corners
are included. Blender checks ear Modify/head posing and distal hock movement.

Default and contrasting neutral clay/wireframe views were inspected. Neutral
body joins are smoother; the evaluated shoulder pose still shows chest pinching
from broad body weights. Functional pose isolation is not final deformation
acceptance. Evidence uses `artifacts/shared-anatomy/canine-realism-*`.

Validation: 389 core tests, the full 236-test Blender suite, and all six focused
canine Blender tests (including the new ear test) pass. Real canine save/reopen,
the rebuilt isolated package, compilation and whitespace checks pass. The six
baseline samples change only Quadruped geometry and weights; all rest skeletons,
clips, Human and Avian output are unchanged. CI coverage remains unverified locally.

This is a smoother anatomical starting point. Eyes, nose/mouth detail, toes,
coat detail and final gait/contact quality remain unfinished.

## Localized attachment weights (2026-09-27)

Limb weights now occupy their authored region and the connected bridge between
its declared loops. Body vertices use axial bones. A topology-distance blend
holds the body loop on the parent and transitions to the upper limb; the limb
loop retains 25% parent weight. This remains stable after large Modify edits.
The helper rejects empty, overlapping or escaping boundaries. No geometry, rest
rig or clip data changes, and artist-owned saved weights are not overwritten.

Shoulder diagnostics now measure torso/head/tail displacement as well as other
limbs. The inspected shoulder pose loses the large chest/neck folds; a small
local crease remains at the attachment. Evidence uses `canine-shoulder-local*`
and `shoulder-*` under `artifacts/shared-anatomy/`. All 392 core tests and 238
Blender tests pass, together with the actual canine save/reopen and isolated
package checks. All 32 parameter corners have bounded normalized attachment
blends. The six-sample baseline confirms only Quadruped weight changes.

## Next work

Continue refining the canine reference body: scapula/pelvis detail, neck/muzzle,
front-joint stance and paws, then localized weights and pose review. Make geometry
and rig changes deliberately with baseline comparisons. After the canine quality
pass, migrate Avian through the same layer using bird-specific rules.
