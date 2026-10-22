# Human review notes

## User and family feedback — 2026-10-11

Recorded after the shared-anatomy integration into main (`76780c7`). These are
reported observations and requested refinements, not completed fixes. The exact
asset parameters and neck pose were not supplied.

- **Glute volume / silhouette:** The user's wife finds the buttocks insufficiently
  voluptuous. Review fullness, roundness and rear projection from side, back and
  three-quarter views. Preserve independent shape controls so fuller glutes do not
  require unwanted changes to waist, hip width or thigh spacing.
- **Feet:** The user's wife finds the feet too flat and long. Review foot length
  relative to the body, instep/arch height, heel volume and toe profile in neutral
  front/side/three-quarter views. Confirm any refinement still supports grounding
  and ankle poses.
- **Neck bend pulls the glutes upward:** The user reports that bending the neck
  lifts/pulls the glute region unexpectedly. Prioritize reproducing this deformation
  issue before silhouette tuning. Compare neutral and isolated neck poses while
  holding the pelvis and lower spine fixed; inspect bone hierarchy, skin weights
  and any pose coupling. The cause is unconfirmed. A localized neck pose should
  not unexpectedly move the glutes; add a regression check once reproduced.

Keep before/after visual evidence and record parameters, pose and commit when
investigating. Preserve artist-owned meshes, weights and actions; use the existing
preview/apply and explicit regeneration workflows.


## Additional paired-pose observation (2026-10-18)

The default generated Human at source `da6f3c5`, before semantic editing, shows
visible torso/hip pulling in the combined diagnostic pose `upper_arm.left` local
Z = 1.05 radians and `forearm.left` local Z = 1.2 radians. Matched evidence is in
`artifacts/shared-anatomy/semantic-deformation/human-combined-before.png` and the
corresponding after image. The broad-shoulder edit is compared with that same posed
baseline; preserved weights do not establish that those baseline weights are good.
Neck-pose reproduction and the root cause remain outstanding. Keep this with the
deferred Human quality review; no base anatomy/weight changes were made here.


## Upper-body weight isolation repair (2026-10-20)

The default 180 cm / 95 kg Human reproduced both reported deformations at
main 7211654. With authored arms excluded, vertices in the neutral 65-125 cm
height band moved up to 5.75484 cm under neck local X = 0.85 radians and
14.97645 cm under upper_arm.left local Z = 1.05 radians (also with forearm.left
local Z = 1.2). A worst neck case carried 16.1% neck weight near the hips;
a worst arm case carried 50.7% upper-arm weight on the lower torso.

The shared solver includes parent/child neighbors of the nearest bone. For the
long torso bone, that neighborhood includes neck and upper arms even far below
their attachments. Human recipe 2 now retains the shared solver and applies a
Human-only smooth taper transferring remote influence to torso. Neck influence
fades over a quarter-torso-height band. Upper-arm influence fades from the torso
midpoint to the lowest authored shoulder-join height, preserving original
upper-arm weights on both sides of that join. Authored arm-chain weights are unchanged;
neutral geometry and rest bones are unchanged. Saved meshes, weights and Actions
are not rewritten. Existing assets need an explicit generated-weight rebuild or
a freshly generated/rigged asset to receive the correction; preserve artist work.

The same diagnostic reports zero lower-body displacement for all three poses
after repair. Blender regressions exercise neck and bilateral combined-arm bends
in both directions on 180 cm / 95 kg and 160 cm / 55 kg bodies, while verifying
that the intended upper-body motion still occurs. Glute volume and foot silhouette
feedback remain open, as do continuous motion and final artistic acceptance.

Local evidence: artifacts/shared-anatomy/human-isolation-before.json,
human-isolation-current.json, diagnose_human_isolation.py and
human-local-weights-review/. The latter uses the existing
scripts/review_semantic_deformation.py --providers human --render helper.

Validation: the three focused Blender deformation tests and all nine Model JSON
acceptance tests pass. The default amount-0.6 semantic pose comparison passes all
four poses, and its rendered combined pose no longer shows the diagonal torso/hip
pull. The full 16-pose Human semantic screen remains FAILED: eight cases already
failed in the previous review, and the same eight fail now. The initial bone-head-based taper worsened two strong-edit shoulder compression
ratios. Using the authored shoulder join instead restores both baseline values
(0.497 default, 0.361 contrasting); the refinement introduces no additional
failing cases in this matrix. The pre-existing strong-edit findings remain open; do not treat this isolated-weight repair as complete Human quality
acceptance or relax the screening thresholds.

The shoulder-join preservation regression compares repaired versus original
upper-arm weights on every torso-side join vertex, and exact authored arm weights.
Final numerical matrix: artifacts/shared-anatomy/human-join-weights-review/report.json.
The broad local core run ended without a completion result and is not a pass;
full CI on the PR remains the broader validation gate.


## Shoulder profile deformation refinement (2026-10-21)

Follow-up to the validated recipe-2 lower-body repair (PR #305). The remaining
semantic screen had eight failures among 16 poses. Two independent mechanisms
were confirmed: distant forearm weights deformed the shoulder collar during an
elbow bend, and a strong localized broad profile compressed neutral surface edges
before posing. Widening the selected shoulder region did not resolve the problem
and is not part of the implementation.

Human recipe 3 retains the shared weight solver and recipe-2 body constraint.
Within authored arms, torso influence fades out by the upper-arm segment midpoint;
forearm influence fades in between the midpoint and distal quarter. Influence
removed from these regions transfers to the upper arm. Hands and lower-body
ownership remain separate, and existing saved weights are never rewritten.

Only shoulders/broad receives a smooth bound on neighboring displacement
differences. The existing transform and selected region remain; its displacement
is scaled by 1/sqrt(1+(maximum_gradient/0.45)^2). For nondegenerate neutral edges
this bounds length to more than 55% and less than 145% of the original. Increasing
amount still increases broadening, with diminishing increments at strong values.
Explicit scale, offset and other profiles are unchanged. This is a geometry
constraint, not a replacement for the unchanged posed-edge acceptance screen.

The production review is reproduced with scripts/review_semantic_deformation.py
--providers human --render --output artifacts/shared-anatomy/human-shoulder-refined-review.
Core tests protect monotonic strength, neutral-edge bounds, unchanged profile
boundaries, shoulder locality and blended elbows. Blender tests exercise all
16 default/contrasting poses at amounts 0.6/1.5 and preserve both earlier hard
and blended shoulder edits: old incompatible edits stay intact and are blocked
from automatic reconstruction. Explicitly rebuild generated weights or use fresh
assets for recipe 3; do not overwrite artist-owned weights or saved shape edits.

Glute fullness, foot silhouette, continuous motion, self-intersection and final
artistic acceptance remain separate work.

Validation completed: 25 focused core tests and 14 focused Blender tests pass.
The production review passes all 16 paired poses with unchanged 0.5-2.0 edge
ratio thresholds; observed ratios span 0.697851 to 1.418240. Both normal-strength
paired renders were inspected. Full CI remains required before merging.

Full-suite follow-up: the initial recipe-3 CI run exposed two stale tests in
tests/blender/test_semantic_deformation.py that required the old Human defect.
Current profiles now use strict screening for all three providers. The rejection
and scene-cleanup regression explicitly reconstructs the old unbounded shoulder
profile, preserving a meaningful negative case without accepting a live defect.

## Independent glute fullness (2026-10-21)

Human Modify now accepts shape target `glutes`, profile `full`, amount 0..1.5
(default 0.65), advertised in the exported Model JSON contract. Two compact
posterior displacement fields increase rear projection without changing X/Z,
waist, anterior tissue, topology, UVs or authored arms. Existing neutral geometry,
recipe identity and saved assets are unchanged. Use the normal preview/apply path;
this does not rewrite artist data or automatically regenerate weights.

Example semantic operation:
`{"operation":"shape","target":"glutes","arguments":{"profile":"full","amount":0.6}}`

Reproduction with Blender background/factory-startup:
- scripts/render_human_review.py -- --glute-fullness 1 --modes clay --output artifacts/shared-anatomy/human-glute-review/neutral-full.png
- Repeat without --glute-fullness for neutral-base.png.
- scripts/review_semantic_deformation.py -- --providers human --human-target glutes --render --output artifacts/shared-anatomy/human-glute-review

The saved report passes all 16 default/contrasting hip poses (amounts 0.6/1.5),
with paired edge ratios 0.698280..1.661431 and unchanged skin weights. Local core
checks cover locality, monotonic strength, topology/UV preservation and relocated
hands. The actual Model JSON operator proof covers preview, cancel, apply and
blocking subsequent artist-edited geometry.

Visual limitation: neutral rear projection increases, but the baseline pelvis
outline remains angular. More importantly, BOTH combined hip/knee images show
severe baseline hip-junction folding (upper_leg.left X=0.95, lower_leg.left
X=-1.2). The relative screen passes because it compares against that already
poor baseline. This is not visual or motion acceptance. Diagnose hip weighting
before further foot polish; foot length/instep/heel and final glute anatomy remain
open. The paired images and report above preserve this evidence.

## Hip-weight continuity repair (2026-10-21)

The prior glute review revealed a baseline rig defect, independently of the new
shape control. The shared nearest-bone solver flips left/right influence at X=0
and enables its torso/thigh bridge inside a hard radius. At the default pelvis,
adjacent vertices only 0.1304 cm apart jumped by 45.1 percentage points of left
thigh weight. Absolute posed/rest hip-edge stretch reached 34.91x across the
180/95 and 160/55 reference bodies.

Human recipe 4 adds a continuous local pelvis weight field after shared weighting:
vertical torso/thigh blending, bilateral midline blending, and smooth transitions
back to the existing weights above the pelvis and below the upper thigh. Authored
arms and distal knee/ankle weights remain intact. The neutral mesh, topology and
rest bones do not change. Existing saved meshes/weights/Actions are not rewritten;
explicitly rebuild generated weights or create a fresh rig to receive the fix.

scripts/review_human_hip_deformation.py measures absolute posed/rest edge ratios,
not just semantic edits relative to an already-deformed baseline. Reproduce with
Blender background/factory-startup --python scripts/review_human_hip_deformation.py
-- --output artifacts/shared-anatomy/hip-after.json. All 12 forward/backward and
combined hip/knee poses on both sides of both bodies are within 0.528802..1.441008.
Maximum left-thigh weight gradient drops from 3.460/5.874 to 0.0822/0.1185 per cm.
The original report is artifacts/shared-anatomy/hip-before.json.

Matched visual evidence: the old human-glute-review/human-combined-before.png
contains sharp folds. The new human-hip-refined-review/human-combined-before.png
shows a continuous hip join. Both directories are under artifacts/shared-anatomy.
In these paired semantic reports, 'before' means before the glute shape edit,
not before the code change. The new combined render has been visually inspected.
Relative glute and shoulder screening remains required alongside the absolute
hip regression. Final continuous motion, collision checks and anatomical approval
are still open; foot silhouette is the next geometry task.

Validation: all 14 focused core tests and 17 Blender deformation/Model JSON
tests pass. The rendered 16-pose glute screen also passes with recipe-4 weights.
Full CI remains the merge gate.

## Foot profile and ankle refinement (2026-10-21)

Human recipe 5 replaces the long thin foot tube with a shorter forefoot, a raised
instep, a fuller heel and separate heel/ball ground-contact stations. One shared
human_foot_profile in geometry/surface_human.py now supplies surface rings and
toe rest landmarks. The established floor datum, body vertices above the feet,
ring counts, topology and bone names remain unchanged. A local vertical ankle
weight blend supports the new shape and preserves knees, body and authored arms.

The first candidate exposed an ankle/instep fold in close-up despite passing the
closed-mesh audit. The final profile has monotonic upper/lower forward contours
and a continuously descending upper surface; a regression protects that seam.
The old distance weights also compressed the revised feet during strong bends.
The final local blend passes all eight left/right ankle cases at X=1.05/-0.6 on
180/95 and 160/55 bodies, with absolute edge ratios 0.632447..1.390993 and no
opposite-foot movement. Neutral heel and ball stations remain on the floor.

Default 180 cm / 95 kg foot bounds: length 20.5587 -> 17.7926 cm (13.45% shorter),
width 9.2565 -> 9.0504 cm, floor 0 cm before and after. Source fingerprints and
measurements are in artifacts/shared-anatomy/human-foot-review/measurements.json.
The local before.png / after.png four-view close-ups were visually inspected.
They are auto-framed diagnostic crops, not pixel-registered overlays.

Reproduce neutral and bent views with Blender background/factory-startup:
--python scripts/render_human_review.py -- --region left-foot --modes clay
--output artifacts/shared-anatomy/human-foot-review/after.png
Add --foot-bend 1.05 for ankle-bend.png. The initial before.png used recipe 4.
The close-up crops the shin for inspection; it does not change asset topology.

Saved recipe-4 geometry and artist data remain intact. Because both surface and
toe landmarks changed, use explicit fresh generation/rebuilding to adopt recipe 5;
do not silently replace an existing mesh or rig. A Blender regression reconstructs
the old feet and proves ownership blocks automatic semantic regeneration.
Detailed toe anatomy, collision-free continuous gait and final artistic approval
remain outside this blockout-foot refinement.

Validation (2026-10-22): 26 focused core tests and all 19 Blender deformation /
Model JSON acceptance tests pass. Full CI remains the merge gate.

## Actual-action motion baseline (2026-10-22)

Foot PR #309 passed all six CI jobs (run 39773820643). Those checks do not
establish continuous motion acceptance. scripts/review_human_motion.py samples
actual Blender Walk/Run actions on fresh recipe-5 assets at 64 intervals per
cycle, with source hashes and loop closure. Reproduce with Blender background:
--python scripts/review_human_motion.py -- --output artifacts/shared-anatomy/human-motion-review/baseline.json

At strength 1, 180/95 Walk reaches -0.1881 cm floor clearance; 160/55 reaches
-0.0908 cm. The lowest of both feet rises to 2.6972 / 2.9366 cm respectively.
Run stays airborne at every sample: minimum clearance 3.0172 / 3.8839 cm,
with the lowest foot rising to 26.1831 / 26.3105 cm. All four loops close exactly.
These in-place clips have no demonstrated ground-contact schedule; Run flight
phases are expected, but an entirely airborne cycle is not accepted locomotion.

Whole-mesh edge ratios expose additional defects beyond the focused pose tests:
Walk 0.1424..2.0959 (180/95), 0.1294..2.3333 (160/55); Run
0.1549..6.8797 and 0.1294..6.7554. Worst compression is at body-owned neck-base
edges 4878/4879 or 4909/4910 (83.6% height). Worst Run stretch is authored
arm.right edge 38941/38942 near the wrist. These are measured diagnoses, not
proof of self-intersection. Source walk.py also alternates knee flexion sign.

Next work: isolate neck-base and distal-arm weight transitions under combined
actions, correct Walk knee direction, then implement and validate grounded Human
locomotion. Do not mask these defects with global floor offsets or weaken screens.
The sampler is diagnostic (exit success means measurement completed); it does
not mark these failing motion results as acceptance. Samples cannot bound peaks
between samples, prove contact slip, or replace visual review.

## Walk knee direction repair (2026-10-22)

The Walk generator previously alternated each lower-leg X rotation between
negative and positive values, bending the knee forward for half the cycle.
Generated Walk now retains backward flexion only, with the right leg half a
cycle out of phase. Hip/arm tracks, timing, peak backward flexion and strength
scaling are unchanged. Existing saved Actions are not rewritten.

Fourteen focused core tests and three Blender action tests pass. The new action
regression samples 65 phases at maximum strength, including between authored
keys, and rejects forward knee rotation on either side. This is a joint-direction
repair, not grounded-locomotion acceptance. Neck/distal-arm deformation and
contact scheduling remain open; no global floor offset or relaxed screen was used.

The 64-interval actual-action audit completed at
artifacts/shared-anatomy/human-motion-review/knee-direction.json. Loop closure
remains exact and whole-mesh edge extrema are unchanged. Walk minimum foot Z
worsens from -0.1881 to -0.7619 cm (180/95), and -0.0908 to -0.3316 cm (160/55).
Maximum lowest-foot height becomes 2.8866 / 3.8286 cm. Run is unchanged.
This contact regression blocks acceptance/merge of the knee-only candidate;
retain it in the draft while coordinating the next grounded gait repair.
