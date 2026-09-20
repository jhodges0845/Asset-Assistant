# Mathematical Human development record

## Authority and objective

The user requires anatomy generated entirely from mathematical surfaces. No base
mesh downloads, image-to-mesh replacements, or imported anatomical assets.
Target: the supplied adult Maxine reference. Current status: experimental study,
NOT accepted as realistic, reference-matched, rigged, or production-ready.
Read mathematical-human-workflow.md for commands and the operator prompt for
handoff instructions. This record explains decisions, evidence, and failures.

## 2026-09-19: pelvic transition experiment

Ownership: object_core/geometry/surface_pelvis.py owns the new transition and
local displacement fields. surface_human.py calls it only for this opt-in study.
The default Human provider and rig are not replaced.

Coordinates during construction are meters: X left/right, +Y anterior, Z up.
Final core output uses centimeters and is normalized to the requested height.
Torso and thigh boundaries each have 64 vertices. The lateral half-ring patches
now use eight longitudinal intervals. Their interpolation is cubic Hermite:
P(t)=(2t^3-3t^2+1)A+(t^3-2t^2+t)M0+(-2t^3+3t^2)B+(t^3-t^2)M1.
M0 follows the neighboring torso row; M1 is vertical at the thigh attachment.
Front/rear transition strips share endpoint indices with the lateral patches.
Only the first short strip uses pole triangles. The medial saddle has 16 columns.
Boundaries must share exact indices, not merely coincident positions.

Separate compact fields modify Y only. Kernel K= (1-t^2)^2 for |t|<1 and zero
outside, with t the normalized distance from the field center. This has zero
value and first derivative at its support boundary. Broad posterior displacement
peaks at 0.022 m before height scaling, with shallow fold/inguinal/pubis relief.
These are analytic proposals, not anatomical measurements inferred from the image.

Measured on the default control mesh in the 88-100 cm pelvis band:
- Previous generator: 42,410 vertices / 42,754 faces; maximum edge 9.498 cm.
- Longitudinal patch before relief: 43,082 / 43,426; maximum edge 4.432 cm.
- Relief retains the new topology. Shorter edges do not establish anatomical quality.

The anatomical-planes package generated and reopened successfully in Blender
5.2.1. Its geometry fingerprint is
c48b42ab0319cb8783e9ab82743b7cf8d8fb365dca663596c4a1103ad0962bc8.
Reopen maximum coordinate error: 0.00000596 cm. Core audit: closed, connected,
orientable, Euler 2; Blender found zero nonadjacent control-triangle intersections.
Subdivided surface intersections and animation behavior are NOT verified.

Visual verdict from the four-view render: NOT accepted as an anatomy improvement.
There remain conspicuous angular shelves across front/back pelvis, abrupt lateral
hip-to-thigh transitions, rectangular shoulder/axilla transitions, simplified face,
thin hands and undivided feet. Lighting also obscures surface detail. Preserve the
experiment for study; do not promote it as a realistic model or hide these faults.
Next geometry work should trace tangent continuity across pelvis patch boundaries,
inspect control cages and normals, and compare identical front/side/back cameras.
Adding more vertices or glute displacement alone did not solve the visible joins.

## Reproducibility lesson

An earlier longitudinal-patch run passed generation and rendering but FAILED its
reopen comparison because generator source was edited while rendering. Its saved
mesh predates the new fields. This was a workflow failure, not a successful check.
Never retrofit current source onto an older run and claim it generated that run.

New builds capture source_snapshot before generation, including core Python,
the Blender adapter, runners, documentation, and selected preset. SHA-256 hashes
are recorded in source_manifest.json. The wrapper reopens using the snapshot's
verifier and generator. Hash verification rejects modified snapshot source.
Freeze repository edits until capture/build finishes. Snapshots establish provenance,
not visual quality. Use a fresh output directory; preserve failed experiments.

## How another assistant should continue

1. Read the workflow, this record, and the operator prompt before editing.
2. Run the PowerShell wrapper with the supplied preset and fresh output folder.
3. Inspect generation/render reports and require successful saved-file verification.
4. Open review.png and evaluate shape against the reference; tests cannot do this.
5. Change one anatomical region, retain cameras/materials, and rerun relevant tests.
6. Record the hypothesis, equations, measured checks, visual verdict, and limits here.
7. Give the user absolute paths to the blend, preview, source, and documentation.

Source snapshots are the executable handoff; this journal is the reasoning handoff.
Do not ask a base model to reconstruct the generator from conversational memory.

## Packaged checkpoint validation

`outputs/maxine-pelvis-documented/` generated, rendered, and reopened successfully.
Running its archived PowerShell runner independently produced
`outputs/maxine-snapshot-reproduction/` with the identical geometry SHA-256 and
a successful reopen check. Ten focused geometry/provenance tests passed.
The symmetry regression was a decimal rounding tie; the test now compares actual
coordinate distances at the unchanged 1e-5 cm tolerance. No geometry was changed
to accommodate that numerical test issue.
`python -m unittest discover -s tests/core -q`: all 336 tests passed (65.292 seconds). `git diff --check` passed.

## 2026-09-19: transverse tangent correction (pending visual review)

Two concrete discontinuities were found. The root height used piecewise slopes
0.005 outside and 0.055 inside, a derivative jump at front/back ring vertices.
The saddle rows then joined those descending roots with zero transverse Z slope.
Replacing the root height by 0.965+0.030*c-0.025*c*c (c=side*cos(theta)) keeps
outer/inner/front heights but gives one continuous derivative at front/back.
Transverse rows use parabolic sag 4*u*(1-u)*span*0.030/(4*root_radius), weighted
by sin(theta)^2. Unlike the previous sine-squared bump this has the nonzero
endpoint derivative needed to meet the root's transverse slope. Geometry still
requires collision, topology, symmetry, and visual review; this is not acceptance.
Source snapshots now include the context indexes requested by the operator prompt.

### Tangent experiment outcome and revised arch hypothesis

The first parabolic correction passed 10 tests but was visually rejected: the
front shelf remained. Its aggregate 88-100 cm normal metric worsened (42 to 78
edges over 45 degrees); that band also includes hands, so it is not a pure pelvic
metric. The worst located edges were the medial thigh-to-saddle boundary (~85.8
 degrees), where an almost vertical leg met an almost horizontal bridge.

Next experiment: retain the smooth root profile, raise the torso's terminal ring
from 0.99 to 1.06 m to allow a merge region, and construct transverse cubic
Hermite arches using the actual incoming first-thigh-strip direction at each
boundary. Endpoint derivative magnitude equals the cross-strip span. This gives
space for the anterior/posterior arches above the thigh roots and rounds the
medial junction. It replaces the rejected parabolic/sine contour, rather than
layering more cosmetic displacement on that join. Acceptance remains pending.

The full-span arch overshot adjacent panels (148 intersecting triangle pairs).
Bounding tangent magnitude to 0.35*span reduced this to 68. An explicit anterior/
posterior relief of 0.020*sin(theta)*4*u*(1-u)*transition_amount meters keeps the
arch panels outside the lateral surface: zero detected control-triangle pairs.
This relief changes the endpoint tangent; do not claim exact tangent continuity.
It is a bounded shape proposal now undergoing rendering, not a solved likeness.

### Bounded fairing measurements

The arch alone still produced a severe front panel fold (maximum adjacent face
normal difference 113.19 degrees). Added positive local diffusion: 40 iterations,
step 0.4, compact Z weight centered 0.995 m with radius 0.135 m, restricted to
|X|<0.23 m. Each vertex is constrained within 0.020 m of its authored position.
There is no negative step, remesh, or change in connectivity. This repairs seam
sampling; it does not add missing anatomical landmarks or establish realism.

Corrected measurement region excludes hands: 88<=Z<=107 cm, |X|<22 cm.
Original documented checkpoint: maximum 85.65 degrees, p95 13.54, 42 edges >45.
Faired arch: maximum 35.27 degrees, p95 10.13, zero edges >45. The control-triangle
collision check remains zero. Region edge counts differ as torso sampling and
vertex positions changed. Reproduce with scripts/measure_surface_pelvis.py.
Visual review and final saved-file verification are still required.

### Final reviewed result: maxine-pelvis-faired

Four-view inspection confirms the conspicuous front/back angular shelf is gone
and the lateral hip join is smoother. The rear and side remain anatomically
simplified; no realistic likeness is claimed. This is the new seam-comparison
baseline. Model: 42,186 vertices / 42,530 faces. Geometry SHA-256:
09d08b6f6a2a9a6aa0230bacf5dd4129f4aca3985f420014d970a4fc6485e12c.
Both previews rendered, saved-file verification against archived source passed
(max error 0.00000596 cm), and all 338 core tests passed in 80.271 seconds.
Twelve focused tests include the 45-degree normal-jump regression and the 2 cm
fairing bound. git diff --check passed. Next region: shoulder/deltoid/axilla;
face, hands, feet, gluteal anatomy, and realistic proportions remain unfinished.
