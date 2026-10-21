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
Human-only smooth taper over the quarter-torso-height band below each attachment,
transferring removed influence to torso. Authored arm-chain weights are unchanged;
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
failed in the previous review, and the same eight fail now. At amount 1.5, the
minimum edited/baseline edge ratio in the shoulder pose worsens from 0.497 to 0.391
(default) and 0.361 to 0.248 (contrasting). These strong-edit compression findings
remain open; do not treat this isolated-weight repair as complete Human quality
acceptance or relax the screening thresholds.
