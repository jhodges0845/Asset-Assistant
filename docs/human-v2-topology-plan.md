# Human V2 Topology Plan

Human V2 is a coordinated geometry, deformation, and motion quality pass. It is not a polygon-count increase. The goal is a procedurally generated neutral Human that already reads as recognizably human in Blender solid shading, before semantic/LLM character shaping is applied.

## Visual checkpoint — September 2026

A fresh neutral Human and a Maxine model-change round trip were compared after the torso support, facial support, neutral facial-anatomy, and soft-joint-weighting work.

The round trip is functioning: Maxine's parameter and semantic changes materially alter height/weight/body type, shoulder width, torso/waist proportions, limb proportions, head/face, jaw, and cheeks. The limiting factor is now the base mesh. The current low-resolution ring/branch surface turns a neutral mannequin into a differently proportioned mannequin, and stronger face operations can exaggerate angular planes rather than produce convincing anatomy.

This is the Human V2 quality gate:

> A neutral Human with no LLM modifications should already look recognizably human and reasonably smooth in solid viewport shading. Semantic operations should create character identity, not be responsible for creating basic human anatomy.

Accordingly, intentional base-mesh topology is now the highest Human V2 priority. Additional semantic-profile tuning, rig expansion, locomotion work, and final UI polish remain behind this gate unless a concrete blocker requires otherwise.

## Phase 1 — topology/anatomy foundation

### Completed foundation

- Added intentional support topology around pelvis/hip transitions and shoulder/armpit transitions.
- Added deterministic head-local facial support topology without breaking manifold connectivity.
- Added neutral facial depth for jaw, mouth/lips, nose, cheeks, eye sockets, and brow.
- Preserved deterministic generation, one connected editable body, UV coverage, semantic editability, and export behavior.

### Current priority — production-oriented procedural base mesh

Replace the blockout-level anatomical surface with intentional topology while preserving the existing provider/core architecture and deterministic generation.

- Face: establish useful flow and resolution for eyes/eyelids, brow, nose/nostrils, mouth/lips, cheeks, chin/jaw, and a smoother cranium.
- Torso: improve chest/ribcage, waist, abdomen/back, and shoulder transitions so the silhouette is anatomical rather than box-like.
- Pelvis: improve iliac/hip, crotch, glute, and upper-leg transitions while preserving a connected body.
- Limbs: use anatomical cross-sections and support around upper/lower arms and legs instead of long tapered prisms.
- Hands/feet: progress beyond tapered block forms once the major body silhouette is credible.
- Use additional geometry where anatomy/deformation requires it; polygon count is secondary to useful placement and edge flow.
- Keep topology deterministic across supported Human proportions and body types.
- Keep branch openings explicit rather than dependent on magic ring indices.

### Acceptance checkpoint

Before moving Human V2 forward to deeper semantic tuning, generate and visually inspect a neutral Human in front, 3/4, and profile views. It should read as a credible generic human without relying on Maxine-specific semantic operations. Then repeat the Maxine JSON round trip and confirm the semantic system creates character-specific proportions without exposing topology artifacts.

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
