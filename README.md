# Asset Assistant

**Asset Assistant** is an open-source, artist-first 3D workflow tool for creating and preparing editable assets. It helps artists generate starting points, rig, animate, surface, validate, prepare, and export characters, creatures, props, and other 3D assets while keeping the artist in control of the creative result.

Asset Assistant is **not intended to replace artists**. Its purpose is to remove repetitive and technical friction so artists can spend more time designing, sculpting, refining, and making creative decisions. Generated and prepared assets should remain editable, understandable, and practical to continue working on in Blender and downstream tools.

The project uses an independent Python core with a thin Blender adapter. **Human, Quadruped, and Avian now have completed deforming-provider foundations**, while Box and a small non-Human animated proof exercise additional shared capability shapes.

Licensed under **GPL-3.0-or-later**. Redistribution and modification are permitted under [the license](LICENSE); see [notices](NOTICE). Generated models do not need to use the GPL merely because they were created with this program.

> **Development roadmap:** use [docs/roadmap.md](docs/roadmap.md) as the working source of truth for priorities, TODOs, milestone definitions, and engineering guardrails.

## Blender workflow

Choose **Human**, generate it, then use **Animate > Rig & Pose** and animation.
See the [Human workflow and code map](docs/human-workflow.md).

Blender 5.2.1 is the supported Blender runtime and the required integration-test target. Blender 2.92.0 is no longer a supported runtime; current development is allowed to use modern Blender behavior without carrying legacy 2.92 compatibility constraints. Standalone CI continues to cover Python 3.9-3.12.

The Asset Assistant sidebar has four workspaces:

| Workspace | Purpose |
| --- | --- |
| Create | Generate Human, Quadruped, Avian or Box; inspect or Modify the current asset. |
| Animate | Add the supported rig, pose it, and generate/select animation clips. |
| Components | Add or manage attached asset components. |
| Export | Choose a target, prepare materials, validate and export. |

## Human status

Human uses one connected mathematical surface, a matching deforming skeleton,
normalized weights, provisional UVs/materials and editable Idle/Walk/Run actions.
It is registered as `HumanProvider` with key `human`. There is no separate static
Human option. The low-level rigid blockout is only an internal pipeline fixture.

This is pre-alpha: anatomy, joint deformation, hand detail, UVs and motion quality
still need visual refinement. Automated workflow checks do not establish final
character quality. See the [Human workflow](docs/human-workflow.md),
[rigging](docs/rigging.md), [animation](docs/animation.md), and
[target verification](docs/target-verification.md).

## Quadruped status

**Quadruped is complete as the current editable four-legged provider foundation.** It generates one connected deformable surface from host-independent dimensions, supplies a quadruped skeleton and localized skin weights, face-corner UVs, a portable textured PBR base coat, and separate generated Idle/Walk/Run clips.

Quadruped deliberately reuses the same provider-driven Blender generation, rigging, animation, material and export infrastructure as Human. Quadruped-specific anatomy remains in `object_core/providers`; no parallel provider-specific Blender workflow is required. Automated Blender tests cover generation, armature binding, deformation at major quadruped junctions, animation creation/playback behavior, UV/material translation and preservation of artist-authored material data. Interactive Blender 5.2.1 review confirmed the generated rig and animations play on the connected mesh.

The current implementation is a low-poly editable starting point rather than an exhaustive all-species generator, finished anatomy, or fur system. Broader destination-specific certification can continue as release hardening.

## Avian status

**Avian is complete as the current editable flying-creature provider foundation.** It generates one connected deformable surface with integrated wings and tail, supplies an Avian-specific spine/neck/head/wing/tail skeleton, normalized local skin weights, deterministic UVs, a portable textured plumage material, and separate generated Idle and Flight clips.

Flight is a real provider-specific locomotion identity rather than a Walk alias. Avian motion generation stays in the provider while the Blender adapter continues to use the shared editable action/export pipeline. Automated coverage verifies wing/tail deformation, symmetric wingbeat behavior, separate Idle/Flight actions, and capability isolation so Human and Quadruped do not gain Flight accidentally.

Representative automated export coverage now exercises Avian through Godot GLB and Unity FBX using the same provider-neutral target adapters. The remaining Avian-specific manual checkpoint is visual animation-quality review in Blender; broader destination playback certification belongs to release hardening rather than provider-foundation completion.

## Install from source

Clone or download this repository, then run in its root folder:

```powershell
python -m scripts.build_blender_addon
```

In Blender, open Edit > Preferences > Add-ons > Install and select the generated `dist/asset_assistant.zip`. Enable **Asset Assistant**. In Object Mode, press N in the 3D Viewport, then open **Generator**.

The packaged add-on uses Asset Assistant branding while retaining historical `humanoid_blender` / `humanoid.*` compatibility identifiers where required by existing Blender data and scripts. [Installation, update, and uninstall guide](docs/blender.md).

## Independent Python core

There are no third-party runtime dependencies. Core code must never import Blender APIs.

```python
from object_core import BodyType, HumanoidSpec
from object_core import generate_proportions, generate_mesh, generate_skeleton

spec = HumanoidSpec(height_cm=180, weight_kg=95, body_type=BodyType.OVERWEIGHT)
proportions = generate_proportions(spec)
mesh = generate_mesh(proportions)
skeleton = generate_skeleton(proportions)
```

Presets are slim, average, muscular, overweight, and obese. They are artistic controls, not medical classifications. The current proportion generator supports 120-240 cm and 30-300 kg. [Proportion rules](docs/proportions.md).

## Tests

```powershell
python -m unittest discover -s tests -v
```

Ordinary Python discovery runs core tests and skips Blender-only integration tests. CI additionally runs the suite inside Blender 5.2.1, including deforming providers, workflow, validation, export, and isolated packaged-add-on coverage. The Blender runtime is cached between CI runs.

Human coverage verifies deformable topology across presets and height extremes, representative joint deformation, generated surface/texture preparation, animation coexistence/switching and target export behavior. Quadruped coverage verifies deterministic connected geometry, quadruped rig/weights, parent-child deformation blends, real Blender surface deformation, Idle/Walk/Run generation, UV completeness, generated texture/material preparation and generic provider workflow integration. Avian coverage verifies deterministic connected geometry, rigging/skinning, wing/tail deformation, UV/material preparation, Idle/Flight generation, capability isolation, and representative Godot/Unity export packaging.

## Structure

```text
object_core/
    objects.py       Provider registry, input fields and type capabilities
    targets.py       Host-independent output profiles and target validation
    models/          Independent data contracts
    proportions/     Dimensions and shared joint locations
    geometry/        Mesh generation
    rigging/         Skeleton and skin-weight generation
    animation/       Portable animation tracks and generation
    providers/       Provider-specific generation, anatomy and behavior
    validation/      Host-independent readiness rules
blender_adapter/     Canonical Blender adapter, UI, rigging, scene inspection, and export
humanoid_blender/    Historical compatibility entry point/module ID
tests/               Core and Blender tests
scripts/             Add-on build, CI helpers, and Blender inspection/test runners
examples/            Standalone core examples
docs/                Architecture, workflow, provider, target, geometry, and roadmap docs
```

See [Architecture](docs/architecture.md), [providers](docs/providers.md), and [workflow](docs/workflow.md).

## Output targets

`Define -> Generate -> Rig (if supported) -> Animate (if supported) -> Surface -> Validate -> Target Prepare -> Export -> Artist Review`

| Destination | File |
| --- | --- |
| Godot | GLB (default), glTF alternative |
| Cura | STL in millimetres, evaluated current pose |
| Unity | FBX with supported rig/animation/material data |
| Unreal Engine | Model/skeleton FBX plus one FBX sidecar per generated clip, imported as animation-only against the model skeleton |

Initial smoke verification exists for Godot, Unity, Unreal, and Cura. Human has completed destination evidence for Godot, Unity, and Unreal; Quadruped has completed its Blender provider checkpoint and reuses those generic target adapters; Avian now has representative automated Godot GLB and Unity FBX export coverage. Destination checks are scoped evidence rather than broad production certification. See [target verification](docs/target-verification.md) and [supported target scope](docs/targets.md).

## Release readiness

Provider expansion is complete for the first release scope. Before alpha, current priorities are a shared anatomy system with Human, Quadruped and Avian recipes and a new animation quality pass, followed by release hardening. See the [active alpha plan](docs/shared-anatomy-alpha-plan.md).
