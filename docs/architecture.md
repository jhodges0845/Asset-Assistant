# Architecture

Asset Assistant separates host-independent asset logic from Blender integration and destination-specific export behavior.

The high-level flow is:

`Generate OR Import -> inspect/adopt -> configure behavior/attachment -> edit/animate -> validate -> save editable state -> validate for target -> export`

An editable `.blend` checkpoint is the authoritative resumable working state. Delivery formats are not replacements for editable project state.

## Core boundary

`object_core` owns host-independent contracts and generation logic and never imports Blender. Providers own anatomy/asset-specific behavior; `blender_adapter` translates those contracts into editable Blender data; target adapters own destination behavior.

The canonical generation providers remain Human, Quadruped, Avian, and Box. Shared workflow code consumes capabilities rather than anatomy names.

## Import and adoption are first-class entry paths

Generation is not required. An artist may bring an asset created without Asset Assistant into the workflow. Asset Assistant should inspect recognizable geometry, rigs, materials, weights, animations and attachments, report what it can safely support, and ask for explicit adoption/registration before claiming management rights.

Adoption is preservation-first. Unsupported or unusual external structures should degrade to reduced Asset Assistant capabilities rather than forcing regeneration. Artist/imported materials, animation curves, rigs, NLA, drivers and unrelated objects are never silently claimed. Ownership transfer must be explicit and validated.

## Components

Hair, clothing and accessories are **separate assets**, created/generated/imported independently from a base body and attached later. They are not Human body semantics. Component kind answers *what the asset is*; behavior answers *how it participates in the scene*. These concepts must remain independent.

The portable behavior profiles are:

- `static`: no component deformation/rig requirement;
- `rigid`: follows an attachment/root/bone without deforming;
- `parent_skinned`: deforms from the parent character rig;
- `self_rigged`: owns an independent rig and may later own independent animations;
- `physics_assisted`: declares optional dynamics intent layered over a compatible attachment/rig strategy.

Examples: a ring can be static/rigid; fitted clothing can be parent-skinned; a mechanical gauntlet can be self-rigged; hair can be static on a low-cost path, bone-driven, or physics-assisted. Material/emission behavior such as a glowing ring must not require a fake skeleton.

Performance-heavy behavior is opt-in. Components should have graceful lower-cost fallbacks where practical so projects can target older hardware. Physics intent stays portable; Blender/game-engine adapters decide how to realize it.

Rigid and parent-rig-skinned imported adoption, ownership metadata, safe remove/replace, and checkpoint persistence are already implemented. Self-rigged animation lifecycle and richer physics realization are follow-up work built on the same component contract rather than separate hair/accessory workflows.

## Validation and persistence

Validation is a gate in the normal workflow, not a cleanup step. Before an editable checkpoint is saved, working-state validation should verify identity, ownership, rig/attachment compatibility, component records and animation state. Before destination export, fresh target validation must verify current scene state and target-specific requirements. A prior green result or successful file write is not authorization to export.

The intended production workflow is therefore:

`Generate/Import -> Inspect/Adopt -> Configure -> Preview -> Validate -> Save Editable Checkpoint -> Reopen/Continue -> Validate for Target -> Export -> Destination Review`

Marked Asset Assistant `.blend` checkpoints auto-validate on reopen, including Blender native File/Open and Recent Files. Ordinary unmarked `.blend` files remain side-effect free until explicitly adopted.

## Animation architecture

Animations are first-class assets with stable IDs independent of Blender Action names. Generated clips are Asset Assistant-owned and reproducible. Artist/imported Actions can be registered without transferring curve ownership. Managed Actions are scoped by rig compatibility and owning Asset Assistant rig identity.

A self-rigged component may eventually own its own animation set (for example Deploy/Retract/Charge on a mechanical gauntlet) independently of the character's Idle/Walk/Run. Non-skeletal behaviors such as material emission, visibility, shape keys and physics are not forced through the skeletal animation contract.

External animation Modify currently supports safe generated-clip refinement for duration/strength/export name while preserving stable identity and unrelated Actions.

## Provider and Blender boundaries

Concrete provider implementations live under `object_core/providers`. Anatomy-specific geometry, bone names, landmarks, UV/surface choices, weights, semantic Modify rules and motion generation stay provider-owned. `blender_adapter` owns Blender scene inspection, UI, rig application, component adoption, checkpoint persistence, Modify transport, material preparation, validation and export orchestration.

`humanoid_blender` remains a compatibility entry point only. New Blender implementation belongs in `blender_adapter`.

The dependency direction is enforced in CI: `object_core` and its providers may not import `bpy`, `blender_adapter`, or `humanoid_blender`. New host-specific behavior must be introduced on the adapter side of the boundary instead of leaking into the portable core.

## Target adapters

Destination flow is:

`Editable working state -> fresh Validate -> Target Profile -> Blender Target Adapter -> Export -> Destination Review`

Current defaults are Godot GLB/glTF, Unity FBX, Unreal FBX, and Cura STL. Target adapters preserve source state where practical and never turn a successful file write into a production-readiness claim.

## Tests and compatibility

Tests mirror boundaries: core and architecture guardrail tests run under `tests/core`, Blender integration runs under `tests/blender`, Python 3.9-3.12 is the supported/tested core range, and Blender 5.2.1 is the current supported/tested Blender integration target. Cross-provider and editable-continuity tests protect ownership, persistence, Modify and export behavior.

Support claims must follow tested CI coverage. Adding or removing a supported Python or Blender version requires updating both CI and user-facing compatibility documentation in the same change.

## Architecture rule of thumb

1. Host-independent asset behavior belongs in `object_core`.
2. Provider/component-specific behavior stays with that provider/component.
3. Blender translation, persistence, inspection, scene behavior and UI belong in `blender_adapter`.
4. Destination-specific behavior stays in the target adapter/profile.
5. New abstractions should be proven by real implementations, not speculative framework work.
6. New UI composition should register through explicit presentation/workspace extension points rather than replace another module's callbacks.

The product rule is equally important: **Asset Assistant enhances existing 3D work; it must not require artists to start over inside Asset Assistant.**
