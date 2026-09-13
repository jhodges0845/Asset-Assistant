# Artist Control Contract

Asset Assistant is an assistant inside Blender, not a replacement for Blender and not an owner of the artist's entire asset.

This document defines the artist-control behavior that production workflows must preserve.

## Core rule

> Asset Assistant may automate a declared operation, but the artist remains free to edit the Blender asset directly before, during, and after that operation.

The add-on must treat manual Blender edits as legitimate workflow state, not as corruption merely because the result differs from generated defaults.

## Artist may leave the Asset Assistant UI at any time

An artist should be able to:

- model/stretch/scale geometry;
- enter Edit Mode and move vertices;
- sculpt;
- adjust UVs/materials;
- adjust armatures;
- pose bones;
- weight-paint;
- edit Actions in the Dope Sheet/Graph Editor;
- use NLA;
- create ordinary Blender objects and collections;
- return to Asset Assistant and continue.

Asset Assistant should re-inspect current Blender state when needed instead of silently restoring an older generated assumption.

## Ownership is granular

Ownership applies to specific managed data, not to the whole file.

A single asset may contain all of the following at once:

- Asset Assistant-generated base geometry;
- artist-sculpted changes;
- imported armature;
- imported Actions;
- Asset Assistant-generated animation clips;
- artist-owned materials;
- generated Hair component;
- imported Clothing component;
- manually edited NLA tracks.

The system must preserve these boundaries.

## Generated vs imported vs artist-edited state

### Generated

Asset Assistant may safely regenerate data only when the workflow explicitly identifies that data as reproducible and owned by Asset Assistant.

### Imported

Imported geometry, rigs, materials, weights, Actions, curves, drivers, and NLA are artist-authored by default. Importing a file into Asset Assistant makes it a working asset; it does not automatically transfer destructive ownership of the imported content.

### Artist-edited generated data

Once an artist manually changes generated data, later automation should be conservative. The product should prefer one of these outcomes:

1. preserve the edit;
2. preview a proposed change and explain what would be replaced;
3. require explicit approval before regeneration;
4. block the operation if safe intent cannot be determined.

Silent replacement is not acceptable.

## Semantic editing contract

Semantic editing should follow:

`Inspect -> Understand -> Propose -> Preview -> Apply`

For generated assets, semantic controls may map to known provider parameters.

For imported or manually reshaped assets, semantic controls must be derived from current geometry/rig state and must not pretend original generator values are known.

Examples of acceptable semantic concepts include height, shoulder width, limb proportions, silhouette, motion energy, forward lean, stride, breathing intensity, or other explainable characteristics.

The artist should be able to understand what a semantic command intends to change before applying it.

## Rig and animation control

Imported and generated rigs must remain normal Blender armatures.

Asset Assistant may provide convenience actions such as Select Rig, Pose Rig, inspect deformation, or create a clip, but it must not prevent the artist from using Blender's standard rigging and animation tools.

For animation:

- generated clips remain editable Actions;
- imported clips remain artist-owned unless explicitly converted;
- manual keyframe edits must survive clip switching, checkpoint save/reopen, and export;
- removing an imported clip from Asset Assistant must not delete the artist Action;
- semantic animation edits must preserve or explicitly replace artist changes, never silently overwrite them.

## Static assets

The artist-control contract applies equally to static props.

A static asset may be modeled/sculpted freely, use semantic shape assistance, receive components/material changes, validate, checkpoint, and export without ever acquiring a rig.

Static assets are not incomplete characters.

## Components

Components are independently managed pieces. Adding an Asset Assistant-managed Hair or Accessory component must not grant permission to rewrite the imported/generated base asset.

Likewise, artist-authored components remain artist-owned except for explicit metadata/attachment management the artist approves.

## Recovery after manual edits

Where Asset Assistant caches measurements, provider values, validation state, or semantic inspection results, the workflow needs a clear refresh/reinspect path.

A refresh must:

- inspect current Blender state;
- update derived information;
- preserve artist data;
- invalidate stale validation/preview assumptions;
- explain conflicts rather than silently correcting them.

## Future protection controls

A later enhancement may expose explicit protection/locking, for example:

- protect face geometry;
- protect rig;
- protect an animation clip;
- allow Hair regeneration;
- allow material preparation.

This is useful but not required to satisfy the immediate artist-control contract. The immediate production requirement is that ordinary Blender edits remain compatible with the workflow.

## Production acceptance

The contract is not accepted merely because ownership metadata exists in code. It must be manually demonstrated in Blender by editing mesh, sculpt, rig, weights, animation, and materials, then successfully returning to Asset Assistant for validation/checkpoint/export without unintended replacement.
