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

## Remaining acceptance work

- Review before/after silhouettes artistically; coordinate inequality alone is
  not visual acceptance.
- Complete the separate final artistic/motion and release-hardening gates from
  `shared-anatomy-alpha-plan.md`.

These proofs cover the automated external-file, parameter, component-preservation,
manual-edit and persistence checks. Artistic acceptance remains open; milestone 4
is not complete.
