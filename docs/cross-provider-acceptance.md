# Cross-provider Modify acceptance

## External Model JSON proof (2026-10-17)

`tests/blender/test_model_json_acceptance.py` exercises the registered artist-facing
operators with real exported/imported JSON files, rather than calling only the
portable planner or semantic apply function. Each returned file supplies a semantic
operation; no vertex coordinates are authored in the request.

| Provider | Intended variation | Result |
| --- | --- | --- |
| Human | Broader shoulders, amount 0.6 | Preview and applied geometry match |
| Quadruped | Broader chest, amount 0.6 | Preview and applied geometry match |
| Avian | More powerful chest, amount 0.6 | Preview and applied geometry match |

For each provider the proof checks export, import, temporary visual preview,
cancel/restore, preview again and explicit apply. Import and preview leave the
live source vertices unchanged. Apply produces exactly the previewed vertices,
retains asset identity, records the semantic operation and preserves the existing
armature, modifier and vertex groups. The imported-apply status is verified.

A subsequent manual vertex edit removes generated-geometry ownership. Attempting
a new visual preview then fails without altering those artist-edited vertices or
leaving a preview behind. These are isolated test assets; deferred Human art
feedback is not implemented by this checkpoint.

Validation: all three cases pass in Blender 5.2.1. Local log:
`artifacts/shared-anatomy/model-json-acceptance.log` (ignored). Run with the existing
Blender unittest discovery harness and pattern `test_model_json_acceptance.py`.
No production-code change was required by this proof.

## Parameter, component and fresh-process proof (2026-10-17)

The extended operator cases combine a changed provider parameter with the same
semantic edit. Preview/cancel/apply must agree on geometry, and apply regenerates
the owned rig for the new dimensions. Semantic-only requests still preserve the
existing rig object. A representative generated rigid accessory is then attached
to each asset root.

A subsequent parameter regeneration request is blocked while that accessory is
attached; both body and accessory vertices and the attachment remain unchanged.
This is the existing supported safety boundary, not support for rebuilding a body
under an attached component. The new tests exposed a preview/apply mismatch:
visual preview previously used unenriched portable planning and could display a
change that Apply would block. Preview now uses the same component-aware inspection
and planning path as Apply.

`scripts/test_model_json_reopen.py` saves each resulting asset and launches a
separate Blender process to reopen it. It checks exact saved body/accessory
coordinates, stable identity, parameter value, semantic metadata, generated
ownership, attachment parenting, armature modifiers and skin groups. The original
process deliberately edits the body after saving as part of the ownership test.
All three fresh-process cases pass locally in Blender 5.2.1 (log:
`artifacts/shared-anatomy/model-json-reopen.log`). The reopen harness is included
in CI alongside existing persistence checks.

The full local Blender suite reports 270 tests passing in 626 seconds, and all
five architecture boundary tests pass. The full Blender shell invocation returned
exit code 1 despite unittest reporting OK and no traceback. Remote Blender CI for
commit `08fdb06` subsequently passed the full suite, new fresh-process checks and
packaged-add-on checks (run `39071957394`), providing independent process-level
confirmation. All six CI jobs for that commit passed, including Python 3.12
coverage. The local exit discrepancy remains unexplained.
Local full-suite log: `artifacts/shared-anatomy/cross-provider-full-blender.log`.

Scope is one generated asset-root rigid accessory per provider. Bone attachments,
skinned/imported components and rebuilding with attachments are not established
by these new cases; their existing narrower tests and restrictions still apply.

## Reproducible visual review

Run `scripts/render_model_json_acceptance.py` in a fresh Blender process with
`-- --output artifacts/shared-anatomy/modify-review`. The helper exports and imports
real Model JSON, verifies that preview leaves the source unchanged, applies the
request, and checks that applied geometry equals preview geometry.

For each provider it saves the applied `.blend`, exported inspection, returned
request, a review JSON with source commit/parameters/operation/displacement, and
before/after clay and silhouette sheets. Both states share camera, lighting and
framing derived from their combined bounds. These are neutral semantic-only
comparisons, separate from the combined parameter/component persistence cases.
The Human shoulder example does not implement the deferred Human art feedback.
The complete Blender 5.2.1 run exited successfully and produced all 12 PNGs, three
applied scenes and three review reports. Open the generated `index.html` for
clay/silhouette comparisons. Source geometry is from `08fdb06`; reports record
preview/apply equality. These artifacts are local/ignored and reproducible with
the committed script.

### Initial visual findings (before boundary blending)

The Human `shoulders/broad` edit at amount 0.6 produces an abrupt ledge at the
shoulder-to-upper-arm boundary in the matched clay views. Preview/apply equality
passes, but this variation fails visual quality acceptance. The previous
`human_semantic.py` broad profile applied a uniform X scale within its selected
region, leaving a sharp transition to untouched vertices. The bounded transition below addresses this defect and repeats the same comparison. Do not confuse this with the separately deferred glute, foot or
neck-deformation feedback. Existing saved semantic edits need ownership/version
consideration before changing their reconstruction behavior.

The Canine `chest/broad` edit at amount 0.6 also exposes a pronounced shoulder/chest
boundary ridge in the three-quarter and side clay views. Preserve this comparison
as a regression reference for localized chest blending. Neither observation is a
claim about physical deformation or manifoldness; these are visible rest-surface
quality defects.

## Broad-profile boundary refinement (2026-10-18)

Human `shoulders/broad` and Canine `chest/broad` now blend the existing validated
profile displacement according to distance from the selected region boundary
along mesh edges. Boundary vertices stay fixed; the interior retains the original
profile scale/pivot. A smoothstep falloff reaches full influence at 75% of the
maximum inward distance. Explicit scale/offset arguments and other profiles retain
their prior behavior. No base topology, rig, UV, or global ring-resolution changes
are involved.

The matched amount-0.6 clay views remove the conspicuous Human shoulder ledge and
Canine chest ridge recorded above. New artifacts live in
`artifacts/shared-anatomy/modify-blended-review/index.html`; the original
`modify-review` directory is retained. Reproduce with the existing render helper
and `--providers human quadruped`. These are neutral default-shape observations,
not full deformation or final artistic acceptance.

Core tests cover unchanged seams/exterior vertices (within floating-point
roundoff), topology/UV preservation and interior widening at amounts 0, 0.6 and
1.5, plus fully selected and boundary-only islands. Blender tests cover current
preview/apply behavior and preservation of the old hard-region profiles. All eight
operator cases pass in Blender 5.2.1; all three fresh-process cases pass, and opening
the original saved Human/Canine review files confirms their geometry and metadata
remain unchanged. The full core suite passes 470 tests (591 seconds); four focused boundary/island
tests also pass, including two island cases added during that run. Local evidence:
`semantic-blend-blender.log`, `semantic-blend-reopen.log`, and
`semantic-boundary-final.log` under `artifacts/shared-anatomy`. The revised render
run exited successfully with eight images, two applied scenes and two reports;
reports now include source-file hashes and whether those sources were modified.

### Existing saved edits

There is no automatic migration. Saved old broad-shoulder/chest geometry differs
from reconstruction under the new profile and is therefore treated as unowned
geometry by the existing comparison guard. It remains editable and intact;
automatic Modify regeneration is blocked. To use the new profile, create a fresh
generated asset from the saved parameters and reapply the request, keeping the old
asset for comparison. Do not override the ownership guard or rewrite saved patch
metadata merely to force regeneration. Other profiles and unmodified generated
assets are unaffected by this profile-specific reconstruction change.

## Paired deformation screening (2026-10-18)

`review_semantic_deformation.py` applies each broad profile through the existing
inspection/plan/apply path, retaining the original skin weights. It compares the
edited and unedited body in identical shoulder-forward, shoulder-back, elbow and
combined poses. The matrix covers Human and Canine, default and contrasting
parameters, and amounts 0.6/1.5 (eight cases, 32 paired poses).

The screen requires finite evaluated vertices, effective limb motion and unchanged
posed positions for vertices outside the rest edit. It also flags edited-to-baseline
posed edge-length ratios outside 0.5 to 2. These are conservative diagnostic limits,
not a proof of deformation quality: an already compressed baseline edge can inflate
the ratio even when the edited edge is less compressed. Reports retain the worst
edge indices and both neutral and posed lengths so that distinction is inspectable.
No self-intersection, volume, animation or final artistic acceptance is inferred.
The completed report passes 24/32 pose screens: all 16 Canine poses and eight
Human poses. Every case retains the original skin weights and has zero measured
posed displacement outside the rest edit. Eight Human poses fail the edge screen.

The Human default at amount 0.6 passes this relative screen. The default at 1.5 and
contrasting shape at both amounts fail it. The combined Human pose already shows
torso/hip pulling on the unedited baseline; see `human-review-notes.md`. Keep Human
profile/deformation acceptance open. This checkpoint does not change production
shaping, weights, or the separately deferred Human anatomy feedback.

Run in a fresh Blender process:

```text
blender --background --factory-startup --python-exit-code 1 --python scripts/review_semantic_deformation.py -- --output artifacts/shared-anatomy/semantic-deformation --render
```

The command writes the complete JSON/HTML report and paired default-strength images
before returning failure for the known quality-screen failures. A nonzero exit for
this matrix must not be described as successful deformation acceptance. The
`test_semantic_deformation.py` tests verify the passing Canine cases, explicitly
record the known Human failures, verify strict rejection, and ensure both success
and failure restore the caller's scene/datablocks. All four harness tests pass locally in Blender 5.2.1. Passing these tests does
not close the failing quality gate. The report generator correctly exits nonzero
after saving all four paired images and the complete report. See
`artifacts/shared-anatomy/semantic-deformation/index.html`; the associated logs are
`semantic-deformation.log` and `semantic-deformation-tests.log`.

All six CI jobs passed for production-refinement commit `da6f3c5` before this
diagnostic-only checkpoint. New CI verifies the harness, not final model quality.

## Avian paired deformation checkpoint (2026-10-18)

All six CI jobs passed for `24cb46e` (run `39135176285`). The extended
review now includes Avian `chest/powerful`, using wing-up/down, elbow and the
existing authored compact folded-wing pose. It covers default parameters and a
contrasting 65/24/30 cm body with 145 cm wingspan and 35 cm tail, at strengths
0.6 and 1.5. Use `--providers avian` to reproduce only these four cases; the
unfiltered command now covers 12 cases / 48 poses across all three providers.

All 16 Avian poses fail the unchanged relative-edge screen. Weights remain
unchanged, and posed displacement outside the rest edit is zero. This is a
quality failure, not an operator/persistence failure. The script writes its
complete report before returning nonzero. Local matched folded-wing images and
measurements: `artifacts/shared-anatomy/avian-semantic-deformation/index.html`.
The after image exposes a new ridge on the folded wing at default strength 0.6.

The default right-wing edge 134--142 shrinks from 3.9158 cm to 0.6317 cm
already in the neutral edit. Its left counterpart is 94--102. Authored anatomy
places both endpoints in their respective wing region, but the coordinate-based
chest selector includes only the first endpoint. It therefore scales a partial
wing selection while leaving neighboring wing vertices fixed. This establishes a
rest-shape selection defect; the folded pose reveals it rather than causing it.

Next repair: constrain chest shaping using authored region ownership, check its
body/wing transition across both shapes and strengths, and protect saved existing
chest edits when reconstruction changes. Do not silently migrate saved geometry
or override ownership checks. No Avian production geometry is changed here.
All five focused diagnostic tests report OK in Blender 5.2.1 (82.7 seconds),
including strict rejection and scene restoration. The local shell returned exit
code 1 despite unittest reporting OK with no traceback, matching the earlier
unexplained local runner discrepancy; remote CI remains the process-level check.
Log: `artifacts/shared-anatomy/semantic-deformation-tests.log`. Passing harness
tests must not be reported as Avian quality acceptance.

## Avian chest selection repair (2026-10-18)

`chest/powerful` now intersects its coordinate selection with the constructor's
body region. Authored wing and leg vertices cannot enter this profile, including
when an earlier semantic operation moves them into the chest bounds. The existing
profile scale and pivot calculation then operates on the selected body vertices.
The provider verifies authored topology before using these indices. Other profiles
and chest operations without the powerful profile retain their previous behavior.
There is no base recipe, skeleton, weight, topology or UV change.

All 16 Avian paired poses now pass the unchanged screen across both shapes and
strengths; edge ratios range from approximately 0.844 to 1.354. Weights remain
unchanged and posed displacement outside the rest edit remains zero. The original
failing evidence is retained in `avian-semantic-deformation`; repaired evidence
is in `artifacts/shared-anatomy/avian-chest-refined/index.html`. These sampled
screens do not establish final artistic or animation acceptance.

Saved old powerful-chest edits remain intact but differ from new reconstruction,
so the existing ownership guard blocks automatic regeneration. Create a fresh
asset with the saved parameters and reapply the request to adopt the repaired
profile, retaining the old asset for comparison. A legacy operator regression
and the actual original `modify-review/avian-applied.blend` exercise this boundary.
No stored operation metadata is rewritten and no automatic migration is performed.

The broader Avian core suite passes 49 tests, including wing/leg preservation at
strengths 0, 0.6 and 1.5 and rejection of altered topology. All six CI jobs passed
for preceding diagnostic commit `71f92b8`; repair CI is separate.
The 14 focused Blender operator/deformation tests report OK (198 seconds); all
three fresh-process save/reopen checks pass with process exit 0, as does the
actual legacy-file inspection. Five architecture-boundary tests pass. Matched
folded-wing renders show the added wing ridge removed while retaining chest
expansion. Local logs: `avian-chest-core.log`, `avian-chest-tests.log`,
`avian-chest-reopen.log`, `avian-chest-legacy.log` and `avian-chest-refined.log`
under `artifacts/shared-anatomy`. The redirected core/test/render shell wrappers
returned 1 despite successful test/report output, continuing the local wrapper
exit discrepancy; no quality failure is hidden by that observation. Repair CI
remains the independent full-suite process check.


## Edited Avian action sampling (2026-10-18)

All six CI jobs passed for chest repair `2fc249f` (run `39162848447`).
`review_avian_gait.py` now accepts semantic operations, applies them through the
existing inspection/plan/apply path, verifies geometry ownership and unchanged
weights, then samples actual generated Idle/Walk/Flight Actions. Neutral crossing
checks use the edited surface. Reports identify the applied operations.

`review_avian_matrix.py` accepts `--samples` and `--chest-amounts`; omitting both
retains the unedited 72-case matrix. The edited matrix combines chest amounts
0.6/1.5 with animation strengths 0.1/1/2. Each cycle uses 127 intervals. It retains
the existing contact, crossing and closure thresholds and additionally checks
neutral crossings. Matrix schema 2 records source hashes, commit, working-tree
state, operations and scope. Reproduce all eight canonical review shapes with:

```text
blender --background --factory-startup --python-exit-code 1 --python scripts/review_avian_matrix.py -- --output artifacts/shared-anatomy/avian-chest-motion-full.json --chest-amounts 0.6 1.5
```

The complete 144-case edited matrix passes with process exit 0: eight shapes,
two chest amounts, three clips and three animation strengths. No sampled or
neutral surface crossings were detected; maximum sampled loop-closure error is
0 cm. Minimum Walk clearance is 0.0196018 cm and maximum scheduled-stance
reference displacement is 0.00065136 cm. Report and log:
`artifacts/shared-anatomy/avian-chest-motion-full.json` and adjacent `.log`.

Nine Avian action-review tests report OK locally (67.3 seconds). The new paired
case checks identical foot positions and wing spans before/after the strongest
chest edit across all three clips, as well as loop closure, crossings, actual
motion and scene/datablock restoration. The redirected test wrapper returned 1
despite unittest reporting OK without a traceback, continuing the documented
local wrapper discrepancy; the matrix itself exited 0. Test log:
`artifacts/shared-anatomy/avian-semantic-motion-tests.log`. These sampled measurements do not close
final artistic acceptance, destination acceptance for edited assets, or prove
collision freedom between samples. Human quality work remains open.

## Edited Avian Godot proof (2026-10-18)

The shared export fixture accepts `--chest-amount` for Avian only, validates a
finite value in (0, 1.5], and applies `chest/powerful` through the existing planner
before materials, Actions and GLB export. It records the semantic operation and
neutral mesh positions in Godot coordinates. Unedited fixtures keep their prior
path. Output must be a fresh directory.

The Godot probe optionally compares imported rest vertices against that reference
in both directions, allowing duplicate export vertices at UV/normal seams. This is
vertex-cloud parity, not topology, UV, normal or posed-skin parity. It then runs
the existing source-grid skeletal proof: three cycles each of Walk, Idle, Flight
and Idle again, with 34 samples per cycle and a 0.002 cm bone-head tolerance.

All four fixtures pass in Blender 5.2.1 / Godot 4.7.2: default and canonical
contrasting shapes, each with chest amount 0.6 and 1.5. Rest-coordinate error is
0 cm; worst bone-head error is 0.00005694 cm. A deliberately shifted reference
vertex is rejected with process exit 1; restoring the reference passes again.
An unedited Avian fixture also passes the updated shared probe. All valid export
and Godot processes exit 0. Evidence: `artifacts/shared-anatomy/avian-edited-godot-`
`{default,contrasting}-{06,15}/expected.json` and `godot-report.json`, plus
`avian-edited-godot-negative.json` for the rejection control.

Example (repeat with a fresh directory and the other shape/amount):

```text
blender --background --factory-startup --python-exit-code 1 --python scripts/export_avian_godot_review.py -- --output artifacts/shared-anatomy/avian-edited-godot-default-06 --chest-amount 0.6
godot --headless --path artifacts/shared-anatomy/avian-edited-godot-default-06 --script review.gd -- --source-aligned
```

The probe does not measure rendered skin through motion or establish final
artistic acceptance. Edited-bird skeletal playback and rest geometry are now
verified in this destination; posed-skin and visual destination review remain.

## Edited Avian posed-surface parity (2026-10-19)

All six CI jobs passed for `13b5bb2` (run `39179771358`). The export fixture
now accepts Avian-only `--posed-surface` and records every evaluated Blender
vertex at the existing 34 sample times per clip. `review_avian_godot_skin.gd`
imports through the same source-grid importer and compares Godot's baked skinned
mesh using fixed neutral correspondence. Every source vertex must be represented;
export duplicates retain that correspondence throughout playback. Moving vertices
are never rematched. Nonfinite points and changed surface/vertex counts fail.

All four default/contrasting, amount-0.6/1.5 fixtures pass in Blender 5.2.1 and
Godot 4.7.2. Each tests three cycles through Walk, Idle, Flight and Idle again.
All 312 source vertices are covered. Worst sampled errors are 0.00069782 cm for
default and 0.00110342 cm for contrasting, below the unchanged 0.002 cm threshold.
A separate control changes one Flight reference vertex by 1 cm and correctly
fails with approximately 1.0000002 cm error. All valid processes exit 0; the
negative control exits 1. Evidence: `artifacts/shared-anatomy/avian-skin-`
`{default,contrasting}-{06,15}/godot-skin-report.json`; the separate
`avian-skin-negative` directory retains rejection evidence.

Generate a fresh fixture and run Godot with a rendering-capable driver:

```text
blender --background --factory-startup --python-exit-code 1 --python scripts/export_avian_godot_review.py -- --output artifacts/shared-anatomy/avian-skin-default-06 --chest-amount 0.6 --posed-surface
godot --path artifacts/shared-anatomy/avian-skin-default-06 --script skin.gd --rendering-method gl_compatibility --resolution 320x240
```

Do not use the headless dummy renderer for baked-skin measurements. This run used
Godot's compatibility renderer with ANGLE on the local AMD GPU. These are sampled
surface-position comparisons, excluding between-sample behavior, normals/UVs,
blendshape deformation and final artistic acceptance. The fixture has no animated
blendshapes. Full visual playback review remains open; numerical agreement alone
does not establish appealing motion or anatomy.

## Remaining acceptance work

- Review before/after silhouettes artistically; coordinate inequality alone is
  not visual acceptance.
- Complete the separate final artistic/motion and release-hardening gates from
  `shared-anatomy-alpha-plan.md`.

These proofs cover the automated external-file, parameter, component-preservation,
manual-edit and persistence checks. Artistic acceptance remains open; milestone 4
is not complete.
