# Shared anatomy implementation checkpoint

Current implementation: September 27, 2026, recipe version 9 at `572813c` on
`codex/shared-generation-system`. Human and Quadruped use shared resolved-anatomy
contracts. Canine recipe version 9 adds localized paw volume and forward
projection to the grounded soles; visual refinement continues.
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
neck into large folds. A small attachment crease remains. Version 7 brings all
four neutral soles to their recipe ground plane through a localized
post-refinement height map below the ankle/hock. Version 8 adds a smooth cubic
underside profile. Both steps preserve vertices at/above those heights, surface
topology and rest-rig landmarks. Version 9 adds a validated recipe-owned paw
profile: horizontal width/length and forward projection fade smoothly below
a low-paw transition, capped below each ankle/hock. It preserves every height,
upper-limb vertex, rest joint and connection while making the paw end more distinct.

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
| `providers/quadruped_anatomy.py` | Canine landmarks, body/paw profiles, 17 bones and six connections: four limbs and two ears. |
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
to adopt version 9; there is no automatic topology, weight or Action migration.
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
| `7b9768e` | Elbow/hip pose and signed ground-clearance diagnostics. |
| `afe5a10` | Recipe version 7 neutral sole contact. |
| `f5c6626` | Neutral/posed paw footprint diagnostics and support baseline. |
| `9fab659` | Recipe version 8 broader grounded sole support. |
| `572813c` | Recipe version 9 localized paw volume, depth-aware review lighting and evaluated footprint regressions. |

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
core tests and the three focused Blender deformation tests pass, along with
Python compilation and whitespace checks. The full Blender suite and packaged
add-on checks were not repeated for this diagnostic-only change; remote CI
status is not established by these local results.

## Broader sole profile (recipe version 8)

The construction-only ground map now follows its contact correction with the
normalized cubic `s*s*(2-s)`. It lowers the underside smoothly, with a positive
height derivative above the sole and unit derivative at the ankle/hock boundary.
It preserves XY coordinates and height ordering without flattening faces onto
the ground. The same early exit keeps repeated grounding exact. Semantic Modify
does not run this map; lifting a paw remains possible.

Near-ground hull areas at the existing 0..0.1 cm band are:

| Sample | Front paw (cm²) | Hind paw (cm²) |
| --- | ---: | ---: |
| Default | 2.4285 | 9.2510 |
| Contrasting | 3.1248 | 6.3584 |

Both sides agree. These are diagnostic hulls, not physical contact areas.
Topology, ownership, rest landmarks and clip code are unchanged; generated
geometry and resulting weights change. Existing saved surfaces require explicit
replacement to adopt version 8.

All 403 core and 239 Blender integration tests pass, including the 32 parameter
corners, localization, monotonicity, idempotence, lifted-foot Modify and broader
support regressions. Actual canine save/reopen and rebuilt isolated package
checks pass, as do Python compilation and whitespace checks. Default neutral
and contrasting elbow clay and wireframe sheets were inspected. The elbow
diagnostic reports zero other-limb and torso/head/tail displacement. Evidence
uses `artifacts/shared-anatomy/sole-*`.

This is a limited underside refinement: paws remain coarse, attachment creases
remain visible, and detailed paw anatomy, front stance and gait acceptance remain
open. The follow-up below completes the clay/wireframe pose matrix and six-sample
fingerprint comparison. Remote CI status remains unverified.

## Version 8 review matrix and lighting repair (September 27, 2026)

Reviewed all 12 combinations of default/contrasting proportions and neutral,
shoulder, elbow, hip, knee and hock poses at `9fab659`. Each has four-view clay
and wireframe sheets plus JSON under `artifacts/shared-anatomy/sole-matrix-*`.
All neutral limbs have minimum Z=0 cm. All ten joint diagnostics pass movement
and isolation checks with exactly zero other-limb and torso/head/tail movement.
Moving-limb minimum Z values are positive (centimeters):

| Pose | Default | Contrasting |
| --- | ---: | ---: |
| Shoulder | 3.5263 | 2.6367 |
| Elbow | 1.5040 | 0.8205 |
| Hip | 2.2214 | 1.2117 |
| Knee | 5.7902 | 5.9762 |
| Hock | 2.0582 | 1.7053 |

These are isolated rotations, not planted gait poses or ground-contact acceptance.
The sheets show connected, articulated limbs, but paws still read as blunt tube
ends and shoulder/hip attachment creases remain. The front stance is still
straight. Silhouette-only sheets and looping gait playback were not rerun.

The matrix exposed a review-lighting defect: height-only light placement put
lights within the depth of long canine views, producing dark bands in the clay
sheets, especially the contrasting sample. `scripts/render_human_review.py` now
places the lights ahead of the nearest rotated surface with a height-based
margin, and scales light size/power with distance. This is a shared diagnostic
renderer correction; provider geometry, rigs, weights and clips are unchanged.
The original matrix retains its pre-fix lighting for provenance. Follow-up clay
renders use `sole-lighting-*` for default/contrasting neutral and contrasting
shoulder. Use these corrected views when assessing shaded surface detail.

The new `test_canine_lights_stay_in_front_of_all_review_surfaces` regression
failed on both samples before the fix. All four renderer integration tests pass
afterward, including Human wide/portrait framing and clipping checks. All 403
core tests pass; compilation and whitespace checks pass. Full Blender workflow,
package and save/reopen suites were not repeated for this review-only change.
Logs use `sole-matrix-core-tests.log` and `sole-lighting-*-tests.log`.

`sole-baseline.json` captures all six provider/sample combinations on Python
3.9.13. Compared with the recorded `contact-after.json` version 7 snapshot, only
Quadruped mesh and weight fingerprints differ. Human/Avian outputs, every rest
rig and every clip match. The reference snapshot records HEAD `7b9768e` plus
uncommitted anatomy/geometry/test edits; it must not be treated as the output of
that clean commit. Current baseline geometry is clean `9fab659`.

## Localized paw volume (recipe version 9)

Implementation commit: `572813c`. Local evidence was captured before this commit
with HEAD `9fab659` plus the recorded working-tree edits; those source changes
are now committed. Generated renders, reports and the ZIP remain local artifacts.

`CaninePawProfile` owns low-paw width/length scale, forward projection and the
transition height. Construction applies a horizontal map after the existing
sole-height map. A smooth falloff confines it below the lesser of the recipe
height and ankle/hock height; all Z coordinates stay unchanged. The profile is
validated and immutable. It runs only during construction, not on artist edits
or semantic Modify. Recipe versioning invalidates generated caches; topology,
region membership, attachment loops and the 17-bone rest rig remain unchanged.

Default width/length scales are 1.20/1.65. Forward projection is bounded by body
width and shoulder height; the amount was checked against the established elbow
pose to avoid introducing toe penetration. Paws have modestly fuller ends and
forward projection, not individual toes or pads. Front stance and attachment
creases still need work. Existing version 8 surfaces remain untouched and require
explicit replacement to adopt the new shape.

Near-ground hull areas at Z=0..0.1 cm (both sides agree):

| Sample | Front paw (cm²) | Hind paw (cm²) |
| --- | ---: | ---: |
| Default | 4.7924 | 18.2893 |
| Contrasting | 6.1666 | 12.5612 |

All 12 default/contrasting neutral and joint-diagnostic evaluations pass movement
and isolation checks. Neutral minimum Z remains exactly 0 cm; all ten posed
moving limbs have positive minimum Z, with zero other-limb and torso/head/tail
movement. The contrasting elbow has only 0.0901 cm clearance: this is a fixed
pose check, not a gait/contact guarantee. Evidence is `paw-final-poses.json`.
Default/contrasting neutral, default elbow and contrasting hock clay/wireframe
sheets use the `paw-final-*` prefix under `artifacts/shared-anatomy/`.

Pose reports now include `evaluated_neutral_support_footprint` alongside the
source-space neutral report. Stationary-paw comparisons use evaluated before/after
coordinates, avoiding double-versus-Blender-float hull-area differences without
loosening the isolation tolerance. A Blender regression protects positive moving-
paw clearance in the established elbow/hip poses.

The final six-sample `paw-final-baseline.json` comparison against
`sole-baseline.json` changes only Quadruped mesh/weight fingerprints; all rigs,
clips, Human and Avian outputs are identical on Python 3.9.13. Parameter-corner
regressions cover localization, unchanged heights, noncollapsed paw faces,
unchanged topology/ownership, useful forward support and profile validation.
All 405 core tests and 240 Blender integration tests pass on the final profile.
Actual canine save/reopen, rebuilt isolated package, compilation and whitespace
checks pass. Final logs and evidence use `paw-final-*`; remote CI is unverified.
This remains a limited shape checkpoint, not final canine visual acceptance.

## Front stance (recipe version 10)

Implementation commit: `17c6b01` (pushed to `codex/shared-generation-system`).
Generated renders, pose reports and validation logs remain local artifacts.

The recipe advances each front shoulder by `min(body_length * .04,
shoulder_height * .06)` in +Y, leaving elbow, ankle, paw and ground landmarks
fixed. The upper leg now slopes back toward the elbow; the existing lower-leg
alignment and low-paw profile remain. Both surface and rig consume the same
resolved shoulder. The 17 bone names and parents remain; upper front rest bones,
mesh and weights change. Existing assets require explicit replacement to adopt
this construction; artist-owned surfaces are not regenerated automatically.

The local `stance-before.json` / `stance-after.json` six-sample comparison changes
only Quadruped mesh, skeleton and weights. Human, Avian and all clip fingerprints
match. Default/contrasting topology, region membership and attachment loops match
the previous shoulder placement. Clay/wireframe sheets are `stance-*-neutral*`
under `artifacts/shared-anatomy/`. The visual change is modest; shoulder attachment
creases and detailed paw anatomy remain unresolved.

Expanded inspection found pre-existing distal front-cage face folds at the
shortest/widest parameter corners (height 15 cm, width 55 cm). The version 9
shoulder placement reproduces all eight affected corner combinations; evidence
is `stance-before-front-normals.log`. Upper front-ring orientation is covered by
the stance regression, while the existing hind-chain orientation gate remains.
This is not full anatomical acceptance across the entire parameter range.

Validation: all 407 core tests and 240 Blender integration tests pass. Actual
canine save/reopen passes. The 12 default/contrasting neutral and joint checks
pass movement/isolation; all ten posed moving limbs retain positive clearance,
including 0.0901 cm for the contrasting elbow. Evidence is `stance-poses.json`.
Default/contrasting neutral clay/wireframe and default shoulder clay were rendered
and visually reviewed. Compilation and whitespace checks pass. Logs use the
`stance-*` prefix. Package installation, gait playback and remote CI were not
repeated for this slice. Evidence was captured with HEAD `6cf84de` plus the
recorded working-tree edits; the final source and regression changes are now
committed in `17c6b01`. The reports retain their original capture provenance.

## Distal front-leg bounds (recipe version 11)

Implementation commit: `4fd30d6`.

The former width-only front ankle height could exceed elbow height for very
short, wide bodies. Recipe 11 bounds ankle height to half the elbow height and
paw height to 60% of ankle height; forward paw reach is limited to 8% of shoulder
height. The front cage thickness is bounded to 18% of shoulder height, using the
existing construction seam. Dimensions below these bounds retain their previous
values. Shoulder, elbow and ground landmarks remain fixed, so all rest bones and
clips are unchanged. These construction changes require explicit replacement of
older generated surfaces and do not rebase artist edits or semantic Modify.

The full front-ring outward-normal regression fails at eight version 10 parameter
corners and passes with these bounds. Coverage now includes every front and hind
ring interval, strict front-joint height ordering, grounded soles, symmetry and
connected topology. A separate 49-point height/width sweep found no inverted
front cage faces. This gate addresses cage folding; it does not establish full
anatomical quality or prove absence of all surface intersections.

The six-sample `distal-before.json` / `distal-after.json` comparison leaves every
mesh, rig, weight and clip fingerprint unchanged for default/contrasting Human,
Quadruped and Avian. The saved failing corner and corresponding renders use the
`distal-corner-*` prefix under `artifacts/shared-anatomy/`. Evidence was captured
above `49487dc` with working-tree edits; generated evidence remains local.

The 18 neutral/joint evaluations cover default, contrasting and the short/wide
sample; movement and isolation checks pass. The extreme elbow still penetrates
by 0.1361 cm, improved from 1.1549 cm when the saved version 10 mesh is evaluated
with the unchanged rig and weighting algorithm (`distal-before-elbow.json`).
This is a residual pose-contact limitation, not a neutral-fold regression.
Before/after clay and wireframe sheets show the corrected front limbs; the
extreme overall body proportions are not anatomically accepted.

All 407 core tests and 240 Blender integration tests pass; canine save/reopen,
compilation and whitespace checks pass. Logs use `distal-*`. The extreme sample
retains its exact face topology. Package installation, gait playback and remote
CI were not repeated for this slice.

## Paw close-up diagnostics (recipe 11 baseline)

`scripts/render_canine_review.py` now accepts `--region front-paw` and
`--region hind-paw`. Both select the left limb. Selection uses neutral authored
membership and whole faces touching the low-paw band (twice the larger of the
recipe paw-profile height and paw-landmark height). Evaluated pose coordinates
are then applied to the same indices. The open upper boundary is a crop, not a
new cap; no provider geometry, rig, weights or clips change.

Adjacent JSON records source vertex indices, the neutral selection height and
the chosen limb. Ground-clearance and footprint reports still describe the full
evaluated asset, not the cropped display. Body/head views retain their face
selection. Shared review layout now centers each view in depth as well as width,
so small off-origin crops do not fall behind the camera or beyond its far plane;
lighting uses the resulting centered bounds.

Example commands (using the portable Blender executable documented above):

```text
blender --background --factory-startup --python scripts/render_canine_review.py -- --output artifacts/shared-anatomy/closeup-default-front-paw.png --region front-paw --modes clay wireframe
blender --background --factory-startup --python scripts/render_canine_review.py -- --output artifacts/shared-anatomy/closeup-contrasting-hock.png --region hind-paw --sample contrasting --pose hock --modes clay
```

The focused crop/camera/deformation suite has ten passing Blender tests,
including default, contrasting and short/wide framing; pose-stable selection;
source-face ownership; and existing Human camera gates. Log:
`artifacts/shared-anatomy/paw-closeup-tests.log`. This diagnostic slice retains
recipe 11 and does not resolve the previously documented extreme elbow contact
limitation. Full core/integration, package and save/reopen suites are not repeated
for these review-only changes.

Local baseline sheets use `closeup-default-front-paw` and
`closeup-default-hind-paw` (clay/wireframe), plus `closeup-contrasting-elbow` and
`closeup-contrasting-hock` (clay). They show broad terminal volumes without
distinct toes or pads; the front sole remains visibly faceted. These views are
a shape baseline, not anatomical acceptance. JSON reports retain full-asset
support metrics and the selected crop indices. Compilation and whitespace checks
pass; the source checkpoint is `4fd30d6` plus these review-tool edits.

## Next work

Next, refine detailed paw anatomy and shoulder/hip attachment creases using
recipe 11 as the baseline. Use the new paw close-ups alongside its whole-body
neutral and joint diagnostics as the before-state for the next geometry change,
rendering comparisons with corrected lighting and the portable Blender 5.2.1
runtime above. Neutral sole contact is complete; planted
support through a gait cycle and contact drift remain open.

Eyes, nose/mouth detail and scapula/pelvis shaping also remain in the canine
quality pass. Compare geometry, rig, weights and clips deliberately against the
baseline and preserve artist-owned edits. After canine visual acceptance, migrate
Avian through the same layer using bird-specific rules, then continue the shared
anatomy/Modify acceptance and cross-provider animation milestones in the alpha plan.
