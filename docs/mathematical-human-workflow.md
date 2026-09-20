# Mathematical Human: reproducible study workflow

This is an opt-in, fully mathematical anatomical study. It uses no imported base
mesh, no downloaded anatomical asset, and no voxel-union construction. It is NOT
a claim of finished realism, Maxine likeness, animation readiness, or production UVs.

## Run, without inventing geometry

From the repository in PowerShell:

```powershell
.\scripts\build_surface_human.ps1
```

The wrapper verifies Blender 5.2.1, generates into a new timestamped folder under
`outputs/human-runs/`, then reopens the blend and compares the saved mesh against
the resolved preset. Use `-Output 'C:\...\new-folder'` to choose a destination.
The output folder must be empty. `-NoRender` skips images but still validates.
Pass `-Blender` if the installed executable is elsewhere.

Direct Blender command:

```powershell
& 'C:\Users\Jason\AppData\Local\Programs\Blender\blender-5.2.1-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/build_surface_human.py -- --preset presets/human/maxine.json --output outputs/my-new-human-run
```

This runs in a separate background process. It does not rebuild an artist's open
scene. Existing output requires an explicit `--overwrite`; routine runs should
use a new directory. No dependency installation or network access is needed.

## Stable controls

Copy `presets/human/maxine.json` before experimenting. Change only its parameters.
Unknown keys, unsupported versions, booleans, nonfinite numbers and out-of-range
values fail rather than being silently reinterpreted.

| Parameter | Default | Allowed range | Meaning |
| --- | --- | --- | --- |
| height_cm | 175 | 150–200 | Ground-to-crown height |
| shoulder_scale | 1 | 0.85–1.15 | Shoulder breadth and arm-root placement |
| waist_scale | 1 | 0.85–1.15 | Local waist breadth |
| hip_scale | 1 | 0.85–1.15 | Pelvic breadth and thigh-root breadth |
| chest_fullness | 0.55 | 0–1 | Continuous anterior chest relief |
| muscle_definition | 0.45 | 0–1 | Restrained clavicle, torso and leg relief |

Ranges limit exploration; the geometric audit is still authoritative for each
combination. These are shape controls, not clinical measurements or weight/age
estimates. The preset is reference-inspired, not image reconstruction.

## Outputs and acceptance

- `character.blend`: one editable body in Character; linked copies in Four view review.
- `character.png`: three-quarter study.
- `review.png`: front, three-quarter, side and back, in that order.
- `resolved_preset.json`: exact parameters used.
- `render_report.json`: dimensions and sampled contrast; blank previews fail generation.
- `generation_report.json`: generator version, geometry hash, structural checks,
  detected nonadjacent control-triangle intersections, and explicit unchecked items.

A passing build means finite geometry, one component, closed edges, consistent
winding, no zero-area faces and no detected intersections between nonadjacent
control triangles. It does not certify the subdivided surface, neighboring-face
foldovers, deformation, sculptural quality, identity, or UVs. The hash identifies
the generated control mesh; it is not an image similarity score.

Current quality remains `experimental_anatomical_study`. Review all four views.
Do not replace the rigged Human provider or declare this production-ready simply
because tests pass. There is no rig, no facial expression system, no skin texture,
and no production UV layout. The existing Human rig assumes different topology.

## What changed and why

The earlier Maxine experiment unioned ellipsoids and lofts. It proved that bpy
could generate/save a model but left disconnected-looking masses and weak anatomy.
The current study uses continuous profile surfaces, explicit shoulder windows,
a bilateral pelvic saddle, and topologically connected hands and feet.
Profile interpolation preserves monotonic segments rather than introducing
overshoot. Source anatomy is defined before display subdivision.

An independent bug in the existing full Human pelvis was corrected: indices
0..7 were treated as a left-side half-ring, although x=cos(angle) places that
half on the front. The corrected split uses indices 12..4 and 4..12. Existing
manifold checks missed the twist; a new geometric regression checks that outer
pelvis bands do not cross the sagittal midline.

## Ownership

- `object_core/geometry/surface_human.py`: versioned mathematical construction.
- `object_core/providers/surface_human.py`: preset parsing and portable audit.
- `blender_adapter/surface_human_study.py`: Blender conversion, intersection check,
  preview scene, rendering and saving.
- `scripts/build_surface_human.py`: background-only orchestration.
- `scripts/build_surface_human.ps1`: version check, fresh run and saved-file verification.
- `scripts/verify_surface_human.py`: reopen verification against generator output.
- `tests/core/geometry/test_surface_human.py`: portable contract tests.

The study provider is callable in code but intentionally not registered as the
add-on's rigged Human replacement. No UI, rig, export or semantic compatibility
is implied. Existing local pelvis experiments were preserved.

## Next anatomy acceptance work

1. Shoulder/deltoid and axillary transitions must read as continuous anatomy.
2. Pelvis front, side and back must lose remaining broad patch transitions and
   develop convincing inguinal, sacral, gluteal and proximal-thigh organization.
3. Face needs anatomically resolved eyelids/eyes, nose wings, lips and ear folds;
   generic surface relief is not a finished face or a likeness.
4. Hands need proportion review and knuckle/nail detail; feet need separate toe
   articulation and refined heel/arch contour.
5. Only after shape acceptance: add deliberate UVs, rig/weights and deformation
   tests. Do not reuse the legacy rig without a topology mapping.

Use `docs/prompts/mathematical-human-operator.txt` for the base-model handoff.
Change one region per revision and retain identical cameras/materials for comparison.
Record whether a change improved the reference match; do not equate smoothing
with anatomy. Never lower validation thresholds to make a bad surface pass.

## Earlier reviewed checkpoint (2026-09-19)

`outputs/maxine-mathematical-cpu/` contains the earlier reviewed package.
The default control surface has 42,410 vertices and 42,754 faces, one connected
component, Euler characteristic 2, zero open/nonmanifold/inconsistent edges,
zero degenerate faces, and zero detected nonadjacent control-triangle intersections.
It is symmetric and 175 cm tall. The operator wrapper also generated and reopened
an independent copy successfully. The displayed shoulder and pelvic transitions
still need visual refinement; do not label this realistic or reference-matched.

A stale context index initially described the older deformable pipeline rather
than the current anatomical provider. Its call-chain pointers were corrected.
Normal shell tools failed with a sandbox helper setup-refresh error; approved
execution outside that helper worked. This is an environment issue, not a need
for special Blender packages or alternative anatomy code.

Preview rendering uses Cycles on the CPU (16 samples, denoising, 8 threads).
Pixel inspection reads the buffer once; a blank/uniform image fails generation.

## Pelvis experiment and portable provenance

See `docs/mathematical-human-development.md` for the formulas, comparison, and
visual rejection of the remaining pelvis shelves. The latest experiment has
43,082 vertices and 43,426 faces, but is still not realistic.
New packages contain `source_snapshot/` with the exact generator and SHA-256
manifest. The wrapper verifies using that snapshot. To regenerate later, run
`source_snapshot/scripts/build_surface_human.ps1` with a fresh output folder.
The snapshot preset defaults to the selected preset from its originating run.

## Current seam-correction checkpoint (2026-09-19)

`outputs/maxine-pelvis-faired/` is the newer pelvis seam experiment: 42,186
vertices and 42,530 faces. The raised merge region, rounded transverse panels,
and bounded local fairing replace the rejected angular patch. The three-quarter
render removes the conspicuous front shelf. Completed four-view review and validation
are recorded in the package CHECKPOINT.md; this is not realistic likeness acceptance.
Use the package source_snapshot runner to reproduce this exact revision. Earlier
42,410/43,082-vertex checkpoints are historical and topology-incompatible.

Current integration: Mathematical Human is now a separate static plugin option. See docs/mathematical-human-plugin.md. Earlier statements about being unregistered describe historical study checkpoints. The original rigged Human is unchanged.
