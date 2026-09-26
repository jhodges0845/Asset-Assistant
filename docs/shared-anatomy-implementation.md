# Shared anatomy implementation checkpoint

Branch: `codex/shared-generation-system`. Foundation: `381637d`. Human/Quadruped
proof checkpoint: `bfecc5e`. Human now resolves its construction data before mesh,
rig, skinning and semantic Modify. Quadruped still has its torso/front-left proof;
full canine and Avian migrations remain ahead.

## Code ownership

- `object_core/anatomy/contracts.py`: body-plan-independent immutable identity,
  landmarks, regions, chains, symmetry and connection declarations. No provider
  imports, registry or rich per-vertex objects.
- `object_core/providers/human_anatomy.py`: `HumanRecipe` resolves validated
  controls, all Human rest landmarks and joint chains, bilateral limb regions
  and body attachment expectations. `ResolvedHumanAnatomy` adds only the immutable
  Human proportions/reference payload needed by its constructor.
- `object_core/providers/human.py`: caches the resolved recipe and composes mesh,
  rig, weights and Modify. Cache keys normalize positional/named calls and include
  recipe ID/version plus every public control. Edited meshes recompute weights.
- `object_core/geometry/surface_human.py`: the one authored Human surface
  implementation; owns remapped arm and leg membership. The optional metadata
  return does not alter vertex order, topology or coordinates.
- `object_core/geometry/surface_human_builder.py`: audits the neutral surface and
  exposes its authored membership. `geometry/human_shaping.py` owns the existing
  body-control transform used by both recipe resolution and surface shaping.
- `object_core/rigging/surface_human.py`: constructs bones directly from resolved
  chains/landmarks; it no longer calculates a second set of Human landmarks.
- `object_core/providers/human_semantic.py`: uses resolved landmark bounds and
  authored body/limb membership. Face, jaw, cheek, torso and shoulder profiles keep
  their existing spatial shaping rules; this migration does not redesign them.
- `object_core/providers/quadruped_anatomy.py`: resolves the existing
  torso/front-left proof. The existing mesh/rig builders consume those landmarks;
  geometry binds actual region and shoulder-boundary indices after construction.

Human retains its public `human` identity, controls, materials, motion and Blender
workflow. No replacement UI or parallel generation implementation was added.

## Behavior changes and limits

Human arm and leg semantic operations now follow authored limb ownership and the
rig's side labels (+X is left for this Human). Previously spatial selection used
the opposite sign and could include nearby unrelated regions. Membership remains
stable after large vertex moves. Topology-changing input is rejected before
applying indexed ownership; ordinary vertex edits, UVs and face order are retained.
Saved artist work is not regenerated automatically.

Resolving the whole Human also exposed a rig boundary issue: summing proportions
can round a few ulps outside the allowed height range. The reference height is
bounded after validating the actual input. Tests cover both supported height and
weight endpoints across all five body types; out-of-range input still fails.

Human body/limb connections declare connected-surface expectations. Their local
boundary loops are not populated yet; the existing whole-surface audit remains
the connectivity/winding gate. Region memberships are explicit, compact integer
indices, with the body intentionally containing its limb subsets. No local-frame
abstraction was needed for this migration.

Quadruped retains its existing distinct surface/rig centerlines and ground-level
lower-bone endpoint. Its surface ankle/paw are separate landmarks. Reconciling
those relationships belongs to the canine quality work. Its four/eight-vertex
shoulder boundaries are bound from actual geometry and tested for bridge faces.

## Reproduce validation

```powershell
python -m unittest discover -s tests/core -v
python scripts/anatomy_baseline.py --output anatomy-baseline.json
```

The pre-migration `anatomy-baseline-2026-09-26.json` contains default and contrasting
Human, Quadruped and Avian parameters, counts, environment, fingerprints and
observed timings. Each sample runs in a fresh process. Compare fingerprints on
the same runtime; timings are observations, not acceptance thresholds.

Current local evidence is under `artifacts/shared-anatomy/`:

- `human-baseline.json`: final six-sample comparison output.
- `human-core-tests.log`: complete portable suite.
- `human-blender-tests.log`: Blender 5.2.1 integration suite.
- `human-package-tests.log`: isolated ZIP workflow verification.
- `human-visual-tests.log`, `human-migration-deformation.png`: projected pose review.

Human migration validation on Python 3.9.13 / Blender 5.2.1:

- All 370 core tests pass; all 231 Blender integration tests pass.
- All six baseline fingerprint sets match exactly (mesh, rig, weights, clips).
- Isolated ZIP generation/rig/animation/validation/export checks pass.
- Real Human and attached-component save/reopen checks pass.
- All seven diagnostic pose checks pass. The rendered eight-card sheet was
  inspected: labels and silhouettes are readable and expected bends are visible.
- Python compilation and whitespace checks pass.

Save/reopen logs are `human-reopen-tests.log` and `component-reopen-tests.log`
in the same artifact directory. The refreshed installable add-on is
`dist/asset_assistant.zip`. Coverage tooling is not installed in local Python;
CI coverage remains pending. This preserves current anatomy; it does not claim
final anatomical quality acceptance.

## Next slice

Expand the canine recipe beyond its proof limb, deriving the full rest anatomy,
geometry, local weights and executable semantic controls from the shared seam.
Then migrate Avian using bird-specific surface and joint rules. Continue visual
silhouette, wireframe and deformation gates as anatomy quality changes.
