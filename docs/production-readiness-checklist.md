# Production Readiness Checklist

This document is the current manual and product-readiness gate for Asset Assistant before a production/public-alpha decision. Passing automated CI is necessary but is not sufficient. The installed Blender UI and artist workflow must be exercised end to end.

## Release principle

Do not call the current workflow production-ready until every item below has either passed or been explicitly deferred with a documented reason.

For each manual checklist row, record the tested build/commit and any failure notes so visual acceptance is reproducible rather than anecdotal.

The critical product contract is:

> An artist can generate or import an asset, move through modeling/rigging/animation/components/export, leave Asset Assistant to edit directly in Blender at any time, return without losing control, and export a technically valid result.

## 1. Semantic model quality — production blocker

The semantic layer is **not yet production quality**.

Before production readiness:

- [ ] Audit Human semantic modeling controls for quality, predictability, and deformation safety.
- [ ] Audit semantic animation controls for quality, predictability, and preservation of artist edits.
- [ ] Semantic changes must preview clearly before destructive application where practical.
- [ ] Semantic editing must distinguish generated source parameters from measurements inferred from imported/artist-edited geometry.
- [ ] Imported artist geometry must never be presented as though its original generator parameters are known.
- [ ] Test semantic changes after manual Blender edits rather than only on pristine generated assets.
- [ ] Confirm semantic operations preserve protected/artist-authored rig, mesh, material, animation, NLA, and component state unless the artist explicitly chooses otherwise.

### Static semantic proof

The Box provider is the required first static semantic proof:

- [ ] Start from the generated Box.
- [ ] Use the semantic layer to turn the box into a recognizable rock/stone prop.
- [ ] Confirm the resulting object remains directly editable in Blender.
- [ ] Confirm static validation succeeds without requiring rig or animation state.
- [ ] Confirm the rock exports successfully to each applicable static target.
- [ ] Confirm editable checkpoint save/reopen preserves the result.

This proof should demonstrate that semantic editing is useful beyond characters and does not assume a rigged workflow.

## 2. Import matrix — full UI walkthrough required

Every supported base-asset import path must be manually exercised through the **same complete Asset Assistant workflow**, not merely checked for successful file parsing.

Supported pre-release import matrix:

| Format | Import | Current Asset | Modify | Rig access | Animate | Components | Validate | Checkpoint | Re-export |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `.blend` | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| `.glb` | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| `.gltf` | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Unity-style `.fbx` | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Unreal-style `.fbx` | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

For every row confirm:

- [ ] Import creates/assigns one stable Asset Assistant working asset.
- [ ] Meshes are discoverable independent of selected child object.
- [ ] Existing base rig is discoverable and accessible when present.
- [ ] Existing animation clips are visible and usable when present.
- [ ] Materials survive import and remain artist editable.
- [ ] Modify gives appropriate generated or imported-asset behavior instead of provider errors.
- [ ] Components can be added/managed without reclassifying base geometry.
- [ ] Validation consumes the complete normalized asset boundary.
- [ ] Editable checkpoint save/reopen restores the same current asset.
- [ ] Re-export preserves the expected mesh/rig/material/animation result.
- [ ] Selecting a mesh, armature, Empty, or canonical root does not change the asset summary incorrectly.

The user should not need to understand importer-specific Blender hierarchy differences.

## 3. STL / Cura export — required manual proof

STL export remains a production gate even though STL **import** is post-launch scope.

- [ ] Export at least one generated Human current pose to STL.
- [ ] Export at least one static prop to STL.
- [ ] Confirm multiple valid closed shells do not fail merely because they are disconnected.
- [ ] Confirm genuinely open/non-manifold/zero-volume/self-intersecting geometry is blocked or clearly reported.
- [ ] Open the STL in Cura and confirm scale/orientation are correct.
- [ ] Slice successfully in Cura.
- [ ] Document any target-specific limitations or expected manual print preparation.

## 4. Rigging placement in the UI

Rigging should be treated as preparation for animation, not automatically as a peer top-level creative destination.

### Product question to resolve

The current design has Rig inside Create. Evaluate moving rig controls to the **top of the Animate workspace**.

Default direction:

`Animate -> Rig & Pose -> Clip Library -> Create / Edit Animation`

Reasons:

- Most rig interaction exists to make posing/animation possible.
- Imported characters may already have a rig and only need direct access to it.
- Static assets should not be visually pushed toward rigging.
- Combining rig + animation reduces navigation friction during iterative pose/animation work.

Keep rigging separate only if a concrete non-animation workflow requires it, such as rig-dependent deformation/attachment work that is confusing when hidden under Animate.

Before changing navigation:

- [ ] Audit Components workflows that require a base rig or bone attachment.
- [ ] Audit weight-paint/deformation workflows.
- [ ] Confirm rig access remains obvious for artists who need to adjust armatures before creating clips.
- [ ] Test the proposed layout in Blender before deleting the existing entry point.

## 5. Export workspace hierarchy

The primary save/export actions currently become visually lost below validation output.

Required UX change:

- [ ] Put **Save Editable Checkpoint** and **Export Asset** near the top of the Export workspace.
- [ ] Keep validation status directly associated with those actions.
- [ ] If export is blocked, leave the action visible but disabled with a concise reason rather than making the user search below a long validation list.
- [ ] Keep **Run Validation** obvious and nearby.
- [ ] Detailed validation results should appear below the primary action area.

Suggested hierarchy:

1. Destination / asset use
2. Save Editable Checkpoint + Export Asset
3. Readiness summary + Run Validation
4. Detailed validation results
5. Target-specific notes/options

The user should always be able to see where the workflow is headed even when validation returns many rows.

## 6. Static asset workflow

Static assets are first-class assets, not degraded characters.

- [ ] Generate a static provider asset.
- [ ] Modify it semantically.
- [ ] Manually model/sculpt/edit it in Blender.
- [ ] Add optional components where appropriate.
- [ ] Validate without rig/animation requirements.
- [ ] Save/reopen editable checkpoint.
- [ ] Export to Godot/Unity/Unreal static-compatible output where applicable.
- [ ] Export to STL/Cura.
- [ ] Import a static GLB/FBX/`.blend` and repeat the applicable workflow.

UI copy must never tell a static artist to add a rig simply because the generic workflow contains rig support.

## 7. Artist-control continuity — production requirement

Asset Assistant must automate operations without monopolizing the Blender asset.

At any reasonable point in the workflow, an artist must be able to leave the add-on UI and use Blender normally.

Required manual-edit proofs:

- [ ] Stretch/scale/model the mesh manually.
- [ ] Move vertices in Edit Mode.
- [ ] Sculpt the mesh.
- [ ] Adjust armature bones/rig structure where supported.
- [ ] Weight-paint or adjust deformation.
- [ ] Edit imported/generated animation keyframes in Dope Sheet/Graph Editor.
- [ ] Add or adjust NLA state.
- [ ] Adjust materials.
- [ ] Return to Asset Assistant and refresh/reinspect the current state without silent regeneration.
- [ ] Validate and export the artist-edited result.

### Ownership rule

Asset Assistant metadata describes what it may safely manage; it must not be treated as authority to overwrite newer artist-authored Blender state.

Generated and artist-owned portions may coexist in one asset. Examples:

- generated base mesh + artist-adjusted rig;
- imported base character + Asset Assistant-generated hair;
- imported rig + imported animation + generated accessory;
- artist-sculpted mesh + Asset Assistant-managed export preparation.

Future semantic operations should support explicit protection/locking of artist-owned areas where useful, but the immediate requirement is that ordinary Blender edits do not make the workflow unusable.

## 8. Animation artist control

- [ ] Imported clips can be selected and previewed.
- [ ] Generated clips can be edited directly in Blender.
- [ ] Artist keyframe edits survive switching clips, checkpoint save/reopen, and export.
- [ ] Imported Actions remain artist-owned unless explicitly converted to an Asset Assistant-owned/generated clip.
- [ ] Rename/remove behavior remains ownership-safe.
- [ ] Semantic animation refinement proposes understandable changes and does not silently destroy detailed curve edits.
- [ ] Rig access is available from the same working context used to animate.

## 9. Manual UI acceptance pass

Do not collapse this into one generic “UI looks good” checkbox. Test each workspace with generated, imported-rigged, imported-static, and manually edited assets where applicable.

- [ ] Create / Generate
- [ ] Import Asset File
- [ ] Modify
- [ ] Rig / Pose (or future Animate-top location)
- [ ] Animate / Clip Library
- [ ] Components
- [ ] Export
- [ ] Validation output
- [ ] Save Editable Checkpoint
- [ ] Reopen / continue

For each, check functionality, discoverability, wording, spacing, disabled states, and ability to recover from manual Blender edits.

## 10. Exit criteria

Production/public-alpha consideration requires:

- [ ] Semantic model quality accepted for intended alpha scope.
- [ ] Semantic animation quality accepted for intended alpha scope.
- [ ] Every supported import format passes the end-to-end matrix.
- [ ] STL/Cura export manually verified.
- [ ] Static model workflow passes, including the Box-to-rock semantic proof.
- [ ] Rig/Animate information architecture decision completed and visually tested.
- [ ] Export primary actions remain visible above detailed validation output.
- [ ] Artist manual-edit continuity passes for modeling/sculpting/rigging/animation.
- [ ] Documentation matches actual behavior.
- [ ] Automated CI remains green.
- [ ] Explicit release approval is given.

Until these are satisfied, the project should be described as **production hardening / pre-release**, not production ready.
