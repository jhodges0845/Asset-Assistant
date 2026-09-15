# Human V2 pelvis topology ownership

The pelvis is a shared anatomical region, not a torso cap plus two independent leg attachments.

## Ownership

`object_core.geometry.anatomical_pelvis` owns the neutral construction profiles that must agree across the lower torso and both upper thighs:

- iliac/lateral hip width,
- groin descent,
- rear gluteal projection,
- the fade from pelvic volume into the upper thigh.

`anatomical_human` consumes those profiles while retaining responsibility for connected mesh assembly, manifold seams, the rest of the leg, arms, head, UVs, and final face orientation.

This boundary is intentionally Human-specific. Generic deformable geometry remains generic.

## Migration rule

Do not add another post-generation pelvis refinement layer. If the diagnostic wireframe still shows the pelvis behaving like a torso ring with two radial leg fans, the next topology change must replace that assembly seam with a coordinated pelvis/dual-leg opening patch. The profile module is the source of shape truth for that patch; it is not a substitute for the patch.

## Acceptance

After each structural pelvis change, render clay, silhouette, and wireframe. The lower body is ready to move on only when:

1. the front/three-quarter view has continuous waist → hip → upper-thigh flow without a skirt-like shelf,
2. the side/back view has recognizable gluteal projection that blends into the thigh,
3. the groin reads as a bridge between two leg openings rather than a horizontal torso termination,
4. the wireframe no longer concentrates the entire pelvis-to-leg transition into two triangular radial fans,
5. manifold, symmetry, UV, grounding, deterministic-generation, Modify/JSON, rigging, ownership, and export contracts remain intact.
