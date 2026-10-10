# Shared anatomy implementation checkpoint

Current implementation: October 5, 2026, recipe version 14 on
`codex/shared-generation-system`. Human and Quadruped use shared resolved-anatomy
contracts. The stylized canine anatomy finishing pass adds facial relief,
matching four-toe paws, shallow pad/claw forms and fuller limb/pelvis profiles.
Avian still uses its existing construction and awaits recipe migration.
This is a development checkpoint; final motion acceptance remains open.

## Current behavior

The canine generates one connected surface with 17,218 vertices, 17,216 quads
and the existing 17-bone rest rig. It has a tucked waist, fuller chest/pelvis,
connected ears, a distinct muzzle, and separate hip/knee/hock/paw hind chains.
Local facial subdivision adds eye/eyelid, closed-mouth and nostril relief on
the authored head surface. These are sculpted features, not a facial rig or
separate eyeballs. Ear boundary loops propagate through local subdivision.

Both front and hind paws now have a short recipe-owned toe section, matching
four-toe contours and local terminal refinement. Shallow connected claw tips
and underside pad borders remain limb-owned. Front projection and distal depth
are bounded to preserve isolated elbow clearance and avoid folds at parameter
corners. The hind grounding map ends lower on the pastern to retain paw volume.
The exact neutral ground points remain at zero; pad borders only lift nearby
underside vertices. Paw expansion uses the low sole center instead of an
oblique rest-joint projection. Upper-leg taper and fuller rear body sections
soften the shoulder/hip transitions without changing rest bones or weights'
authored-chain ownership.

Shape/scale Modify executes for body, torso, chest, waist, head, muzzle, tail,
both ears and all four limbs. Head edits carry facial detail and ears; muzzle
edits stay in their region. Coat/accessory operations are not executable canine
geometry capabilities. Existing ownership, preview/apply and topology guards
remain in force. Saved recipe-13 and earlier surfaces require explicit creation
of a new Quadruped to adopt this topology; no automatic geometry, weights or
Action migration occurs.

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
| `providers/quadruped_refinement.py` | Global and local subdivision; propagates regions and ordered loops. Limb boundaries remain 16/32; locally refined ear boundaries are 64/32. |
| `providers/quadruped_detail.py` | Construction-only connected facial and paw relief; retains authored region ownership. |
| `providers/quadruped_rigging.py` | Rest chains, authored limb/ear ownership, attachment bridges and interior collar fades. |
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
to adopt version 14; there is no automatic topology, weight or Action migration.
Manual artist edits continue to block procedural replacement. Installing the
updated add-on alone does not upgrade existing geometry or artist-owned weights.

## Validation and reproducibility

Recipe-12 validation checkpoint (September 28, 2026): all 411 core tests and 243 Blender
integration tests pass, along with real canine save/reopen, the rebuilt isolated
package, compilation and whitespace checks. This is the recipe 12 working tree
plus the attachment collar fade described below; see `collar-*` artifacts for
this slice and `paw-cap-*` for the preceding topology checkpoint. Remote CI and
gait playback are not established by these local results.

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

Implementation commit: `b3b130f`, pushed to `codex/shared-generation-system`.

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

## Paw quad caps (recipe version 12)

Each paw now closes with four cage quads around a regular four-edge center,
replacing the single octagonal cap that refined into an eight-edge radial pole.
The original boundary ring is retained. The new center is explicitly owned by
its limb, and subdivision propagates that ownership through the cap. Body,
attachment rings, landmarks and the 17-bone rig are unchanged. This is a local
paw topology migration: old surfaces require explicit replacement, and artist
edits are not silently rebased onto new connectivity.

The fuller front cap uses a validated `front_forward_scale=.25` on the existing
`min(body_width * .02, shoulder_height * .03)` cm projection. Hind projection
is unchanged; both retain the existing 1.20 width and 1.65 length scales.
This balance preserves forward hind support and the established elbow
clearance gate. Grounding still runs through the existing construction path;
there is no pose-specific correction or alternate geometry implementation.
The cap is a better surface foundation for toe/pad work, not separated digits
or completed paw anatomy.

The new regression checks four cap quads, center position and valence, and
limb ownership after refinement. Existing parameter-corner coverage now treats
the cap center separately from the tube rings, preserving full front/hind ring
orientation, manifold, symmetry, ground-contact and Modify checks.

The final six-sample comparison (`toe-before.json` to `paw-cap-baseline.json`)
changes only Quadruped mesh and weight fingerprints. Human, Avian, every rest
rig and every clip match. Quadruped grows from 6,274 vertices / 6,272 faces to
6,402 / 6,400: 128 additional vertices and quads across the four paws. Evidence
is captured at `b3b130f` plus working-tree edits. The earlier `toe-*` contour
renders are rejected experiments and are not the accepted recipe 12 surface;
use the final `paw-cap-*` reports and renders.

The final 18-case neutral/joint matrix passes movement and isolation checks.
Default/contrasting moving paws retain positive diagnostic clearance; the
contrasting elbow has 0.0349 cm. The short/wide elbow remains 0.0402 cm below
ground, improved from recipe 11's 0.1361 cm penetration. This is still an open
pose-contact limitation, not a gait acceptance result. Default front/hind
clay/wireframe close-ups, contrasting elbow/hock clay, and default whole-body
clay were rendered and visually inspected. The front cap no longer has the
previous radial pinch; individual toes and pads remain future work.

Final validation: all 409 core tests and 243 Blender integration tests pass on
the front-only projection profile. Canine save/reopen, a rebuilt isolated add-on
package, compilation and whitespace checks pass. Logs and final renders use
`paw-cap-*` under `artifacts/shared-anatomy/`. Remote CI and gait playback were
not repeated. This remains a limited paw-surface checkpoint, not final canine
visual acceptance.

## Attachment collar fade (September 28, 2026)

The body-to-limb bridge already retained 25% parent influence at the limb loop,
but the next interior row dropped directly to chain-only weights. A short collar
now fades parent influence across the next three refined edge rows: 21.09375%,
12.5% and 3.90625%, reaching zero at the fourth edge with the default four-bone
limit. In parallel it blends from the boundary's upper-bone weighting into the
existing distance-based chain weights. Lower influence limits truncate and
renormalize as before; they do not retain those exact parent percentages.

The collar traverses authored limb topology, so it stays local after Modify
translations. Body/bridge rows and vertices four or more edges inside the limb
keep their previous weights. Meshes, UVs, rest rigs, clips and recipe version 12
are unchanged by this weighting slice. Saved artist-owned weights remain intact;
new weights enter through the existing explicit generation/rig/Modify workflow.

Independent graph-distance regressions check the parent fade and exact distal
weights for default/contrasting samples, plus normalization, influence limits,
determinism and large Modify translations. Evidence uses `collar-*` in
`artifacts/shared-anatomy/`. The six-sample `collar-before.json` to
`collar-after.json` comparison changes only Quadruped weights; all mesh, rest-rig
and clip fingerprints, and all Human/Avian output, match the pre-change recipe
12 working tree. Default/contrasting shoulder and hip clay/wireframe sheets were
inspected. All four poses retain zero other-limb and torso/head/tail displacement.
The visible attachment crease remains, so this is a weight-continuity improvement,
not final anatomical/gait acceptance. The rebuilt isolated package and real
canine save/reopen checks pass in Blender 5.2.1. All 411 core tests and 243
Blender integration tests pass, as do compilation and whitespace checks.

## Front-paw toe contours (recipe version 13, October 3, 2026)

The two terminal front-paw cage rings and their four-quad caps receive a local
linear split before the existing two subdivision passes. Shared edge midpoints
also enter adjacent polygons, so the normal refinement produces a closed quad
surface with no hanging seam vertices. Added vertices stay limb-owned; attachment
loops are unchanged. This grows the mesh by 1,216 vertices and quads to
7,618 / 7,616. Older generated surfaces require explicit replacement; construction
does not rebase saved artist edits or apply the contour during Modify.

A validated `front_toe_indent_scale=.18` retracts three narrow bands on the front
half of each low front paw, suggesting four toes in the connected surface.
The map preserves X/Z coordinates, fades out below the ankle, and keeps forward
ordering (its Y derivative remains positive throughout the allowed 0..0.2 depth
range). Neutral sole grounding still uses the canonical construction path.
This is stylized surface detail, not separated digits, pads, claws or dewclaws.
The four-toe direction follows the primary toe/pad arrangement described by
[University of Illinois Extension](https://web.extension.illinois.edu/dogs/parts.cfm?slide=15).

Initial sparse-cage contours looked like faceted dimples. Refining all four paws
made the hind soles look too flat, so that draft was rejected. Only front paws
receive this change. The accepted evidence uses `front-toes-*` under
`artifacts/shared-anatomy/`; `toe-contour-*` files are intermediate experiments.
The front contour is clearer in close-up and whole-body views but remains
faceted, with a visible upper toe lip. Hind shape and the attachment creases
still require anatomical refinement.

Portable regressions cover closed local splits, ownership/seam preservation,
contour locality, exact height preservation, depth validation, and supported
parameter corners. The symmetry check compares coordinates with an explicit
1e-7 cm tolerance rather than requiring identical decimal rounding bins.

The six-sample comparison from `toe-contour-before.json` (clean `52a1f66`) to
`front-toes-baseline.json` changes only Quadruped mesh and weight fingerprints.
Human, Avian, all rest rigs and all clips match. The 18-case neutral/joint matrix
passes movement and isolation checks. All neutral soles remain grounded.
Default, contrasting and short/wide elbow clearances are 0.8723, 0.1091 and
0.0572 cm respectively. This removes the prior short/wide elbow penetration in
that isolated pose; it is not a planted-foot or gait-cycle acceptance result.
The Blender elbow/hip regression now also includes that short/wide sample.

All 414 core tests and 243 Blender integration tests pass. Default front/hind
clay/wireframe, contrasting elbow/hock clay, and default whole-body clay sheets
were rendered and inspected. The rebuilt isolated package and canine save/reopen
checks pass in Blender 5.2.1. Compilation and whitespace checks pass. Remote CI
and gait playback were not repeated.

## Sampled walk/run contact baseline (October 3, 2026)

`scripts/review_canine_gait.py` generates actual editable Blender walk/run actions
through the normal adapter, evaluates their deformed surfaces in world centimeters,
and records 33 evenly spaced cycle samples including both endpoints. It creates
and removes its own scene and generated data, preserving the caller's scene/frame.
The report includes per-frame signed clearance and near-ground hulls, the worst
sample phase, loop closure, and a fixed neutral sole patch's centroid trajectory.
Centroid XY excursion is the largest separation over the cycle, not inferred foot
sliding: these clips are in-place and no stance schedule or root travel is assumed.
Sampling can miss between-sample peaks. Hulls remain envelopes, not contact area.

Reproduce each row in Blender 5.2.1 with:

```text
blender --background --factory-startup --python-exit-code 1 --python scripts/review_canine_gait.py -- --sample default --output artifacts/shared-anatomy/gait-default.json
```

Use `--sample contrasting` or `--sample short-wide` and a matching output name for
the other shapes. `--intervals 32` is the default; 4..256 intervals are supported.
The CLI uses strength 1, a 1.2-second walk and a 0.64-second run at 24 fps; fractional
frames retain exact normalized sample phases. JSON includes source provenance,
parameters, recipe, runtime, and the fixed sole vertex indices.

| Shape | Clip | Worst sampled penetration (cm) | Limb | Phase |
| --- | --- | ---: | --- | ---: |
| Default | Walk | 1.6194 | Hind right | 0.28125 |
| Default | Run | 5.4796 | Front right | 0.31250 |
| Contrasting | Walk | 2.0399 | Hind right | 0.28125 |
| Contrasting | Run | 7.5214 | Front right | 0.28125 |
| Short/wide | Walk | 0.5609 | Hind left | 0.78125 |
| Short/wide | Run | 2.0425 | Front right | 0.31250 |

All six cycles close exactly in evaluated vertex positions at their endpoints,
but all penetrate the fixed ground plane between them. This establishes a gait
contact defect despite the passing isolated elbow/hip checks; it is not gait
acceptance. The diagnostic change does not alter generated geometry, weights,
rigs or clips. Keep `front-toes-baseline.json` as their fingerprint baseline.
Local reports use `gait-default.json`, `gait-contrasting.json` and
`gait-short-wide.json` under `artifacts/shared-anatomy/`.

Blender regressions exercise real walk/run movement, fractional endpoint timing,
closed cycles, report consistency and caller-data preservation on success,
invalid input and an injected measurement failure. All 245 Blender integration
tests pass in Blender 5.2.1, including the two new gait-review tests. Compilation
and whitespace checks pass. Core/provider code is unchanged from `27dfb74`,
whose 414 core tests passed at the recipe checkpoint.

## Portable contact trajectory foundation (October 3, 2026)

`object_core/animation/contact.py` now defines an immutable `ContactCycle` and
`ContactTarget` for the next gait solver. Each foot declares duration, reference
root travel per cycle (cm), stance duty factor, swing height (cm), and touchdown
phase. Forward is a scalar axis selected by the caller; it is not implicitly a
Blender bone axis. Targets are offsets from a neutral contact point.

Stance moves backward at constant reference speed `stride_cm / duration` with
zero lift. Adding the corresponding forward root travel produces a stationary
reference contact. Swing returns through a cubic Hermite curve with matching
endpoint velocities and a quartic lift with zero endpoint velocity. Small
fore/aft overshoot during swing is intentional. Position and velocity are
continuous; acceleration continuity is not promised. Phase wraps over repeated
cycles, including negative phases. Stance includes touchdown and excludes
liftoff. Stride means full-cycle root travel, not stance excursion.

Six portable tests independently check stationary stance under reference travel,
nonnegative lift and the declared apex, numerical position/velocity continuity,
phase offsets and loop wrapping, duration scaling, and invalid input. This is
an executable target contract, not a joint solver or gait acceptance result.
At this foundation checkpoint no provider consumed it; meshes, rigs, weights
and clips were unchanged. The integration checkpoint below supersedes that state.
All 420 core tests pass on Python 3.9; compilation and whitespace checks pass.
The focused tests exercise every executable line in the new module under the
standard-library trace tool. Full coverage.py reporting was unavailable locally.
Evidence: `artifacts/shared-anatomy/contact-core-tests.log` and
`contact-coverage/`. Blender and remote CI were not repeated for this portable,
unconnected foundation.

The integration below supplies canine footfall/duty-factor and travel values,
solves joint channels against generated proportions, and validates the deformed
sole with the Blender gait review. Its stance labels describe the new clips,
not the earlier sinusoidal baseline.

## Contact-driven walk/run integration (October 3, 2026)

`providers/quadruped_gait.py` now consumes the portable contact targets through
normal Quadruped Walk/Run generation. The provider accepts optional saved
parameter values; omitting them retains the public default-proportion call.
The Blender adapter passes the asset's saved values through the generic
`animation_uses_parameters` seam. Human and Avian remain on their existing path.

The solver uses recipe 13's canonical geometry, region membership, rest bones
and weights. In each limb's YZ plane it solves upper/lower rotations for both
the fixed neutral sole patch's forward centroid and the minimum height of every
authored limb vertex under linear-blend skinning. Hind pastern rotation cancels
the accumulated upper/lower rotation. A constant root crouch of
`0.07 * shoulder_height_cm * strength` provides front-leg reach. No evaluated
vertices are clamped, no mesh or weights are rewritten, and the 17-bone rest rig
is unchanged. The solver rejects a target when it cannot converge within its
bounded iterations/rotation range, rather than silently clipping the target.

Walk uses touchdown phases front-left 0, hind-right .25, front-right .5 and
hind-left .75, with stance duty .65. Run is a diagonal running trot: front-left
and hind-right at 0, the other diagonal at .5, with duty .4 and flight intervals.
Reference stride per cycle is shoulder height times strength times .20 (Walk)
or .30 (Run). Swing lift uses .06 or .10 respectively. Forward is +Y, and
reference speed is stride/duration. These are deliberate stylized starting
values, not species-wide biomechanical claims or generated root travel.

Each limb has 128 joint intervals per cycle and a 0.02 cm contact margin.
Quaternions and the root-height translation become ordinary editable curves
through the existing action lifecycle. Idle explicitly keys zero root height so
native/clip-list switching cannot retain a gait crouch. Neck/tail follow-through
remains; spine oscillation is omitted while contact is solved against a steady
body. Existing actions are preserved and are not automatically replaced.
The bounded cache includes recipe identity/version, parameters, duration,
strength and gait. Cold generation is several seconds per clip; the fingerprint
report records timings. This is a material cost versus the old angle waves.

The schema-2 gait review records declared stance, reference travel, forward and
clearance target errors, and stance-centroid drift after reference +Y travel.
It joins stance samples across the cycle seam. This tracks a fixed material
patch centroid, not zero velocity at every sole vertex, physical contact area,
or arbitrary artist-modified surfaces/weights. Contact guarantees here apply
to the tested canonical generated assets. Strength/curve editing can change
contact and needs a fresh review. Samples cannot bound every between-sample peak.

Final 127-interval reports (all six have exactly zero evaluated loop error):

| Shape | Clip | Minimum clearance (cm) | Maximum reference stance drift (cm) |
| --- | --- | ---: | ---: |
| Default | Walk | 0.01997 | 0.001565 |
| Default | Run | 0.01994 | 0.000026 |
| Contrasting | Walk | 0.01997 | 0.001137 |
| Contrasting | Run | 0.01995 | 0.000018 |
| Short/wide | Walk | 0.01999 | 0.000427 |
| Short/wide | Run | 0.01998 | 0.000009 |

The largest sampled forward target error is 0.00401 cm and clearance target
error 0.00612 cm. Interior review phases fall between the 128 animation key intervals. Evidence is
`artifacts/shared-anatomy/gait-contact-{default,contrasting,short-wide}.json`.
Reproduce with the earlier gait CLI plus `--intervals 127`. The new
`render_canine_review.py --gait walk|run --phase 0..1` options render actual
editable actions; the `contact-run-default.png` and
`contact-walk-contrasting.png` clay sheets inspect the former worst-contact
phases from front/side/angled views. Bends remain connected and readable;
attachment creases and faceted paws remain. This is not final animation acceptance.

The six-sample `gait-contact-baseline.json` comparison against
`front-toes-baseline.json` retains every mesh, rest-rig and weight fingerprint,
and all Human/Avian output. Quadruped clips change, including an explicit zero
root translation in Idle. The 18-case generation matrix covers default,
contrasting and short/wide shapes at strengths .1, 1 and 2. Additional
length/height/width corner checks exposed an overly restrictive solve limit for
tall short bodies at run strength 2; the corrected limit and focused regression
cover that case without changing ordinary gait targets.

Validation: all 425 core tests and 246 Blender integration tests pass. After
the explicit Idle-height reset was added, the 30 portable animation tests were
repeated and passed; the 246-test Blender run includes that final change and
the new centimeter-unit/clip-list-switch regression. Real canine save/reopen,
the rebuilt isolated add-on package, compilation and whitespace checks pass.
Logs use `contact-final-*` under `artifacts/shared-anatomy/`. Remote CI and
destination playback were not repeated. The two inspected pose sheets are not
a three-cycle animation-quality review.

## Anatomy finishing checkpoint (October 5, 2026)

Recipe 14 retains the same public provider, semantic targets and 17-bone rig.
It intentionally changes geometry, topology, weights and contact-solved joint
curves. New facial features are part of the connected surface; claws and pads
are restrained relief suitable for this stylized reference. They are not
individually articulated digits. Fur, facial performance and breed coverage
remain deferred.

Review evidence uses `anatomy14-final-*` in `artifacts/shared-anatomy/`:
default/contrasting neutral clay, silhouette and wireframe; head and both paw
close-ups; shoulder, hip, knee and hock bends. Open paw/head crop boundaries are
diagnostic selections, not openings in the complete generated surface.
Resumed verification confirms that all six current provider fingerprints match
`anatomy14-baseline.json`. The corrected final core run (`anatomy14-accepted-core.log`)
passes all 427 tests; `anatomy14-verified-blender.log` passes all 246 Blender tests.
Earlier `final`/`verified-core` logs contain rejected drafts and are not the final
result. The corrected paw-profile test isolates horizontal expansion from pad
relief instead of attributing their combined clipped footprint to one map.
The isolated package and real canine save/reopen checks pass in Blender 5.2.1.

The surface now has 17,218 vertices and 17,216 quads. Compared with the contact
recipe 13 baseline, only Quadruped mesh, weights and clips change; its rest rig
and all Human/Avian fingerprints match. Local facial resolution, the extra toe
segment and both-paw detail require explicit regeneration of older assets.
The close-ups still show faceting and shallow relief; this checkpoint is not
final motion/visual acceptance.

Recipe 14 contact reports use 127 intervals, between the 128 animation key
intervals. All six cycles retain positive minimum clearance (0.01993..0.01999 cm),
zero evaluated loop error, and maximum reference stance-centroid drift below
0.00156 cm. Evidence is `anatomy14-contact-{default,contrasting,short-wide}.json`.
The previous recipe 13 contact limits still apply; this is sampled canonical
asset validation, not arbitrary edited-surface or continuous-time proof.

## Fractional GLB clip endpoints (October 7, 2026)

The destination round-trip probe found that integer-frame NLA baking truncated
fractional contact clips: at 24 fps, Walk ended at frame 29 instead of 29.8 and
Run at 16 instead of 16.36. The source actions remained closed, but their exported
files lost the precise endpoints. This was an export-timing defect, separate
from the already-correct native-Blender contact solver.

`blender_adapter/targets.py` now exports unconstrained generated clip libraries
from authored keys using their temporary single-strip NLA associations. Explicit
track-name merging preserves user export names, and single-armature broadcasting
is disabled so unassociated actions cannot leak into the file. Saved actions and
artist NLA/driver ownership retain their existing preservation boundaries.
Allowed constrained/driven exports retain evaluated baking; existing rig-driver
and artist-NLA preparation guards still apply. The fractional timing result
below applies to the authored-key path on the tested Blender 5.2.1 runtime.

The real GLB regression exports Idle, Walk and Run together, including a renamed
Walk, plus an unrelated action that must be excluded. Reimported Walk/Run retain
1.2/.64-second durations, positive sampled clearance and loop closure within
0.001 cm. The source active action is restored and temporary tracks are removed.
The measurement excludes importer-created bone-display helper meshes and uses
only the mesh skinned to the imported armature.

Final 127-interval default-shape round trips retain minimum clearance of
0.01997 cm (Walk) and 0.01994 cm (Run). The largest difference from the source
minimum-height trace is below 0.000017 cm. Evidence uses
`anatomy14-glb-final.json` and `anatomy14-glb-test.log` under
`artifacts/shared-anatomy/`. This is a Blender
GLB round trip, not a Godot/Unity runtime playback sign-off. FBX and constrained
clip timing remain outside this verification.

Validation: all 247 Blender integration tests pass after the export fix. The
rebuilt isolated package and all five portable export-contract tests also pass,
as do compilation and whitespace checks. Logs use `anatomy14-resume-*` and
`anatomy14-export-core.log`. The confirmed 427-test anatomy core result above
remains applicable; this continuation changes only export behavior, its regression
and checkpoint documentation.

## Vertical body response (October 9, 2026)

Walk now adds a small compression pulse between footfalls; the diagonal Run
compresses mid-stance and rises during flight. Root translation and solved limb
rotations share 128 intervals and an exact closing key. Each solve includes the
current root height, preserving the sole contact target while the body moves.
The additional vertical range is 0.006 times shoulder height for Walk and 0.014
for Run, scaled by strength (0.33/0.77 cm at the default 55 cm height and strength
1). This is authored stylized response, not a dynamics simulation. There is no
horizontal root travel; the declared reference-travel contract remains in use.

All 428 core tests and 247 Blender integration tests pass, including the GLB
round-trip regression. The rebuilt isolated add-on package, compilation and
whitespace checks also pass (`body-response-package.log`). Fresh provider
fingerprints change only Quadruped clips;
all meshes, rest rigs, weights and Human/Avian results match the prior checkpoint.
The six default/contrasting/short-wide contact reports at 127 intervals retain
minimum clearance above 0.01991 cm, maximum reference stance-centroid drift below
0.00157 cm and maximum clearance-target error below 0.00612 cm. These remain
sampled canonical-asset checks. Evidence is `body-response-core.log`,
`body-response-blender.log`, `body-response-baseline.json` and
`body-response-{default,contrasting,short-wide}.json` in `artifacts/shared-anatomy/`.

`scripts/create_canine_motion_review.py` saves real editable rig/action scenes
and optionally renders three cycles from front, side, three-quarter and back
views. At 25 fps, both canonical durations have exact whole-frame periods.
For example:

```sh
blender --background --factory-startup --python-exit-code 1 --python scripts/create_canine_motion_review.py -- --gait run --output artifacts/shared-anatomy/body-response-run.blend --render
```

Use `--gait walk --sample contrasting` for the contrasting walk review. Default
Run and contrasting Walk MP4s and scenes were generated. Representative Run
frames 1, 4 and 8 were inspected; faceting and attachment creases remain visible.
This does not constitute a complete video review or final visual acceptance.

## Hind-paw swing curl (October 9, 2026)

The third hind-limb joint now adds a restrained swing pitch (0.12 radians at
strength 1), with zero pitch and zero slope at liftoff and touchdown. Stance
retains the existing level-paw orientation. The weighted-surface solver includes
this pitch when solving the two upstream joints, so forward position and the
lowest surface point remain the contact targets. The existing 17-bone rig,
geometry and front-limb motion are unchanged. This is swing articulation;
stance toe-off and independent forepaw roll remain unfinished.

Seven focused core gait tests and three Blender animation/GLB regressions pass.
The new regression requires both hind chains, checks nonzero swing articulation
and verifies level stance. Existing maximum-strength and branch-continuity tests
also pass. A three-cycle Run scene/video is saved as `paw-curl-run.blend/.mp4` in
`artifacts/shared-anatomy/`; rendering is not final visual acceptance. Test logs
use `paw-curl-core.log` and `paw-curl-blender.log`. The previous full-suite results
belong to the preceding body-response checkpoint; this slice uses focused tests.

All six 127-interval Walk/Run sweeps across default, contrasting and short-wide
shapes retain positive minimum clearance (above 0.01991 cm), zero evaluated loop
error and reference stance-centroid drift below 0.00157 cm. Maximum clearance
error remains below 0.00612 cm. Reports are `paw-curl-{sample}.json`. Run frame 8
was visually inspected; no obvious limb separation was observed, but complete
animation review remains open. Compilation and whitespace checks pass.

## Material-point stance diagnostics

Before stance toe-off tuning, gait report schema 3 adds
`maximum_reference_vertex_displacement_cm`: the largest XY displacement of any
fixed neutral sole vertex from that vertex's first sampled stance position,
after applying declared reference +Y travel. This supplements the existing
centroid diameter metric; opposing vertex motion cannot cancel out. The sample
count is recorded separately, and fewer than two stance samples produce null,
not an unsupported zero. Wrapped stance intervals retain vertex identity.

The metric includes all neutral sole vertices even when lifted. It measures
material-patch motion, not actual contact slip or a toe pivot. In particular,
centroid drift and per-vertex displacement use different reference definitions;
they are complementary diagnostics rather than interchangeable thresholds.
Generated motion, geometry and rigging are unchanged in this checkpoint.

Ten portable metric tests pass, including opposing slip hidden by a fixed
centroid, a wrapped stationary stance, invalid input and insufficient samples.
Two Blender review regressions also pass, covering report fields, caller scene
preservation and failure cleanup. Compilation and whitespace checks pass.

The default 127-interval Blender sweep records maximum per-vertex displacement
of 0.02743 cm (front) / 0.22378 cm (hind) for Walk, and 0.03458 / 0.19254 cm for
Run. Walk hind-centroid drift stays below 0.00005 cm despite that material
motion. Evidence: `material-contact-default.json` and
`material-contact-tests.log` in `artifacts/shared-anatomy/`. These values are a
baseline, not acceptance thresholds or proof of actual ground slip. Before
adding toe-off, identify the planted toe patch and measure its motion separately
from lifted sole points; do not treat the old centroid limit as sufficient.

## Next work

Complete the motion pass: lateral weight shift, stance toe-off and forepaw articulation, then inspect
at least three cycles from front/side/three-quarter views and verify destination
playback. Preserve the declared stance/travel contract and sampled contact/drift
checks while tuning. Use the new material-point baseline when choosing toe-off
pivots; a stable sole centroid alone does not establish planted toes. Arbitrary edited shapes/weights and dense-time contact
remain outside the canonical generated-asset checkpoint.

After the canine motion/visual sign-off, migrate Avian through the shared layer
using bird-specific rules, then complete cross-provider Modify acceptance and
release hardening in the alpha plan. Do not reopen canine anatomy for additional
species, fur or facial animation unless a concrete release blocker requires it.
