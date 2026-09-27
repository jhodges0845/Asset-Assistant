# Shared anatomy implementation checkpoint

Current implementation: September 27, 2026, recipe version 7 following diagnostic commit `7b9768e` on
`codex/shared-generation-system`. Human and Quadruped use shared resolved-anatomy
contracts. Canine recipe version 7 is implemented; visual refinement continues.
Avian still uses its existing provider construction and awaits recipe migration.
This is a development-branch checkpoint, not a release or final anatomy acceptance.

## Current behavior

The canine generates one connected surface with 6,274 vertices, 6,272 quads and
17 bones. It has a tucked waist, fuller chest, connected ears, a distinct muzzle,
and separate hip/knee/hock/paw hind chains. Two portable subdivision passes refine
the control cage while preserving authored region and attachment ownership.

Shape/scale Modify executes for body, torso, chest, waist, head, muzzle, tail,
both ears and all four limbs. Profiles include broad chest/head, tucked waist,
long muzzle/tail and sturdy limbs. Indexed selection remains stable after edits;
head edits include ears, while muzzle edits stay within the muzzle region.
Coat/accessory operations are not executable canine geometry capabilities.

Limb weights follow authored chains. A topology-distance blend spans each limb's
attachment bridge: the body loop follows its parent and the limb loop retains
25% parent influence with the default influence limit. The remaining body uses
axial bones; ears follow the head. Shoulder poses no longer pull the chest and
neck into large folds. A small attachment crease remains. Version 7 brings all four neutral soles to their
recipe ground plane through a localized post-refinement height map below the
ankle/hock. It preserves vertices at/above those heights, surface topology and rest-rig landmarks.

## Construction and ownership

`provider validation -> recipe resolution -> control surface + bound regions -> refinement -> rest rig -> weights / Modify -> existing Blender workflow`

Providers remain the public compatibility boundary. Human and Quadruped retain
their existing identities, controls and animation APIs. Shared anatomy does not
introduce a registry or an alternative Blender generation workflow.

| Source under `object_core/` | Responsibility |
| --- | --- |
| `anatomy/contracts.py` | Immutable recipe identity, landmarks, regions, chains, symmetry and connection declarations. |
| `providers/human_anatomy.py` | Human recipe, proportions, shape reference and rest landmarks. |
| `geometry/surface_human.py`, `surface_human_builder.py`, `human_shaping.py` | Human topology, audits and shape controls. |
| `rigging/surface_human.py` | Human bones from resolved chains. |
| `providers/quadruped_anatomy.py` | Canine landmarks, body profiles, 17 bones and six connections: four limbs and two ears. |
| `providers/quadruped_geometry.py` | Internal control cage, region indices, body/branch attachment loops and final UV projection. |
| `providers/quadruped_refinement.py` | Two subdivision passes; propagates regions and ordered loops. Cage loops of 4/8 vertices become 16/32 on the final surface. |
| `providers/quadruped_rigging.py` | Rest chains, authored limb/ear ownership and localized attachment blends. |
| `providers/quadruped_semantic.py`, `semantic_geometry.py` | Species profiles and shared validated indexed transforms. |
| `providers/quadruped.py` | Public provider, full recipe/version/parameter cache identity and topology compatibility checks. |

Core/providers remain Blender-independent. Edited meshes recompute weights;
incompatible topology is rejected before indexed edits. Human attachment loops
remain unauthored, with whole-surface connectivity/winding audits providing its
topology gate. Canine declared loops are tested against actual surface edges.

## Use the new canine in Blender

Build with `python -m scripts.build_blender_addon`, then install/update
`dist/asset_assistant.zip` using the [installation guide](blender.md). Choose
**Quadruped** in Create and generate a new asset. Use the existing Modify and
Animate > Rig & Pose workflows; Idle/Walk/Run remain available.

Saved surfaces from older recipe versions are preserved. Create a new Quadruped
to adopt version 7; there is no automatic topology, weight or Action migration.
Manual artist edits continue to block procedural replacement. Installing the
updated add-on alone does not upgrade existing geometry or artist-owned weights.

## Validation and reproducibility

Historical version 6 local results for `79c855b`: 394 core tests and 238 Blender tests passed,
as did actual canine save/reopen, isolated package verification, compilation and
whitespace checks. The version 6 six-sample comparison changed only Quadruped
mesh/weights from the prior checkpoint; all rest rigs, clips, Human and Avian
outputs stayed unchanged. Local results do not establish remote CI/coverage status.

Run from the repository root with `blender` on PATH (or substitute its full path):

```powershell
python -m unittest discover -s tests/core -v
blender --background --factory-startup --python-exit-code 1 --python scripts/test_blender.py
blender --background --factory-startup --python-exit-code 1 --python scripts/test_canine_reopen.py
python -m scripts.build_blender_addon
blender --background --factory-startup --python-exit-code 1 --python scripts/test_blender_package.py
New-Item -ItemType Directory -Force artifacts/shared-anatomy | Out-Null
python scripts/anatomy_baseline.py --output artifacts/shared-anatomy/current-baseline.json
blender --background --factory-startup --python-exit-code 1 --python scripts/render_canine_review.py -- --output artifacts/shared-anatomy/current-canine.png
```

Add `--sample contrasting`, `--region head`, or `--pose shoulder` / `elbow` / `hip` / `knee` /
`hock` after the script separator for additional reviews. Head crops show a cut
neck boundary; the generated whole model remains connected. Adjacent JSON records
parameters, recipe/version, source state, counts and pose-isolation measurements.
Pose checks include torso/head/tail and other-limb displacement.

Current local evidence uses `canine-muzzle-*` and `muzzle-*` in
`artifacts/shared-anatomy/`; shoulder comparisons use `canine-shoulder-local*`
and `shoulder-*`. Artifacts and the ZIP are generated locally, not committed.
The committed `anatomy-baseline-2026-09-26.json` is the historical pre-migration
numeric baseline. Compare fingerprints on the same Python/runtime; timings are
observations, not acceptance thresholds.

## Checkpoint history

The sections below describe results at each checkpoint, including limitations
that later work may supersede. Use the current behavior above for today's state.

| Commit | Checkpoint |
| --- | --- |
| `381637d`, `bfecc5e` | Shared contracts/baseline and Human/Quadruped proof slices. |
| `36cd967` | Full Human recipe migration. |
| `be3d778` | Canine construction migration and executable Modify. |
| `ce279f6` | Authored limb-chain weights. |
| `2223c85` | Separate hind knee/hock/paw chains. |
| `13b5fbc` | Recipe-owned torso profiles. |
| `f99db79` | Refined surface, connected ears and symmetric joins. |
| `8d88708` | Localized attachment blending and body isolation. |
| `79c855b` | Distinct muzzle and stable facial cross sections. |

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

## Muzzle profile (version 6)

The recipe adds a muzzle-base section between the skull and nose tip. A lower,
narrower muzzle and raised forehead give the smoothed surface a distinct snout.
Facial depth is bounded by head length; vertical facial cross sections prevent
neck curvature from rolling the underside through itself at parameter limits.
The generated surface now has 6,274 vertices and 6,272 quads. Rest bones and clip
data are unchanged. Older generated surfaces require explicit replacement.

Muzzle Modify includes the new base and tip; head Modify includes both and the
ears. Tests check independent recipe control and outward-facing facial cage
sections across all 32 parameter corners. The review renderer supports
`--region head` for a diagnostic crop of the real generated surface, with the
cut neck boundary visible. This is a shape pass; eyes, nose and mouth detail,
toes and coat remain ahead.

Default and contrasting clay/silhouette or wireframe views and the head close-up
were inspected. Evidence uses `canine-muzzle-*` and `muzzle-*` under
`artifacts/shared-anatomy/`. The six-sample baseline changes only Quadruped
geometry and weights; all rest rigs, clips, Human and Avian output are unchanged.
All 394 core tests and 238 Blender tests pass, together with actual canine
save/reopen, the rebuilt isolated package, compilation and whitespace checks.

## Ground-contact diagnostics (September 27, 2026, local continuation)

The review script now supports isolated elbow (`fore_lower.left`) and hip
(`hind_upper.left`) poses in addition to shoulder, knee and hock. Its JSON reports
neutral and evaluated posed ground clearance for each authored limb against the
recipe's Z=0 plane, in centimeters. Positive minimum Z is a gap; negative minimum
Z is penetration. Measurements use the full generated surface before any head
crop. They do not establish gait contact, contact drift or visual acceptance.

The version 6 neutral default surface has front gaps of 0.824 cm and hind gaps
of 2.243 cm. The documented contrasting sample has front gaps of 0.925 cm and
hind gaps of 1.405 cm. Both sides agree. This confirms paw/contact refinement
remains necessary; changing an object-level ground offset alone cannot equalize
front and hind contact. Local evidence is
`artifacts/shared-anatomy/canine-ground-clearance.json`.

All 396 core tests, Python compilation and whitespace checks pass. A Blender regression covers
both new poses and both samples, including isolation and independently calculated
minimum heights. Local Blender 2.92 could not import the suite because its bundled
Python lacks `typing.Protocol`; the new pose regression and rendered reviews
were unverified at that checkpoint. The version 7 continuation below uses a verified
portable Blender 5.2.1 runtime to exercise them. No surface, rig, weights,
clip data or recipe version changes are included in this diagnostic slice.

## Neutral sole contact (recipe version 7)

The refined cap previously left unequal gaps under front and hind paws. The
canonical surface constructor now resolves each authored limb's sole to its
recipe ground plane after subdivision, before final UV projection. A monotone
height map below the front ankle or hind hock preserves vertical ordering and
has unit slope at the fixed upper transition. It does not flatten faces or move
other regions. Hind ground landmarks are now explicit; rest bones are unchanged.

Version 7 preserves the 6,274 vertices, 6,272 quads, connection loops and region
indices. Saved surfaces remain untouched; explicitly create/replace a generated
asset to adopt the new construction. Modify still permits lifting/moving a foot;
this construction step never re-grounds edited meshes. This establishes neutral
sole contact only, not a support patch, detailed paw anatomy or gait acceptance.

Regression coverage checks default/contrasting proportions and all 32 parameter
corners, signed ground height, monotone ordering, unchanged non-distal vertices,
unchanged ownership/topology, exact repeated application and lifted-foot Modify.
Default and contrasting neutral clay/silhouette/wireframe sheets and isolated
elbow/hip clay/wireframe sheets were inspected in Blender 5.2.1. All four neutral
limbs report 0 cm minimum Z in both samples; both diagnostic poses report zero
other-limb and torso/head/tail displacement. The surfaces remain coarse paws,
with the existing shoulder/hip creases still visible. Neutral contact does not
establish anatomical or animation acceptance.

All 398 core tests, compilation and whitespace checks pass.
All 239 Blender integration tests pass, including the prior elbow/hip diagnostic
regression. Actual canine save/reopen and the rebuilt isolated ZIP check pass.
The six-sample baseline comparison changes only Quadruped mesh/weight fingerprints;
all rest rigs, clips, Human and Avian outputs are unchanged. Evidence and logs use
`artifacts/shared-anatomy/contact-*`; baseline records are `contact-before.json`
and `contact-after.json`. Remote CI status is not established by these local runs.

A SHA-256-verified portable Blender 5.2.1 runtime is available locally at
`artifacts/installers/blender/runtime/blender-5.2.1-windows-x64/blender.exe`.
Use that executable in the validation commands above; the globally installed
Blender 2.92 cannot import the current project. The runtime and review artifacts
are ignored local files, not committed dependencies.

## Paw support diagnostic baseline (September 27, 2026)

The canonical review script now records `neutral_support_footprint` and, for
joint diagnostics, `posed_support_footprint`. Each limb reports the XY convex
hull area, width and length of its authored surface within Z=0..0.1 cm. Edge
intersections include sloped faces even when no mesh vertex lies in that band.
The band is measured from the fixed ground plane, so lifting a foot removes its
footprint. Read these values alongside signed clearance: the hull spans gaps
and concavities, excludes penetration below the plane, and is not physical
contact area or a gait-support acceptance test.

| Version 7 sample | Front paw hull (cm²) | Hind paw hull (cm²) |
| --- | ---: | ---: |
| Default | 0.4724 | 1.2588 |
| Contrasting | 0.5870 | 0.8536 |

Left/right values agree. The baseline covers neutral and isolated elbow, hip,
knee and hock poses for both samples in Blender 5.2.1; local evidence is
`artifacts/shared-anatomy/support-baseline.json`. The normal review commands
above reproduce these measurements in their adjacent JSON. This diagnostic
slice does not alter recipe version 7 geometry, rig, weights or clips.

Portable tests cover analytic clipped footprints, flat versus point contact,
raised/penetrating surfaces, invalid input, generated symmetry and lifted-foot
Modify. Blender regression coverage checks that elbow/hip poses change the
selected footprint while preserving the other three. Paw shape/support-area
refinement and front-joint stance remain the next construction work. All 402
core tests and the three focused Blender deformation tests pass.

## Next work

Next, refine paw shape/support area and front-joint stance using the grounded
version 7 surface as the baseline. Review shoulder/hip attachment creases and
repeat default/contrasting neutral and elbow/hip/knee/hock diagnostics with the
portable Blender 5.2.1 runtime above. Neutral sole contact is complete; planted
support through a gait cycle and contact drift remain open.

Eyes, nose/mouth detail and scapula/pelvis shaping also remain in the canine
quality pass. Compare geometry, rig, weights and clips deliberately against the
baseline and preserve artist-owned edits. After canine visual acceptance, migrate
Avian through the same layer using bird-specific rules, then continue the shared
anatomy/Modify acceptance and cross-provider animation milestones in the alpha plan.
