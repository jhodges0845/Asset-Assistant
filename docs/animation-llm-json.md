# LLM animation JSON round trip

Asset Assistant can export a portable description of the current asset, rig, rest pose, and optional active animation. An LLM can use that context to author a new animation JSON file that Asset Assistant validates and converts into a new Blender Action.

The workflow is:

1. In **Animate**, activate a reference clip if desired.
2. Click **Export Context JSON**.
3. Send the file to an LLM with an animation request such as `Create a polished confident idle` or `Create a more urgent version of this run`.
4. Ask the LLM to return JSON using `asset_assistant.animation.v1`.
5. Click **Import Animation JSON**. Import validates only; it does not modify the rig.
6. Review the validation summary.
7. Click **Create Loaded Animation** to create a new Blender Action.

The source clip is never overwritten by this workflow.

## Returned animation schema

A minimal LLM response looks like this:

```json
{
  "schema": "asset_assistant.animation.v1",
  "target": {
    "rig_signature": "copy the signature from the exported context"
  },
  "clip": {
    "name": "Confident Idle",
    "fps": 24,
    "looping": true
  },
  "notes": "Subtle breathing, shoulders back, small weight shift.",
  "keyframes": [
    {
      "frame": 1,
      "bones": {
        "Hips": {
          "location": [0, 0, 0],
          "rotation_quaternion": [1, 0, 0, 0]
        }
      }
    },
    {
      "frame": 24,
      "bones": {
        "Hips": {
          "location": [0, 0, 0.01],
          "rotation_quaternion": [0.9998, 0.01, 0, 0]
        }
      }
    }
  ]
}
```

Supported per-bone channels are `location`, `scale`, `rotation_quaternion`, `rotation_euler`, and `rotation_axis_angle`. Bone names must match the exported rig exactly. The importer rejects incompatible rig signatures, missing bones, malformed transforms, non-finite values, and extreme values. Asset Assistant does not silently retarget a response to another skeleton.

The exported context includes the rig hierarchy, rest-pose matrices, heads/tails, unit and axis conventions, FPS, and optional sampled key poses from the currently active reference Action. This is intentionally portable JSON rather than a dump of Blender implementation details.