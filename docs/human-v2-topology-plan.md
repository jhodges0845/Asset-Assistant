# Human V2 Topology Plan

Human V2 is a coordinated geometry, deformation, and motion quality pass. It is not a polygon-count increase. The goal is a procedurally generated neutral Human that already reads as recognizably human in Blender solid shading, before semantic/LLM character shaping is applied.

## Visual checkpoints — September 2026

### Maxine round-trip checkpoint

A fresh neutral Human and a Maxine model-change round trip were compared after the torso support, facial support, neutral facial-anatomy, and soft-joint-weighting work.

The round trip is functioning: Maxine's parameter and semantic changes materially alter height/weight/body type, shoulder width, torso/waist proportions, limb proportions, head/face, jaw, and cheeks. The limiting factor is now the base mesh. The low-resolution ring/branch surface turns a neutral mannequin into a differently proportioned mannequin, and stronger face operations can exaggerate angular planes rather than produce convincing anatomy.

### Neutral Human checkpoint after cross-section refinement

A fresh neutral Human was inspected from front, 3/4, profile, and back after torso (#257), limb (#258), and cranium (#259) cross-section refinement.

Those refinements improved the global silhouette and proved that Human-specific post-process refinement can add useful resolution without disturbing the shared primitive or architecture. They also established the ceiling of simply rounding the existing eight-sided mannequin: the neutral result still reads as a procedural mannequin rather than a credible generic human.

The next bottleneck is anatomical structure, not generic subdivision. In priority order:

1. shoulder/chest/pelvis anatomy — replace hard shoulder corners, box-like ribcage/waist transitions, and rectangular pelvis-to-leg transitions with intentional neutral anatomy;
2. true facial feature topology — establish useful eye/eyelid, nose, mouth/lip, cheek, jaw/chin structure rather than adding more subdivision to the current facial surface;
3. hands and feet — replace tapered/capped placeholder forms after the major body and face read correctly.

Do not spend additional passes merely rounding the current eight-sided surface. Future geometry work should introduce anatomically intentional structure and edge placement.

This is the Human V2 quality gate:

> A neutral Human with no LLM modifications should already look recognizably human and reasonably smooth in solid viewport shading. Semantic operations should create character identity, not be responsible for creating basic human anatomy.

Accordingly, intentional base-mesh topology remains the highest Human V2 priority. Additional semantic-profile tuning, rig expansion, locomotion work, and final UI polish remain behind this gate unless a concrete blocker requires otherwise.

## Phase 1 — topology/anatomy foundation

### Completed foundation

- Added intentional support topology around pelvis/hip transitions and shoulder/armpit transitions.
- Added deterministic head-local facial support topology without breaking manifold connectivity.
- Added neutral facial depth for jaw, mouth/lips, nose, cheeks, eye sockets, and brow.
- Added Human-specific torso, limb-shaft, and cranium cross-section refinement while preserving shared `RING_SIDES` and branch seams.
- Preserved deterministic generation, one connected editable body, UV coverage, semantic editability, and export behavior.

### Current priority — anatomical torso, shoulders, and pelvis

Move beyond generic ring rounding and introduce intentional neutral anatomy while preserving the existing provider/core architecture and deterministic generation.

- Shoulder/chest: soften the hard shoulder corner, establish deltoid/upper-chest transition, and make the ribcage read as a volume rather than a rectangular loft.
- Torso: establish chest/ribcage, waist, abdomen, and back contour with controlled front/back and side shaping rather than uniform radial scaling.
- Pelvis: establish iliac/hip, crotch, glute, and upper-leg transitions while keeping one connected editable surface and stable limb seams.
- Preserve left/right symmetry for the neutral base and deterministic behavior across supported proportions/body types.
- Keep the existing limb openings and ownership/export contracts stable unless the anatomy pass proves a seam change is required.
- Use additional geometry only where it creates useful anatomical/deformation structure; do not add another generic subdivision pass.

### Following anatomy milestones

- Face: establish useful flow and resolution for eyes/eyelids, brow, nose/nostrils, mouth/lips, cheeks, chin/jaw. The smoother cranium work is complete; the next face work must be feature topology.
- Hands/feet: progress beyond tapered block forms once the major body silhouette and face are credible.
- Limbs: revisit anatomical cross-sections only where the torso/pelvis visual checkpoint exposes a specific remaining issue; long-shaft generic rounding is complete.
- Keep topology deterministic across supported Human proportions and body types.
- Keep branch openings explicit rather than dependent on expanding magic ring assumptions.

### Acceptance checkpoints

After the anatomical torso/shoulder/pelvis slice, visually inspect a fresh neutral Human in front, 3/4, profile, and back views before proceeding to facial feature topology. The shoulder line, ribcage-to-waist transition, pelvis/glute volume, and upper-leg transition should read more anatomically than the September mannequin checkpoint.

Before moving Human V2 forward to deeper semantic tuning, repeat the full neutral quality gate after face and hand/foot milestones. Then repeat the Maxine JSON round trip and confirm the semantic system creates character-specific proportions without exposing topology artifacts.

## Phase 2 — deformation rig and weights

- Softened weighting transitions at the major bending joints while preserving deterministic normalized weights and side isolation.
- Improve pelvis/spine/clavicle articulation when visual deformation evidence demonstrates the need.
- Add twist/deformation support where needed rather than expanding the skeleton speculatively.
- Keep export/deformation skeleton distinct from any future animator control rig.
- Continue replacing purely distance-driven weighting in difficult anatomical zones with topology-aware weighting as the new base mesh exposes concrete deformation needs.

## Phase 3 — semantic character shaping

- Preserve the current model JSON round trip and provider-owned semantic vocabulary.
- Deepen semantic profiles only after the neutral base mesh passes the visual quality gate.
- Keep semantic operations focused on character identity and controlled proportion/style changes rather than compensating for missing anatomy.
- Re-test Maxine after each meaningful topology milestone to ensure semantic editability remains useful.

## Phase 4 — locomotion semantics

- Drive locomotion from contact/down/passing/up phases rather than sparse raw rotations.
- Add center-of-mass, pelvis, heel/toe, spine/clavicle and weight-transfer behavior.

## Guardrail

Architecture remains frozen unless Human V2 exposes a concrete boundary problem. Quality work should fit the existing provider/core/Blender-adapter model rather than reopening broad infrastructure cleanup.

For every major Human V2 change ask:

> Did we make Asset Assistant better without making it harder to maintain?

Flag the change before merge if it requires Blender imports inside core/providers, anatomy-specific logic in shared workflow infrastructure, hidden presentation callback replacement, silent ownership transfer, validation bypass, or a second workflow implementation inside a fastpath.
