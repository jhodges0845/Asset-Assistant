# Shared anatomy recipe contract

Status: design checkpoint for milestone 1 of the shared-anatomy alpha plan.

This document defines the smallest host-independent seam to prove before migrating provider geometry. It is intentionally a design contract, not a promise to replace provider-specific anatomy with generic primitives.

## Decision

Place shared anatomy beneath the broader **Asset Recipe** direction rather than making anatomy the universal recipe system.

The long-term V2 discovery flow is:

`user intent / search term -> asset recipe catalog -> matching AssetRecipe -> composed construction capabilities -> existing Asset Assistant workflow`

An Asset Recipe answers: **does Asset Assistant know how to make this kind of thing, and what controls does it expose?** Recipes may describe rigid/static assets, procedural organic assets, articulated biological assets, or future construction families. A rock does not need anatomy simply because Human does.

For anatomical assets, the recipe composes the shared anatomy capability:

`HumanRecipe / CanineRecipe / AvianRecipe -> anatomy resolution -> resolved anatomy -> mesh / skeleton / regions -> weights / semantic Modify`

For a rigid asset the path can remain much smaller:

`RockRecipe -> rigid/procedural geometry construction -> geometry semantics -> materials / Modify`

Both paths rejoin the existing Asset Assistant workflow for validation, components where supported, artist editing, save/reopen and export.

**Providers remain the current tested compatibility/workflow boundary while this recipe architecture is proven.** Do not remove or duplicate the provider system during milestone 1. The long-term recipe catalog is the scalable content/discovery layer; providers should not become a one-class-per-asset content catalog.

Treat the current Human mathematical system as the first complete anatomical recipe implementation beneath that larger Asset Recipe concept, not as a second public Human generator.

The anatomy layer owns resolution and anatomical metadata. Anatomy-specific constructors continue to own body-plan-specific surface construction and motion. Blender receives the existing portable mesh, skeleton, weights and animation contracts.

## Why this seam

Current code already exposes the right evidence:

- Human builds a neutral authored mathematical surface, shapes it from proportions, derives a surface-aligned skeleton, preserves authored arm ownership, and executes semantic geometry edits.
- Quadruped has a connected deformable mesh, skeleton and weights, but these are separate provider-specific generators and its advertised semantic regions are not yet executable.
- Avian has separate geometry/rigging plus executable semantic edits.

The first extraction should therefore unify the **source of anatomical truth**, not force all three providers through one mesh algorithm.

## Asset Recipe versus anatomy capability

The general recipe layer and the anatomy layer solve different problems.

### AssetRecipe

An Asset Recipe is the eventual catalog/discovery unit. It has a stable identity, searchable names/aliases, published parameters and semantic controls, and declares/composes the construction capabilities needed to produce the asset.

Examples:

- `RockRecipe`: rigid/procedural geometry + stone-oriented geometry semantics; no skeleton or anatomy.
- `SwordRecipe`: rigid construction + dimensional/detail semantics; no anatomy.
- `HumanRecipe`: anatomical construction + rigging/skinning + Human semantics + supported motion.
- `CanineRecipe`: quadruped anatomy + canine-like controls/motion.
- `AvianRecipe`: avian anatomy + wing/leg/tail controls and flight motion.

A recipe name is not necessarily a single preset. One recipe may expose useful variants such as jagged/river/boulder rock profiles or different proportion presets while retaining one known-good construction implementation.

The eventual catalog should support the V2 interaction: type a concept such as `rock`, determine whether a recipe/alias exists, then route artistic intent into that recipe's published controls. The LLM/search layer selects known-good recipes and semantic parameters; it does not author arbitrary vertices by default.

**Milestone 1 does not implement the general recipe catalog.** It only positions anatomy so the catalog can be added above it without another architectural inversion.

### Anatomy capability

Anatomy is an optional construction capability used by recipes that need a shared anatomical source of truth across geometry, rigging, skinning, semantics and motion. Static/rigid recipes do not implement placeholder anatomy concepts.

## Minimal anatomy typed concepts

Implement these as ordinary immutable Python data in a focused host-independent package such as `object_core/anatomy/`. Names may change during implementation; responsibilities should not.

### AnatomyRecipe

Provider-owned declaration/configuration for one anatomical family. It identifies a recipe/version and resolves validated provider values into `ResolvedAnatomy`.

It may call provider-specific construction helpers. It must not import Blender.

### ResolvedAnatomy

Immutable result for one complete anatomical parameter set. It is the common anatomical truth consumed by geometry, rigging, skinning and semantic operations.

Keep this object compact and anatomical. It must not become a container for materials, Blender state, animation clips, arbitrary mesh-builder configuration or general Asset Recipe metadata.

Minimum contents:

- recipe identity/version and normalized parameter identity;
- named landmarks in model space;
- named regions and deterministic region membership/ownership;
- named joint chains with parent relationships;
- local frames/bend directions where needed for deformation and motion;
- symmetry relationships;
- declared connections/attachment boundaries;
- enough provider-owned data to construct the existing mesh and skeleton deterministically.

Do **not** require every provider to share the same landmark names or limb topology.

### AnatomyRegion

A stable semantic/anatomical region identifier plus membership metadata. Region ownership must survive ordinary semantic vertex movement. Do not reconstruct critical ownership only from nearest-bone or spatial proximity when authored/topological ownership is available.

Examples: Human arm ownership, Quadruped front/hind limb regions, Avian wing regions.

### JointChain

Ordered joints/bones plus anatomical roles, parent relationship, bend plane/direction and optional motion role metadata. This is descriptive anatomy; it does not require a universal Human-like skeleton.

### AnatomyConnection

Declares how regions meet and what continuity is expected: connected body join, articulated appendage boundary, or intentionally separate surface. This gives topology audits an explicit expectation instead of guessing.

## What stays provider-specific

Do not generalize these in milestone 1:

- Human mathematical surface loft/patch construction;
- canine-like torso, scapular, pelvis, digitigrade limb and paw construction;
- Avian breast, wing, beak, leg/foot and tail-fan construction;
- provider-specific semantic shaping math;
- gait/flight behavior;
- material appearance.

A shared anatomy engine should orchestrate these using resolved landmarks/regions/chains, not replace them with a universal body-part generator.

## Human migration map

Current Human code maps cleanly onto the seam:

| Current responsibility | Recipe-system destination |
| --- | --- |
| `generate_proportions(...)` | Human recipe parameter resolution |
| `HumanSurfaceBuilder` neutral surface | Human-specific surface constructor |
| `shape_surface_point(...)` | Human recipe geometry shaping using resolved anatomy |
| authored arm index ownership | `AnatomyRegion` membership |
| `surface_skeleton(...)` | skeleton derived from the same `ResolvedAnatomy` |
| `_surface_skin_weights(...)` bone filter | region-aware skinning constraint |
| `apply_human_semantic_operations(...)` | Human semantic executor consuming resolved regions/landmarks |

The migration is successful only if existing public Human controls and provider identity remain unchanged.

## Quadruped proof slice

Before migrating all Human construction, prove the contract against a deliberately small Quadruped slice:

**torso + left front limb root/chain**.

Resolve and expose at least:

- torso/chest centerline landmarks;
- left shoulder/scapular attachment landmark;
- front upper/lower limb and paw chain landmarks;
- front-limb region membership;
- parent relationship to the torso;
- bend direction/plane;
- connected-body expectation at the shoulder.

Then construct the same current Quadruped slice from those resolved values and derive its corresponding skeleton joints from the same resolved anatomy.

This slice is useful because it immediately tests whether the contract handles a non-Human shoulder and a non-Human limb chain. Do not use Human landmark names with Quadruped aliases.

## Invariants for the first implementation PR

1. `object_core/anatomy` has no Blender dependency.
2. Same recipe/version/values produce equal deterministic resolved anatomy.
3. Mesh and skeleton for the proof slice consume the same resolved landmarks rather than recomputing dimensions independently.
4. Region membership is explicit and stable under vertex movement.
5. Provider APIs and UI-visible Human/Quadruped identities do not change.
6. No external recipe language, dynamic plugin registry or generic node graph is introduced.
7. Existing mesh/skeleton/weight output contracts remain valid.
8. The seam can represent Human bilateral arms and a Quadruped front limb without provider-specific conditionals in shared anatomy types.
9. Resolved anatomy remains compact; do not allocate a rich anatomy object per mesh vertex.
10. The anatomy package does not introduce a global recipe/provider registry or become a second provider system.
11. Static/rigid assets such as Box or a future Rock recipe require no anatomy implementation.

## Baseline before migration

Record current commit plus default and contrasting supported parameter sets for Human, Quadruped and Avian. For each provider capture:

- vertex/face counts and generation time;
- front, side and three-quarter clay silhouette;
- wireframe;
- representative bend/deformation views;
- available animation clips and generation/playback timing.

These are regression evidence, not a claim that current visual quality is acceptable.

## Proposed PR sequence

1. **Contract + baseline harness:** add compact immutable anatomy types and reproducible baseline reporting without changing provider output.
2. **Tiny Human proof:** resolve only a Human shoulder -> elbow -> wrist chain plus authored arm region ownership through the contract.
3. **Tiny Quadruped proof:** resolve torso/shoulder + one front-limb chain through the same shared types, deriving geometry/rig metadata from one resolved anatomy.
4. **Architecture review:** verify that the shared types represent both proofs without Human/Quadruped conditionals, per-vertex rich-object overhead, or a second provider/registry system.
5. **Human migration:** only after that review, route the full Human anatomical source of truth through the seam while preserving current public controls and practical outputs.
6. Proceed to the full Quadruped anatomy recipe and later Avian migration.

The review after the two small proofs is intentional. We do not need a full Human migration to learn whether the abstraction is body-plan independent.

The review after step 3 is intentional. If the shared types need Human-specific exceptions to represent the Quadruped slice, revise the contract before expanding it.

## Non-goals

This checkpoint does not implement the general Asset Recipe catalog/search UI, redesign Blender UI, create a second Human option, solve final pelvis anatomy, add species presets, implement physics, change export formats, or tune final animation. It creates the seam that lets those quality improvements share trustworthy anatomical information without coupling their surface algorithms.
