# Mathematical Human in Asset Assistant

Install the ZIP built by `python -m scripts.build_blender_addon` using Blender
5.2.1. In Asset Assistant > Create > Generate, choose Mathematical Human. Tune
height, shoulder/hip widths; Advanced Options contains waist, chest, and muscle
controls. Generate uses the existing create/replace workflow. Invalid geometry
fails before replacing the current asset. This is a static experimental asset:
no generated rig, animation, or UV layout. Create > Human now uses the same surface with a rig and the existing plugin workflows; see [integration status](visual-testing-integration.md).

The plugin, standalone builder, and visual-review scripts use the same core
surface generator. Plugin creation uses the same control-triangle intersection
gate as standalone studies. It preserves scene units, cursor placement, asset
ownership, saved parameters, and smooth subdivision display. Source snapshots
and detailed Blender reports remain available through build_surface_human.ps1.

## Visual testing

Run Blender in background with `--python-exit-code 1 --python
scripts/render_human_review.py -- --provider human_surface_study --height-cm 175
--output surface_review.png`. This produces clay, silhouette, and wireframe
four-view sheets. Weight/body-type arguments belong only to the rigged Human;
use the strict Maxine preset/standalone runner for all six study controls.
GitHub Tests runs on main and visual-testing and uploads review sheets as the
mathematical-human-review artifact. A rendered image is not automatic likeness
approval. Inspect seams, silhouette, face, and hands against the reference.

## Validation and limitations

Tests cover generated geometry, bounded pelvis fairing, plugin/provider agreement,
scene units, disabled rigging, preservation after failed generation, and isolated
release ZIP generation. The static study does not create a rig; the Human provider uses surface-specific rest landmarks.
Subdivision intersections, production UVs, deformation, and reference likeness
remain unverified. See mathematical-human-development.md for the geometry record.

Clay/silhouette use the same smooth subdivision display as plugin generation. Wireframe deliberately shows the authored control mesh, with subdivision disabled.

## Integration validation (2026-09-19)

336 core tests passed; core coverage 95% (required 90%). The full 230-test Blender
run exposed an old provider-list expectation and missing backwards-compatible
review defaults. After correction all 11 tests in the affected adapter, camera,
and new surface modules passed, along with the Create UI draw check. Isolated
release ZIP generation and real plugin save/reopen passed. All three visual modes
rendered, and front/back orientation was checked against the study's +Y forward
axis. CI reruns the complete suite on both published branches.
