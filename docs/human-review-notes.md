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
