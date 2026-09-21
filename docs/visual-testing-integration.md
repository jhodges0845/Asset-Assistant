# Human V2 integration and visual review

## Current branch behavior (2026-09-20)

Create > Human (`human_experimental`) uses the mathematical surface through the
normal plugin asset workflow, with a deforming rig, materials, provisional face
atlas UVs, animation, semantic Modify and model JSON support. Mathematical Human
(`human_surface_study`) remains a separate static study with six strict controls.
The standalone neutral pelvis is an earlier experiment, not the active Human mesh.

The original surface integration reused mannequin landmarks: arms were too far
from the new arm centers and the old straight legs did not follow the surface's
splayed legs. `object_core/rigging/surface_human.py` now owns surface-version-specific
rest landmarks with the same bone names/parents used by existing animations.
Landmarks share the surface floor/crown normalization and the mesh's shape mapping.
Update these landmarks when changing the authored surface centerlines.

Human keeps its existing 120–240 cm height, 30–300 kg weight and body-type controls.
A validated 175 cm surface is cached, scaled to requested height, then shaped with
smoothly blended hip/waist/chest/shoulder/head ratios from the existing proportion
rules. The same mapping shapes bone endpoints. Weight/body type previously changed
only the rig; height outside the study's 150–200 cm range previously failed.
Mesh and skin caches now include every Human control. Modified meshes recompute
weights; immutable base meshes can reuse them. Semantic region height bounds use
the surface rig rather than the old mannequin landmarks.

## Deformation review

Run from the repository root:

```text
blender --background --factory-startup --python-exit-code 1 --python scripts/inspect_human_deformation.py
```

The output is `human_v2_deformation_review.png`: eight cards in a 1200x1800 sheet.
Rows vary in world Z because the camera looks along Y. The old Y-row layout stacked
poses in camera depth. Text faces the camera without the extra mirroring rotation.
Arms are shown from the front; hip, knee, ankle and neck use side views so bends
are visible. Framing includes evaluated mesh bounds and labels. The script rejects
clipped/overlapping cards, ineffective mesh poses and axial-only bone twists.
These checks establish a readable diagnostic, not anatomical quality approval.

## CI timing

Before this change, run 35515813039 took 3m28s: Blender integration 87s, mathematical
review 42s and deformation review 26s. Core coverage took 115s. Earlier mesh and
weight caches had already reduced runs from 11m40s / 7m to roughly 3–4m.

Tests now run visual rendering in a separate `Human visual review` job alongside
Blender integration, using the existing checksum-verified Blender runtime cache.
All four Python versions, the 90% coverage gate, save/reopen and packaged ZIP tests
remain. Superseded runs on the same branch/PR are cancelled. Both PNG artifacts
remain available on PRs and branch pushes. No path filters hide required checks.
This removes about 68s of rendering from the integration job's measured critical
path; actual GitHub timing depends on queueing/cache state and needs a new run.
The extra job repeats runner setup, trading some runner time for shorter feedback.

## Quality limits

The surface is experimental. Matching bone centers does not establish production
joint volume, extreme-pose quality, foot contact, facial rigging, hand articulation
or production UV quality. Inspect the generated cards and animated clips before
approving anatomy. Existing saved assets retain their current geometry/rig until
explicitly regenerated through the plugin; this change does not migrate artist work.

## Local verification

Blender 5.2.1: 231 integration tests passed, plus 2 focused Modify checks after the
semantic-bound update. The isolated release ZIP generated, rigged, animated,
validated and exported successfully. Static study and rigged Human/component
save/reopen checks passed. The corrected eight-pose sheet rendered and passed
projection/displacement checks; front/side card readability was visually inspected.
GitHub workflow syntax passed actionlint. The installable artifact is
`dist/asset_assistant.zip`; test logs are under `artifacts/visual-testing-validation/`.

Final core validation: 352 tests passed under coverage; total core coverage 95%
(required 90%). These are local results; the revised CI timing is not yet measured
on GitHub; confirm timing on the PR workflow run.

### Review artifact isolation fix

The initial layout test used placeholder cubes and attempted to mock a dynamic
Blender render operator. That did not prevent rendering, so the test overwrote
the human review PNG after visual inspection. Camera setup now performs no
rendering; the layout test calls `main(render=False)` and uses a temporary output
path with a sentinel to verify that existing output is preserved. The focused
Blender regression passes and the real Human sheet is regenerated afterward.

### Wrist/hip weight isolation and knee direction

The arms-down surface puts hands close to the hips. Distance-only candidate
selection assigned some body vertices to forearm/hand bones, producing the
reported hip protrusion when the wrist rotated. Surface generation now optionally
returns immutable authored arm vertex indices after final vertex remapping.
Human skinning restricts distal arm candidates to those indices and excludes leg
bones from the authored arms. Topology-preserving semantic edits keep this
ownership even when vertex positions change. The existing shared weighting and
normalization algorithm still computes the weights; other providers retain their
existing candidate selection. Unknown Human topology is rejected explicitly.

The review knee angle was also reversed: the lower leg now flexes backward along
the model's negative-Y direction. This changes the diagnostic pose, not animation
clips. A real Blender regression verifies that wrist motion moves no non-arm
vertex by more than one micrometer and that the knee's tail moves backward.

Follow-up validation: 353 core tests and both focused Blender review tests passed.
The updated sheet rendered successfully and was inspected after the tests:
the wrist hip protrusion is absent and the knee bends backward. The full 231-test
Blender result above predates this weight-isolation follow-up.

## Promotion to main

The promotion excludes the external `.visual-testing-trigger` marker and its
three committed `pelvis_review*.png` outputs. `scripts/render_pelvis_review.py`
is restored to main's manual standalone-pelvis renderer instead of the repurposed
automation entry point that ignored pelvis controls. Human review commands,
regression tests, the reviewed deformation sheet and GitHub CI artifacts remain.
No external automation configuration is changed by this repository cleanup.
