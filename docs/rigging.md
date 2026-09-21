# Rigging

In **Animate > Rig & Pose**, choose **Add Basic Rig** for a generated Human.
The operator reads the current asset's provider and saved dimensions. An existing
rig is preserved; use Enter Pose Mode to work with it. Rigging requires Object Mode.

## Human implementation

`HumanProvider` (`human`) owns the plugin's single Human path. Its mathematical
surface and skeleton share the same body-control mapping. The rest skeleton uses
16 bones with stable animation names. `rigging/surface_human.py` owns the surface
landmarks; `rigging/deforming.py` owns the common deterministic weighting algorithm.

The surface builder supplies authored arm indices. Human passes a bone filter to
the weighting algorithm so hand/forearm bones cannot pull adjacent hip vertices.
Arms use their own side's arm chain and torso; body vertices exclude distal-arm
weights. Topology-preserving Modify retains these memberships. Modified meshes
recompute weights instead of reusing a base-mesh cache.

The Blender adapter in `workflow.py` resolves saved parameters, requests the
provider skeleton/weights, and calls `rigging.py` to create armature modifiers and
vertex groups. Core geometry and rigging never import Blender. Low-level rigid
blockout helpers remain internal test fixtures, not another Human product path.

## Quality and validation

Core tests protect skeleton structure, normalized weights and region isolation.
Blender tests verify deformation, provider recognition, generated actions and
save/reopen. The review harness renders neutral, shoulder, elbow, wrist, hip,
knee, ankle and neck poses, with projection and movement checks. CI publishes
these images; inspect them for pinching, joint volume and motion quality.

Passing tests does not establish production anatomical or animation quality.
Generated scene data remains ordinary editable Blender data after disabling the
plugin. See [Human workflow](human-workflow.md) and [animation](animation.md).
