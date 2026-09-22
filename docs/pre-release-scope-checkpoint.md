# Pre-release scope checkpoint

> Scope update (2026-09-21): [Shared anatomy and animation](shared-anatomy-alpha-plan.md) is the active pre-alpha plan. Complete the Human/Quadruped/Avian recipe and animation quality milestones before final release hardening. The older checklist below contains historical claims and must be reconciled against source before treating an item as outstanding.


This checkpoint began after the Avian leg/Walk correction and now tracks the path to the first public alpha.

## Current status

- The preservation-aware Modify foundation, external inspection/change-file handoff, transactional parameter regeneration, metadata-only animation rename path, and persistent semantic patch architecture are implemented.
- Avian and Human both have provider-owned topology-preserving semantic geometry executors.
- A real Human inspection -> external returned Modify file -> Blender apply round trip has been manually confirmed, including preservation of the existing rig.
- The Blender sidebar is unified under one **Asset Assistant** tab with **Generate / Modify / Rig / Animate / Validate / Export**.
- Human base-geometry quality work is active because the rich Modify proof exposed that semantic operations need stronger reusable facial/body structure to produce useful character identity.
- Release packaging/tag automation exists, but no tag or release should be created until the version/release decision is explicitly approved.

## Confirmed foundation

- Human, Quadruped, and Avian all generate through the shared provider-driven Blender workflow.
- Human has Idle / Walk / Run.
- Quadruped has Idle / Walk / Run.
- Avian has connected legs and feet plus distinct Idle / Walk / Flight clips; Run remains intentionally unsupported.
- Representative target-export coverage exists across Godot, Unity, Unreal, and Cura paths.
- Core/provider anatomy remains host-independent while Blender-specific workflow behavior remains in the Blender adapter.
- Shared Modify code remains provider-neutral; Human and Avian anatomy/semantic interpretation stay inside their providers.

## Modify workflow status

The current workflow is:

`Select generated asset -> Export Inspection File -> edit externally -> Import Change File -> review plan -> Apply Imported Changes -> revalidate`

Implemented behavior includes:

- stable asset/provider identity binding;
- portable inspection/request documents;
- non-mutating import/preview;
- re-inspection/replanning immediately before apply;
- transactional provider-parameter regeneration;
- preservation blockers for ambiguous artist-owned generated relationships;
- generated animation export-name changes without geometry regeneration;
- provider semantic target manifests and executable-operation reporting;
- persistent semantic patch recipes that survive re-inspection and later parameter regeneration;
- Avian semantic geometry execution;
- Human semantic geometry execution, including body, torso, shoulders, head, face, jaw, cheeks, arms, and legs.

Unsupported operations remain blockers rather than silent partial application.

## Human rich-Modify quality checkpoint

The first end-to-end Human external Modify test worked technically but exposed the next product-quality limitation: the generated Human mesh did not initially contain enough facial structure for recognizable character design.

Completed refinement since that checkpoint:

- increased head profile resolution from chin through jaw/cheek/temple/crown;
- added provider semantic targets for `jaw` and `cheeks`;
- added reusable jaw/cheek profiles;
- added neutral facial structure for chin, mouth, nose, eye recess, brow, and forehead;
- completed manual front/side Blender review confirming visible improvement.

Current limitation: the facial landmarks are still broad. Brow, nose bridge/tip, mouth/chin projection, and local facial readability need further reusable refinement before the Human -> specific-character proof is considered visually complete.

## Hair, clothing, accessories, and physics boundary

Hair and clothing are intentionally not ordinary Human geometry edits. They should become first-class attachable components because they may require independent geometry, materials, rigging/weights, collision, and optional physics.

The planned ownership boundary is:

- Human owns body/facial geometry, skeleton/weights, skin/material foundation, and attachment context;
- Hair owns hairstyle geometry/materials plus optional dynamic metadata;
- Clothing owns garment geometry/materials plus rig/weight and optional cloth/collision metadata;
- Accessories own rigid or skinned attachment behavior;
- Blender/Godot/Unity/Unreal adapters translate optional physics intent for their host/engine.

These component operations remain non-executable until persistence, ownership, inspection, validation, and safe apply behavior are implemented.

## UI overhaul status

The main workflow is organized as one ordered Asset Assistant sidebar experience:

`Generate -> Modify -> Rig -> Animate -> Validate -> Export`

Generate starts expanded; later workflow panels begin collapsed. Stable historical panel/operator identifiers remain underneath for compatibility. Animation export-name controls remain under Animate. The structural UI blocker is complete; visual polish remains part of final release review.

## Revised pre-release order

1. ~~Checkpoint provider state and initial documentation sync.~~ Complete.
2. ~~Implement preservation-aware Modify and external file handoff.~~ Complete.
3. ~~Implement persistent provider-aware semantic geometry architecture.~~ Complete for Avian and Human geometry.
4. ~~Complete structural UI overhaul.~~ Complete; final polish remains.
5. Finish the current Human reusable facial/base-geometry quality checkpoint.
6. Define and implement attachable component architecture for hair/clothing/accessories, with physics kept adapter-facing.
7. Run useful end-to-end Avian -> specific bird and Human -> specific character external Modify proofs.
8. Run and close the full cross-provider regression, preservation, architecture, docs, and test-coverage audit.
9. Finish release hardening and run a clean packaged-install smoke test in Blender 5.2.1.
10. Make an explicit version/tag decision and publish the first public alpha only after approval.

Animation polish, exhaustive destination certification, finished anatomy, Quadruped semantic execution, and broader provider expansion remain follow-up work unless testing exposes a release-severity defect.
