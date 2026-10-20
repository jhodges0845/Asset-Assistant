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
