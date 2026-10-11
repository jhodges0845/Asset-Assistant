# Canine Godot playback probe

Validated October 10, 2026 with Blender 5.2.1 and Godot 4.7.2.
Evidence now includes headless skeletal comparisons and four-view rendered
Godot frame sequences. Full visual acceptance, quantitative skinned-surface
contact, collision and production performance remain open.

## Reproduce

Use a fresh output directory for each fixture. From the repository root:

```powershell
& <blender.exe> --background --factory-startup --python-exit-code 1 --python scripts/export_canine_godot_review.py -- --sample default --output artifacts/shared-anatomy/godot-review-default
& <godot_console.exe> --headless --path artifacts/shared-anatomy/godot-review-default --script review.gd
```

Repeat with `--sample contrasting` and `--sample short-wide`, each at a fresh
path. The exporter writes `canine.glb`, `expected.json`, a minimal Godot project,
and the review, import and rendering scripts. Godot writes `godot-report.json`
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

## Source-grid candidate import

Fresh fixtures now record a verified uniform key grid for each clip. Run:

```powershell
& <godot_console.exe> --headless --path artifacts/shared-anatomy/godot-review-default --script review.gd -- --source-aligned
```

The review-only `scripts/canine_godot_import.gd` imports each clip using its
own authored spacing, then assembles the resulting animations into one
library. It retains constant reset tracks. Current canonical rates are
106.6667 fps for Walk, 200 fps for Run and 4 fps for Idle. This is deliberately
limited to generated clips whose key grid the fixture builder verifies; it
is not a general importer for artist-edited or irregularly keyed animation.

Across default, contrasting and short-wide shapes, the same three-cycle
Walk/Idle/Run/Idle comparison passes, with maximum bone-head errors below
0.000037 cm. The unique three-clip library contains 6,600 keys versus 112,200
at 800 fps (94.1% fewer): Walk 3,096, Run 3,096 and Idle 408. This measures key
count, not runtime memory or frame-rate performance. The 800 fps default
remains available as a diagnostic baseline. Reports are under
`artifacts/shared-anatomy/godot-grid-{sample}/`; the retained default baseline
and candidate comparison reports are `godot-grid-baseline-report.json` and
`godot-grid-default-report.json` in the parent directory.

## Rendered playback

Fresh fixture directories also include `render.gd`. Use a rendering-capable
Godot process, without `--headless`:

```powershell
& <godot_console.exe> --path artifacts/shared-anatomy/godot-review-default --script render.gd --rendering-method gl_compatibility --resolution 1600x600 -- --clip=Walk
```

Use `--clip=Run` for the trot. The helper uses the source-grid importer, keeps
the imported coat material, and captures front, three-quarter, side and back
views at 25 fps for three cycles. Output is `render-walk/` or `render-run/`,
with numbered PNGs and `render-report.json`. On this machine Godot used the
Compatibility renderer through ANGLE on AMD Radeon R7 graphics.

Default Walk (90 frames) and contrasting Run (48 frames) were rendered in
Godot 4.7.2. Frame 7 from each corrected four-view sequence was inspected:
the skin and coat render, and no detached limbs are apparent in those frames.
This does not establish full motion acceptance or numerical skin contact.
Local MP4 previews encoded from the frames with Blender's sequencer are
`godot-grid-default-walk.mp4` and `godot-grid-contrasting-run.mp4` under
`artifacts/shared-anatomy/`. The renderer and helper remain review tools,
not a production Godot project or importer integration.

## Export timing correction

The probe exposed nonzero GLB start timestamps: a Walk authored at frame 1
imported as 1.24167 seconds instead of 1.2 seconds at 24 fps. The authored
GLB/glTF export path now stages zero-based copies of generated Actions and
removes them afterward. Source keys, handles, active Action and slot remain
unchanged, including when export fails. The nonzero-start regression uses
frame 37 and checks the actual GLB time-accessor bounds, not only key span.
Constrained exports retain their existing baking path.

## Still open

Quantitative skinned-surface contact, complete visual playback review, and
production import/performance acceptance remain open. The source-grid mode is
a tested candidate, not yet a shipping importer integration. Bone-head parity
does not prove distal orientation, skinned-surface contact, or visual quality.
The short-wide shape is a stress case with a flattened torso, not an accepted
canine design.
