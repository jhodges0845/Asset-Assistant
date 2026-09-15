# Human V2 Topology Plan

Human V2 is a coordinated geometry, deformation, and motion quality pass. It is not a polygon-count increase. The goal is a procedurally generated neutral Human that already reads as recognizably human in Blender solid shading, before semantic/LLM character shaping is applied.

## Quality gate

> A neutral Human with no LLM modifications should already look recognizably human and reasonably smooth in solid viewport shading. Semantic operations should create character identity, not be responsible for creating basic human anatomy.

The model JSON round trip and semantic Modify workflow are working. Human V2 must preserve them: the base constructor creates credible neutral anatomy; Modify creates the particular character the artist wants.

## September 2026 checkpoint

Early Human V2 passes improved torso, limbs, cranium, face support, shoulder transitions, pelvis transitions, weighting, and Human-specific cross-section resolution. Diagnostic clay, silhouette, and wireframe renders then established that generic rounding/refinement had reached its ceiling. The remaining quality problem is topology organization and anatomical construction, not polygon count.

A fresh independent character-topology review reached the same conclusion: pelvis/hip/crotch is the highest-priority structural problem, followed by ribcage/torso mass and shoulder girdle. The Human should be built from anatomical landmarks and masses into deformation-aware continuous topology rather than treating anatomy as tubes attached to a torso.

### Pelvis reconstruction evidence

PRs #274-#282 progressively improved pelvis contour and topology experiments, but the diagnostic renders exposed two failed construction patterns:

- radial/fan connections from the torso into two thigh tubes create stretched triangular surfaces and a weak crotch/glute structure;
- stacked circumferential thigh-opening rows remove the fan but create a shorts/armor appearance rather than a continuous pelvic surface.

Do not continue tuning either pattern. The pelvis must be solved as its own anatomical surface.

PR #283 introduced the new experimental direction: a **standalone, sex-neutral pelvis constructor** that is deliberately not yet integrated into active Human generation. It exposes three intentional open interfaces:

1. upper torso/lower-abdomen boundary;
2. left thigh boundary;
3. right thigh boundary.

The pelvis is generated first. Once its standalone clay, silhouette, and wireframe diagnostics pass, topology can be extended upward into the lower torso and downward into each thigh. This mirrors an artist's grow/extrude workflow and makes the pelvis the central topology hub instead of a bridge between independently generated tubes.

The neutral pelvis must not assume male or female genital anatomy. Sex/body-shape characteristics belong in later semantic shaping. The base surface should provide a neutral pubic/crotch transition and enough topology for controlled variation.

### Modify compatibility is a construction requirement

The anatomy-oriented constructor must remain semantically controllable. PR #283 establishes independent controls for pelvis width/depth/height, waist dimensions, hip fullness, glute projection, crotch width/depth/drop, thigh-opening dimensions, and thigh spacing.

These controls are intentionally anatomical/shape concepts rather than sex labels. Changes such as wider hips, narrower crotch, reduced glute projection, or closer thigh spacing must remain possible without replacing the topology strategy. Do not couple independent controls merely to make a visual test pass.

The existing Modify UI, semantic operations, JSON export/import, preview/apply workflow, and artist ownership model remain core product behavior. Human V2 construction must support them rather than bypass them.

## Current implementation sequence

### 1. Standalone pelvis — active

- Generate the pelvis independently from torso and thighs.
- Preserve exactly three intentional attachment boundaries.
- Keep the medial crotch/inner-thigh origin close to centerline; carry most width through the outer hip/trochanter region.
- Favor structured, quad-dominant anatomical flow; triangulation can happen downstream when required.
- Keep bilateral symmetry and deterministic generation for the neutral base.
- Use topology tests for structural integrity and renders for anatomy quality.
- Review front, 3/4, side, and back in clay, silhouette, and wireframe using `scripts/render_pelvis_review.py`.
- Do not integrate the prototype into active Human generation until the standalone visual gate passes.

### 2. Extend pelvis into lower torso

After standalone pelvis approval, grow topology upward from the upper boundary into abdomen/waist/ribcage. Establish ribcage and abdominal mass rather than another tapered box.

### 3. Extend pelvis into thighs

Grow each thigh downward from its pelvis boundary. Preserve useful outer-hip, glute, front, and medial longitudinal flow rather than introducing circumferential conversion belts.

### 4. Ribcage and shoulder girdle

Treat torso mass and shoulders together. Establish ribcage volume, clavicle/deltoid/armpit flow, and a natural neck/shoulder transition.

### 5. Remaining anatomy

Continue with anatomical limbs and joints, feet before hands, then skull/face feature topology. Add geometry where it supports anatomy or deformation rather than generic subdivision.

### 6. Deformation and locomotion

Once the neutral topology gate is materially passed, revisit pelvis/spine/clavicle articulation and topology-aware weighting based on deformation evidence. Locomotion should progress toward contact/down/passing/up phases, center-of-mass transfer, pelvis motion, heel/toe behavior, and spine/clavicle contribution.

### 7. Character quality checkpoint

Do not repeat the Maxine JSON round trip yet. Repeat it after the neutral constructor has materially advanced through pelvis integration and torso/shoulder anatomy (and again after later face/hand/foot milestones). The goal is to confirm that semantic shaping creates character identity without exposing topology artifacts.

## Structural acceptance checks

For standalone pelvis work, automated tests should protect structural integrity without overfitting the visual solution:

- deterministic output;
- exact bilateral symmetry for the neutral default;
- exactly three intended open boundary loops;
- internal manifold edge incidence and boundary edge incidence;
- orientability and consistent face winding;
- no degenerate/zero-area faces;
- stable semantic controls and independent Modify dimensions.

The renders remain the anatomy quality gate. A mathematically valid surface can still be visually wrong.

## Architecture guardrail

Architecture remains frozen unless Human V2 exposes a concrete boundary problem. Anatomy work belongs in host-independent `object_core` geometry; Blender is used only for adapter behavior and diagnostic rendering.

For every major Human V2 change ask:

> Did we make Asset Assistant better without making it harder to maintain?

Flag a change before merge if it requires Blender imports inside core/providers, anatomy-specific logic in shared workflow infrastructure, hidden presentation callback replacement, silent ownership transfer, validation bypass, or a second workflow implementation inside a fastpath.
