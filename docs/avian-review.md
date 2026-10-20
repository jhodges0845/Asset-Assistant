# Avian recipe 17 review

Status: bird implementation pass completed on 2026-10-17 for the documented
stylized reference family. This is not a claim of arbitrary-species coverage or
final alpha release acceptance. Human feedback remains deferred.

## Delivered behavior

- Connected raised torso, clawed three-forward/one-rear toes, articulated wing
  chains, height-aware shoulders and torso-anchored collars.
- A broad, thin tail fan and tapered beak; torso, neck and head retain their
  established profiles. Recipe 17 retains 312 vertices, 326 faces and 16 bones.
- Folded Idle/Walk wings. Walk has alternating weighted-surface contact,
  support-timed body compression, head counter-motion and tail follow-through.
- Swing lift saturates at strength 1 (3.5% body height) to avoid folding the ankle
  into the shin. Strength still increases stride within the canonical reach bound.
- Flight has symmetric articulated wing strokes, body/neck/tail response, bounded
  wing excursion and 64 intervals per cycle. Strength above 1 increases body/tail
  response without doubling the wing excursion into self-intersection.
- Idle, Walk and Flight remain separate editable actions with preserved ownership,
  export naming and explicit regeneration. No takeoff, landing or Avian Run.

## Evidence and acceptance bounds

The complete matrix covers default, contrasting, compact-wide, tall-narrow,
long-low, short-wing, long-wing and small shapes. Idle/Walk/Flight at strengths
0.1/1/2 all pass 127-interval checks: 72 cases, no detected non-adjacent crossings,
zero sampled loop closure error. Across Walk cases, minimum foot height is
0.019602 cm and maximum reference stance drift is 0.000652 cm. Idle soles stay
stationary. The former tall-narrow strong-Walk leg defect is resolved.

All eight shapes also pass 17 diagnostic compact-fold positions. Eased quaternion
blends between actual Idle phase 0 and Flight phase 0.25 pass 64-interval checks
at three strengths, with matching endpoint geometry. Reversing this same pose
path gives the corresponding return blend. This is a tested transition path,
not an automatic state machine or a guarantee for arbitrary source/target phases.
`scripts/review_avian_transition.py` creates isolated diagnostics without changing
artist actions or NLA. Takeoff/landing remain outside the milestone.

Three-cycle four-view MP4s and editable scenes exist for both reference shapes
and all three clips. Rendered phase sheets and closer neutral/folded views were
inspected. The result is intentionally a coarse stylized bird with a readable
beak, breast, folded/extended wing distinction, tail fan and grounded feet;
individual feathers, eyes/facial detail and species-specific art direction are
not represented by these quality checks. Flight is an airborne in-place cycle;
place the character above terrain when playing it in a scene.

Godot 4.7.2 source-grid playback passes Walk/Idle/Flight/Idle switching over three
cycles on default and contrasting shapes. Maximum bone-head error versus Blender
is 0.000030 cm / 0.000057 cm, below the unchanged 0.002 cm gate. Imported clips
require explicit destination looping and retained reset tracks. This proves
skeletal playback, not destination rendered-skin parity or Unity runtime playback.
GLB/FBX structural exports pass. Shared canine Godot harness playback is also
regression-checked.

Automated validation: 47 Avian core tests, 27 Avian Blender tests and 5 architecture
tests. Portable semantic Modify, topology, weights, action switching and export
contracts are retained. Cross-provider external JSON/preview/apply acceptance,
shipping performance and release hardening remain their own milestones.

## Regeneration

For an existing recipe-16 bird, explicitly regenerate geometry for the beak/tail
fan, rebuild generated weights and regenerate Walk/Flight. Rest joint locations
and bone names are unchanged from recipe 16; no automatic artist-data replacement
is performed. Older assets still need the applicable earlier geometry/rig rebuilds.

## Reproduce

Run these scripts in Blender background mode with `--python-exit-code 1`, passing
script arguments after `--`:

- `scripts/review_avian_matrix.py --output REPORT.json`: complete 72-case matrix.
- `scripts/review_avian_gait.py --sample contrasting --intervals 127 --output REPORT.json`:
  schema 8 actual Idle/Walk/Flight report; `--clips` selects a subset.
- `scripts/review_avian_transition.py --sample contrasting --output REPORT.json`:
  canonical folded-to-Flight blend.
- `scripts/create_avian_motion_review.py --gait flight --sample contrasting --output REVIEW.blend --render --stills`:
  three-cycle scene, MP4 and four phase sheets. Also supports idle/walk.
- `scripts/export_avian_godot_review.py --sample contrasting --output FRESH_DIRECTORY`:
  shared destination fixture. Run Godot headless against that directory with
  `--script review.gd -- --source-aligned`. The shared harness retains historical
  canine fixture filenames; its oracle identifies the Avian provider and clips.

Local ignored evidence is under `artifacts/shared-anatomy/`: `avian17-matrix.json`,
`avian17-final-tests.log`, `avian17-{default,contrasting}-{idle,walk,flight}.blend`
and adjacent MP4/phase sheets, plus `avian17-godot-dense-{default,contrasting}`.
Numerical checks sample time and detect surface crossings; they do not establish
continuous collision freedom, containment clearance or arbitrary edited weights.

## Semantic chest motion review

The repaired powerful-chest profile has a separate action-sampling matrix. Use
`review_avian_matrix.py --output REPORT.json --chest-amounts 0.6 1.5` for all eight
canonical shapes, or add `--samples default contrasting`. The sampler applies the
edit through the existing planner before generating Actions, preserving weights.
See `cross-provider-acceptance.md` for results and limitations. The export helper
now accepts `--chest-amount` for four edited default/contrasting fixtures; Godot
rest vertex-cloud parity and skeletal playback pass. Four edited fixtures also pass sampled posed-skin parity with `--posed-surface`
and the renderer-backed `skin.gd` probe; final visual destination acceptance
remains open.

The destination gallery now includes 12 three-cycle MP4s alongside the phase
sheets. Encode existing Godot captures with `scripts/encode_godot_review.py`
inside Blender, then rebuild with `scripts/build_avian_godot_gallery.py --root
artifacts/shared-anatomy --require-videos`. Media verification is complete;
browser playback and final artistic acceptance remain open.
