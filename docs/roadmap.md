# Asset Assistant Roadmap

This is the working source of truth for current development priorities. Before continuing development, verify live GitHub main, open PRs, and CI state rather than assuming the state recorded here is still current.

## Active pre-alpha milestone: shared anatomy and motion

The next alpha requires a shared anatomy construction system with Human, Quadruped and Avian recipes, followed by a new cross-provider animation quality pass. The goal is visibly appealing models and motion through one coherent workflow. Packaging readiness alone no longer closes the alpha gate.

Implementation plan and acceptance criteria: [Shared anatomy and animation alpha plan](shared-anatomy-alpha-plan.md).

1. [ ] Capture current visual/performance baselines; prove the shared recipe contract with Human and a Quadruped slice.
2. [ ] Migrate Human without losing current geometry, rigging, semantic Modify or component behavior.
3. [ ] Build and visually accept a Quadruped anatomy recipe with executable semantic shaping.
4. [ ] Build and visually accept an Avian anatomy recipe with articulated wing and leg structure.
5. [ ] Close cross-provider deformation, semantic variation and artist-preservation proofs.
6. [ ] Complete Human Idle/Walk/Run, Quadruped Idle/Walk/Run and Avian Idle/Walk/Flight quality passes.
7. [ ] Verify the packaged candidate, destination output, documentation and release metadata; publish alpha only after approval.

This sequence supersedes the older Human-only near-term milestone and release-hardening-only scope below. Earlier checkpoints describe evidence and history, not additional prerequisites for this alpha. No shared recipe system is implemented yet.

## Product vision

Asset Assistant is an open-source, artist-first 3D workflow assistant. Generation is optional: artists can generate, reopen, or import existing work and adopt it into the same preservation-aware workflow.

Canonical production flow:

`Generate OR Import -> Inspect/Adopt -> Configure behavior/attachment -> Preview -> Validate -> Save Editable Checkpoint -> Reopen/Continue -> Validate for Target -> Export`

## Engineering guardrails

- `object_core` remains host-independent; Blender behavior stays in `blender_adapter`.
- Providers/components own specialized semantics; shared workflow remains capability-driven.
- Hair, clothing and accessories are separate assets, never Human body semantics.
- Component kind and component behavior are independent.
- Expensive behavior is opt-in and should degrade gracefully for older hardware.
- Imported/external work is preservation-first and never silently claimed.
- Validation is mandatory before save and freshly repeated before destination export.
- `.blend` is the canonical editable checkpoint; GLB/FBX/STL/3MF are delivery formats.
- No release/tag without explicit approval.

## Development / CI rules

Main is protected and changes go through branches/PRs. Required CI covers Python 3.9, 3.10, 3.11 and 3.12 plus Blender 5.2.1 integration coverage. Blender 2.92.0 is no longer a supported or required runtime. Blender CI also performs a real component `.blend` save/reopen smoke test and an isolated packaged-add-on smoke test. During the current development-hardening phase, successful PRs are authorized to merge after all required checks pass. On failure, inspect and fix the exact failing job rather than guessing. Never create a release or tag without explicit approval.

## Completed foundation

- [x] Human, Quadruped, Avian and Box provider foundations.
- [x] Host-independent core + Blender adapter boundary.
- [x] Human/Avian semantic Modify and external model exchange.
- [x] Component records, rigid/bone attachment and parent-rig skinning.
- [x] Imported rigid and parent-skinned component adoption with artist material preservation.
- [x] Safe component remove/replace and Modify component state.
- [x] Editable `.blend` save/reopen continuity, including native Blender reopen validation.
- [x] First-class animation records and imported/artist Action registration.
- [x] External generated-animation refinement for duration/strength/export name.
- [x] Godot/Unity/Unreal/Cura target adapters with automated Blender 5.2.1 coverage.
- [x] Real `.blend` reopen smoke coverage for base asset identity, self-rigged component ownership and stable animation identity.
- [x] Blender-native UI/UX pass across Create, Modify, Rig, Animate, Validate and Export, including current-asset context, component hierarchy, animation workspace, validation severity grouping and export-confidence framing.
- [x] UI wrapper-composition compatibility coverage through full add-on registration and the export fast path.
- [x] Blender 5.2.1 dynamic Hair behavior enum registration cleanup while preserving the visible `Rigid` default.
- [x] Generated-model LLM JSON round trip: export self-documenting model context, import/validate an LLM-authored `modify-request/v3`, visually preview without mutating the live asset, then explicitly apply supported changes.
- [x] Model context publishes executable semantic argument contracts and compact current semantic state so LLM edits can be authored against supported controls and current proportions.
- [x] End-to-end generated-Human semantic JSON proof produced a visibly changed silhouette, validating the round-trip architecture and exposing Human geometry fidelity as the next quality ceiling.

## Earlier checkpoint — Human quality foundation

The model JSON transport/validation/preview architecture is now sufficiently proven to stop redesigning the exchange format. The current Human test showed that semantic intent can reach the provider and visibly alter the generated character. The limiting factor is now the coarse Human base geometry/topology: additional semantic labels alone cannot produce a convincing high-fidelity character if the provider does not contain enough anatomical structure to express them.

Do not make the LLM author arbitrary vertices as the default solution. Keep the abstraction:

`LLM artistic intent -> published semantic contract -> provider-owned known-good geometry`

Human V1 remains useful as a lightweight/blockout path. A higher-fidelity Human path can coexist with it. Whether fidelity selection later becomes dynamic is deliberately undecided for now.

### Advanced Human Geometry / Human Provider V2 direction

The next Human quality milestone should proceed in layers:

1. **Anatomy/topology:** improve neck/shoulder transition, clavicle/chest, ribcage, waist, pelvis/hips/glutes, thighs/knees/calves/ankles, upper/lower arms, elbows/wrists/hands, and a substantially more capable head/face mesh.
2. **Semantic anatomy profiles:** expand provider-owned controls for pelvis, waist, chest/bust, glutes, thighs, knees, calves, neck, hands, jaw/chin, cheekbones, brow, eyes, nose and lips. Hair, clothing and accessories remain separate components.
3. **Surface/detail:** smoothing/subdivision/normals, facial detail and materials after the geometry can already carry the intended anatomy and silhouette.

**Acceptance direction:** generate a recognizable, game-ready-ish neutral Human base and push anatomy, silhouette and face substantially toward a supplied hero-character direction through semantic Model JSON before hair, clothing and accessories are attached. The acceptance character is evidence of provider capability, not hard-coded provider logic.

See [Model JSON round trip](model-json-roundtrip.md) for the validated exchange workflow and current contract decisions.

## Independent game-development audit checkpoint

A clean-room game-tools review of the repository reached the following working conclusions. These are deliberately recorded as external-review observations rather than product claims:

- **Core architecture is a strength.** The host-independent core, provider ownership, Blender adapter, and destination-specific behavior have survived expansion across multiple providers, components, imported assets, animation, export and LLM-assisted modification without requiring a fundamental rewrite.
- **CI/test depth is above average for an independent Blender tool.** Core tests span Python 3.9-3.12, Blender 5.2.1 integration runs in CI, real save/reopen behavior is exercised, and the packaged add-on is tested in isolation.
- **The primary engineering debt is Blender integration composition.** `prepare()`/`install()` layers that patch or replace callbacks are increasingly order-sensitive. This has already produced real UI regressions. Future cleanup should move toward explicit presenter/workflow registration or another composition mechanism that does not depend on hidden callback replacement order.
- **The primary product-quality ceiling is generated Human fidelity.** The workflow can already carry semantic intent; the base Human geometry is now the limiting factor for character-quality output.
- **Engine interoperability is promising but still evidence-scoped.** Godot/Unity/Unreal/Cura support is meaningful, but broader production confidence still requires more engine-side repeatability around animation import/retargeting, root motion, skeletal naming, materials and coordinate conventions.
- **Static quality gates should eventually expand.** Functional/integration testing is strong, but linting, static analysis/type checks and an explicit coverage floor would help catch maintainability regressions before Blender runtime testing.
- **Documentation/source-of-truth drift must be watched.** Supported runtime/version statements and package metadata should stay synchronized so contributors and downstream users do not see contradictory support contracts.

The external-review recommendation is not another broad architecture rewrite. Preserve the current core/provider/adapter boundaries, improve one end-to-end character workflow to a substantially higher quality bar, and pay down Blender composition fragility in parallel before adding many more workflow layers.

## Imported asset continuity

Imported/external work remains preservation-first. Existing normalization/adoption work establishes a stable logical asset boundary, supports imported animation registration, and keeps artist-owned geometry/rig/material/animation data distinct from generated provider ownership. Imported model JSON modification remains a separate capability problem: external geometry must not be treated as though it has original generator parameters.

Continue to prefer derived measurements/landmarks and explicitly scoped safe operations for future imported-model modification rather than silently claiming or regenerating artist data.

## Production components and external adoption

Keep the shared workflow capability-driven. Do not create separate special-purpose workflows for hair, clothing and accessories when the existing Generate/Import -> behavior -> attachment -> validate/save/export workflow can handle them.

### Shared component behavior

- [x] Portable behavior profiles: static, rigid, parent-skinned, self-rigged, physics-assisted.
- [x] Backward-compatible behavior inference for existing component records.
- [x] Expose currently executable behavior selection through the existing Generate/Import component workflow rather than a new parallel UI.
- [x] Working-state validation gate before editable save for base/component/ownership integrity.
- [x] Fresh target validation remains mandatory before destination export.
- [x] Self-rigged component lifecycle validation and cleanup preserve unrelated artist Actions.
- [x] Character Idle/Walk/Run export remains functional when component-owned armatures are present.

### External asset adoption

Generation is not required. Asset Assistant inspects external work before claiming management rights. Adoption is preservation-first: never silently claim artist-authored rigs, materials, animation curves, geometry, weights, NLA, drivers, or unrelated objects. Unsupported structures report reduced capability or blocked adoption rather than force regeneration.

- [x] Imported rigid artist mesh adoption.
- [x] Imported parent-rig-skinned mesh adoption.
- [x] Existing Generate entry stage can adopt a selected external mesh as Hair, Clothing, or Accessory with Static, Rigid, or Parent-Skinned behavior where supported.
- [x] General external-object inspection entry point before ownership transfer — PR #165.
- [x] Supported / reduced-capability / blocked status surfaced before adoption — PR #166.
- [x] Reuse first-class imported animation registration for external Actions — PR #167.
- [x] Imported `.blend`, GLB/glTF and FBX base assets retain a stable logical hierarchy boundary after import so inspection is not tied to a particular selected child.
- [x] Explicit adoption/onboarding allows supported external work to enter Asset Assistant without pretending it was generated by a provider.
- [ ] Expand safe reduced-capability adoption for recognizable external rigs/hierarchies without destructive retargeting. Current reduced cases remain preservation-first and may require artist cleanup.
- [ ] Add imported-model LLM JSON modification using derived external-asset state and explicitly safe operations rather than generated-provider parameters.

### First production proofs

1. **Accessory proof — PR #161:** generated Ring/Bracelet is a separate lightweight component with editable radius/thickness, Static/Rigid behavior and root/bone attachment.
2. **Hair low-cost proof — PR #162:** generated Hair Shell is a separate lightweight component with editable width/depth/cap height/back length, Static/Rigid behavior and root/bone attachment.
3. **Hair bone-driven tier — PR #163:** rigged Humans can choose Parent-Skinned/Bone-Driven hair using head/neck/torso weighting without physics or an extra component rig.
4. **Clothing proof — PR #164 merged:** generated Basic Shirt is a separate lightweight parent-rig-skinned Human component with fit ease/length controls and torso/neck weighting.
5. **Self-rigged accessory proof completed:** generic Mechanical Gauntlet owns its own armature and Flex action independently from character locomotion. Lifecycle hardening landed in PR #169; multi-rig export preservation landed in PR #170; real reopen proof landed in PR #171.
6. **Physics hair tier:** optional later enhancement only after the bone-driven path is visually accepted; never required for older-hardware targets.
7. Generalize catalog/provider UX only after hands-on evidence shows the shared workflow is understandable.

### Performance rule

Hair/accessory/clothing motion must not become a baseline runtime requirement. Prefer tiers/fallbacks: Static/Rigid cheapest, Parent-Skinned/Bone-Driven middle path, Physics-Assisted optional. Material animation such as emissive glow must not require skeletal animation. This is especially important for projects targeting older hardware.

## Animation continuity

Animations are first-class assets with stable IDs independent from Blender Action names. Generated clips are Asset Assistant-owned/reproducible. Artist/imported Actions can be registered while preserving artist curve ownership. External generated-animation refinement supports duration/cycle speed, strength and export name while preserving stable identity and unrelated clips.

Self-rigged components can own an independent animation/rig lifecycle without being folded into the character Idle/Walk/Run library. Non-skeletal behaviors such as material emission, visibility, shape keys and physics must not be forced through the skeletal animation contract.

The animation LLM JSON workflow is established separately. Continue improving semantic animation calibration/vocabulary rather than making the LLM infer raw rig-local rotations whenever provider-aware semantics can express the intent more reliably.

## Quality / evidence work remaining

- [ ] Advanced Human Geometry / Human Provider V2 anatomy/topology foundation.
- [ ] Expanded Human semantic anatomy profiles after the V2 topology can express them.
- [ ] Human V2 surface/detail pass after anatomy and semantic control are visually useful.
- [ ] High-fidelity hero-character semantic Model JSON acceptance test against Human V2 before hair/clothing/accessories.
- [ ] Refactor order-sensitive Blender `install()`/`prepare()` composition toward explicit workflow/presenter registration.
- [ ] Add static quality gates such as linting/static analysis and define a useful coverage floor.
- [ ] Imported-model LLM JSON safe modification path.
- [ ] Animation semantic calibration/vocabulary follow-up for stronger first-attempt LLM animation quality.
- [ ] Visually accept/reject the bone-driven hair tier before any physics-hair work.
- [ ] Perform representative Human Cura slicing/physical-print review.
- [ ] Verify Godot, Unity and Unreal output after major Human geometry changes, including Idle/Walk/Run and a self-rigged component case.
- [ ] Continue Export UI hierarchy/blocked-reason polish and explicit glTF UI/documentation work where still open.
- [ ] Semantic static-model proof such as Box -> recognizable rock.
- [ ] Test coverage, documentation and architecture cleanup at meaningful checkpoints rather than allowing long implementation chains to drift.

## Post-launch import expansion

- [ ] Add STL import as a first-class **Static Mesh / Print Asset** workflow rather than pretending STL carries character/rig semantics. Inspect geometry, scale, normals, manifold/watertight state, disconnected geometry and Cura-oriented print readiness after import.
- [ ] Evaluate 3MF import alongside STL so the print workflow can preserve richer manufacturing/material information where Blender support permits.

## Provider quality follow-ups

Human visual refinement is now a primary provider-quality track rather than a generic polish note. Human V1 can remain lightweight while Human V2 develops higher-fidelity anatomy and semantic expressiveness. Quadruped rich semantic Modify remains future work. Avian foundation and rich semantics are complete; further polish is evidence-driven.

## Earlier Human milestone

> Preserve the proven Generate/Import/Modify/Animate/Validate/Export architecture while raising the Human provider's geometry and semantic expressiveness enough that an LLM-authored Model JSON request can produce a recognizable, useful character base rather than only a proportionally modified mannequin.
