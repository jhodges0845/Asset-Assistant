# Generated animation

Asset Assistant keeps animation intent host-independent. Providers return immutable sampled rotation tracks in seconds/radians around axes expressed in rest-armature coordinates. The Blender adapter translates those samples into editable quaternion action curves, converts seconds using FPS / FPS Base, adds Cycles modifiers for looping clips, and preserves generated actions with a fake user.

## Clip selection

The Animate workspace exposes a clip selector. Supported providers can generate separate editable Blender actions according to their declared capabilities. Human and Quadruped currently expose Idle/Walk/Run; Avian exposes Idle/Flight. A generated clip is created once; selecting it again activates the existing action instead of rebuilding or overwriting its keys. This lets an artist keep edits to one generated clip while switching to another.

Only one action is active on the rig at a time for editing and preview. Inactive generated actions remain saved with the Blender file through fake users. Export is different: engine adapters can package the generated clip library without permanently changing the `.blend` file. Temporary export state is always restored after writing.

Artist-authored actions are never replaced by generated clips. Existing NLA tracks, drivers, constraints, and manual non-rest poses remain preservation boundaries that require deliberate artist preparation.

## Idle

The idle generator produces a closed provider-defined resting cycle while leaving locomotion roots stable. In Blender, generate a model, add its basic rig, choose Idle in the Animate workspace, set cycle duration and motion strength, and generate the clip. Preview Motion Pose shows the middle of the active clip without playback.

## Human locomotion

Human exposes portable in-place Walk and Run cycles in addition to Idle. Walk uses opposing upper-leg and upper-arm swing, lower-leg motion, and a small torso counter-rotation. Run uses a faster flight/contact rhythm with stronger limb articulation and a small forward torso pitch. Both are deliberately in-place game-animation foundations rather than root-motion navigation. The core cycles are deterministic, closed, strength-scalable, and independent of Blender.

The Blender adapter translates generated motion through the same shared clip-to-action path and creates editable `.Walk` and `.Run` actions. Direct Blender integration coverage verifies cyclic action curves, clip coexistence and switching without overwriting generated keys, and preservation of artist animation.

The Human Run received an initial anatomy correction pass for knee and elbow bend direction. Its remaining work is motion-quality polish—particularly upper-arm swing, knee lift, torso pitch, timing, and phase—not a missing pipeline capability.

Generated actions are self-contained poses: each clip owns rotation data for every generated rig bone rather than relying on transforms left by a previously evaluated clip. This prevents cross-clip pose contamination during switching and per-clip export.

## Quadruped locomotion

Quadruped exposes Idle, Walk, and Run through provider-specific four-legged gait generation with spine, neck, and tail follow-through. The implementation lives entirely under the canonical Quadruped provider and uses the same generic Blender clip workflow as Human.

## Avian locomotion

Avian exposes Idle and Flight. Flight is a closed in-place wingbeat cycle with symmetric upper-wing drive, lower-wing follow-through, subtle spine/neck motion, and tail stabilization. Those motion rules live in the Avian provider rather than shared Blender code.

The shared locomotion path supports a provider-defined artist-facing clip name. `Walk` remains the default for existing locomotion providers; Avian declares `Flight`. Blender therefore creates and exports an actual `Flight` action rather than hiding Avian motion behind a Walk label. Automated Blender coverage verifies that Idle and Flight coexist as separate actions and that non-Avian providers do not accidentally gain Flight support.

## Export behavior

Animated engine export treats Asset Assistant-generated actions as a clip library, but packaging is destination-specific.

Godot GLB/glTF exports all generated clips in one file. Current Blender uses Actions mode while older Blender relies on the temporary one-strip-per-action NLA organization. Unity FBX also keeps the generated clips together in one FBX as separate animation stacks; `bake_anim_use_all_actions` remains disabled so unrelated compatible actions are not broadcast into the export.

Unreal uses a different packaging strategy because its skeletal-animation import workflow is more reliable with one animation per FBX. Choosing an Unreal output such as `Human_Unreal.fbx` creates the main skeletal mesh/skeleton/material FBX plus adjacent clip files such as `Human_Unreal_Idle.fbx`, `Human_Unreal_Walk.fbx`, and `Human_Unreal_Run.fbx` when those generated clips exist. The same naming logic applies to provider-specific clips such as Avian `Flight`.

For Unreal 5.8 Interchange compatibility, each animation sidecar retains the recognizable skinned mesh + armature hierarchy while activating exactly one generated action. Texture embedding is disabled for the sidecars. In Unreal, import the main FBX first, then import each sidecar with **Import Only Animations** against the skeleton created by the model import. That destination workflow creates the animation sequences without duplicating the render asset, while giving Interchange enough hierarchy to classify the FBX correctly. Unity's working multi-clip FBX behavior is intentionally unchanged.

All temporary selection, active-action, playback-range, and export state is restored after export. Existing artist NLA tracks and drivers remain preservation boundaries rather than being silently reorganized.

Representative automated Avian export coverage checks that Godot GLB contains the skinned mesh plus Idle/Flight animations and that Unity FBX contains Avian skinning data plus both clip names. These checks prove file packaging, not full destination playback certification.

## Preservation and validation

Generated animation refuses to overwrite artist actions, NLA tracks, drivers, constraints, or non-rest poses. Generated Asset Assistant clips can coexist on the same rig and can be switched explicitly. Removing the add-on preserves the actions and keyframes.

Provider declaration validation treats `supports_run` like the other animation capabilities: it must be boolean, it requires rig support, and a provider declaring it must implement `run(duration, strength)`. `supports_locomotion` remains the generic capability; a provider may optionally supply `locomotion_label` to present a more accurate artist-facing name without moving anatomy-specific motion into shared workflow code.

Validation checks changing unmuted curves, missing targets, non-finite values, Rest Position, zero action influence, and exporter-specific animation restrictions. A successful Blender action or file write is not destination certification; destination import and playback remain separate evidence.
