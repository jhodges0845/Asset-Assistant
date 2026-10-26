# blender_adapter context index

Scope: Blender-specific host behavior. `object_core` remains the portable source of domain behavior.

Read `docs/human-workflow.md` for the user workflow and code ownership map.

## LOD implementation (2026-10-24)

Static LOD budgets and a separate-copy preview/apply/cancel backend are implemented. Saved-preview recovery, explicit multi-mesh groups and Export workspace controls are implemented; experimental skinned preview/apply is implemented, with static GLB bundle export implemented. Internal skinned staging/clip serialization is in lod_skin_export.py and bundle publication in lod_export.py. Single rigs under static Empty parents are supported; animated parent dependencies, playback acceptance, live UI/undo and engine LOD switching remain open. See [../docs/lod-workflow.md](../docs/lod-workflow.md).

## Current workflow and UI audit (2026-10-23)

See [../docs/workflow-acceptance-audit.md](../docs/workflow-acceptance-audit.md) for model/animation Modify, LOD, import/export and UI acceptance evidence. Human rig/clip work is merged; workflow and UX validation are active. LOD support and live UI review remain open. Blender tests use pytest so function-based UI tests run alongside unittest classes.

## Current Human V2 integration (2026-09-20)

Create > Human is the single Human UI path. `HumanProvider` uses key `human` and
composes the mathematical surface builder, rig and shared body-control mapping.
The former static study option and experimental provider identity are removed.
See `docs/human-workflow.md` for the workflow and code ownership map.

## Main seams

- `core_gateway.py` — Blender-facing facade into portable core behavior.
- `presentation_registry.py` — explicit workspace renderer/decorator composition.
- `workspace_panel_host.py` — owns Blender panel draw/poll binding.
- `workflow.py` / `workflow_ui.py` — workflow state and UI presentation.
- `working_asset_ui.py`, `asset_identity_ui.py`, `asset_structure.py` — current asset identity/structure presentation.
- `modification.py`, `model_json_*`, `modify_ui.py` — model inspection/round-trip/preview/apply.
- `animation_*` — animation lifecycle, records, tuning, JSON round-trip, naming.
- `components.py` and component UI modules — component creation/adoption/modify/persistence.
- `targets.py`, `validation.py`, `printing.py` — destination/export/validation behavior. Generated unconstrained GLB/glTF clips use temporary zero-based Action copies, authored keys and explicit track names to retain fractional endpoints; constrained/driven exports retain baking. `tests/blender/test_canine_glb_playback.py` covers clip ownership, timing, loop closure, sampled contact and fixed-vertex source/reimport surface parity through Walk/Idle/Run/Idle switching. The separate Godot probe passes with diagnostic and source-grid import settings; four-view renders exist and sampled baked-skin contact checks pass, while full visual and shipping acceptance remain open. See `docs/canine-godot-playback.md`.

## Presentation rule

Do not introduce hidden callback replacement or order-dependent installer chains. Use the existing `PresentationRegistry`/panel-host composition model.

`ui_fastpath.py` and `modify_fastpath.py` are performance seams only. Do not allow them to become alternate workflow implementations.

## Ownership and safety

- Preserve distinctions between generated, imported, and adopted assets/components.
- Do not silently claim or destructively rebuild artist-owned external work.
- Keep preview/apply explicit for LLM/model changes.
- Export readiness should depend on fresh validation rather than a stale one-time validation state.

## UI direction

The four top-level workspaces are Create, Animate, Components, and Export. Current product work prioritizes Human V2 quality before another broad UI polish pass.

When UI work resumes, favor Blender-native hierarchy, progressive disclosure, compact current-asset state, and predictable transitions over custom visual novelty.

## Tests

- `tests/blender/test_model_json_acceptance.py` exercises actual external Model JSON operators across Human/Quadruped/Avian, including preview cancellation, apply equivalence and manual-edit blocking. Preview shares the component-aware Apply planner. `scripts/test_model_json_reopen.py` verifies parameter/semantic edits and rigid attachments in fresh Blender processes; see `docs/cross-provider-acceptance.md` for scope.

`tests/blender/test_semantic_deformation.py` validates paired-pose diagnostics and scene restoration. Canine and repaired Avian sampled screens pass; Human quality-screen failures remain explicitly open; passing harness tests are not artistic acceptance. See `scripts/review_semantic_deformation.py` and `docs/cross-provider-acceptance.md`.

`scripts/review_avian_gait.py` can apply semantic operations through the existing planner before sampling generated Actions; `test_avian_gait_review.py` checks edited foot/wing preservation and scene restoration.

Use focused tests under `tests/blender/` first. Full CI also includes Blender 5.2.1 integration, real save/reopen, release ZIP build, and isolated packaged add-on verification.

## Human geometry

`object_core/geometry/surface_human_builder.py` builds and audits geometry for
`HumanProvider`. Standalone study scripts are development tools, not a second
plugin workflow. See `docs/human-workflow.md` for the current code map.
