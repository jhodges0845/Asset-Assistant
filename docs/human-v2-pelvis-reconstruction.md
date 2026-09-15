# Human V2 anatomical pelvis reconstruction

The post-#279 clay, silhouette and wireframe review established that contour tuning had reached its limit. An independent game-character topology review reached the same conclusion: the lower body must stop behaving like a torso ring converted into two leg tubes.

## Construction rule

Human V2 treats the pelvis as a semantic anatomical region. The constructor derives surface intent from stable landmarks such as iliac crest, greater trochanter, pubic/crotch region and glute mass. Rings may remain temporarily as compatibility boundaries during migration, but they are no longer the source of anatomical intent.

The first reconstruction slice introduces explicit longitudinal paths for outer hip, rear/glute and inner-thigh/crotch flow. These paths are intentionally independent of mesh connectivity so the next slice can replace the conversion band without rediscovering anatomy from ring indices.

## Migration

1. Establish a bilateral pelvis landmark field and tests.
2. Drive lower-pelvis surface placement from those landmarks.
3. Establish explicit outer-hip, rear/glute and inner-thigh longitudinal paths.
4. Replace the remaining pair-of-pants conversion band with topology that follows those paths.
5. Prefer quad-dominant authoring topology through deformation regions; triangulation belongs downstream where possible.
6. Preserve manifold/orientation, printable-solid, symmetry, UV and provider/semantic workflow gates throughout.

## Visual gate

Before leaving the pelvis, clay/silhouette/wireframe must show no skirt/belt shelf, no abrupt horizontal thigh-root break, a continuous rear glute-to-thigh curve, a believable inner-thigh/crotch origin, and longitudinal wire flow through the pelvis.
