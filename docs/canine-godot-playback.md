# Canine Godot playback probe

Validated October 10, 2026 with Blender 5.2.1 and Godot 4.7.2.
This is headless skeletal playback evidence, not rendered skin, material,
collision, performance, or visual acceptance.

## Reproduce

Use a fresh output directory for each fixture. From the repository root:

```powershell
& <blender.exe> --background --factory-startup --python-exit-code 1 --python scripts/export_canine_godot_review.py -- --sample default --output artifacts/shared-anatomy/godot-review-default
& <godot_console.exe> --headless --path artifacts/shared-anatomy/godot-review-default --script review.gd
```

Repeat with `--sample contrasting` and `--sample short-wide`, each at a fresh
path. The exporter writes `canine.glb`, `expected.json`, a minimal Godot project,
and a copy of `scripts/review_canine_godot.gd`. Godot writes `godot-report.json`
and returns a nonzero exit status for a mismatch. The Blender fixture builder
is intended for a fresh background process; it creates a review scene.

The probe imports through `GLTFDocument`, compares all 19 bone heads against
Blender world-space poses after conversion to Godot axes, and exercises
Walk -> Idle -> Run -> Idle. Each clip has 34 phases evaluated at three cycle
offsets. It checks durations and a 0.002 cm positional tolerance. Looping is
explicitly enabled in the probe; imported clips initially have looping off.

## Import settings matter

The probe uses `generate_scene(state, 800.0, false, false)`: 800 fps diagnostic
resampling, no trimming, and no removal of constant tracks. This high sampling
rate measures source fidelity; it is **not** a production memory/performance
recommendation. A shipping import preset remains to be evaluated.
The API parameters are documented in
[Godot GLTFDocument](https://docs.godotengine.org/en/stable/classes/class_gltfdocument.html#class-gltfdocument-method-generate-scene).

Controlled default-shape runs show why these settings are explicit:

| Configuration | Maximum sampled bone-head error |
| --- | --- |
| 800 fps, retain constant tracks | Walk 0.00106 cm; Run below 0.000037 cm |
| 30 fps, retain constant tracks | Walk 0.1122 cm; Run 0.1822 cm |
| 800 fps, remove constant tracks | Idle after gait up to 12.52 cm |

Removing constant tracks discards reset channels used during clip switching.
To reproduce these failures, append `-- --bake-fps=30` or
`-- --remove-immutable` to the Godot command. Failure reports are diagnostic
results, not acceptance passes. Each run replaces `godot-report.json`.

At the diagnostic settings, maximum errors across Walk/Idle/Run/Idle are
0.00106 cm (default), 0.000758 cm (contrasting), and 0.000277 cm (short-wide).
Reports are under `artifacts/shared-anatomy/godot-final-{sample}/`.
Controlled failure reports are `godot-default-30fps.json` and
`godot-default-pruned.json` in the parent directory.

## Export timing correction

The probe exposed nonzero GLB start timestamps: a Walk authored at frame 1
imported as 1.24167 seconds instead of 1.2 seconds at 24 fps. The authored
GLB/glTF export path now stages zero-based copies of generated Actions and
removes them afterward. Source keys, handles, active Action and slot remain
unchanged, including when export fails. The nonzero-start regression uses
frame 37 and checks the actual GLB time-accessor bounds, not only key span.
Constrained exports retain their existing baking path.

## Still open

Rendered skin/contact and visual playback in Godot, a practical shipping import
preset, and complete multi-view motion acceptance remain open. Bone-head parity
does not prove distal orientation, skinned-surface contact, or visual quality.
The short-wide shape is a stress case with a flattened torso, not an accepted
canine design.
