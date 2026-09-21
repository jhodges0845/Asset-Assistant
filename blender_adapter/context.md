# blender_adapter context index

Scope: Blender-specific host behavior. `object_core` remains the portable source of domain behavior.

Read `docs/human-workflow.md` for the user workflow and code ownership map.

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
- `targets.py`, `validation.py`, `printing.py` — destination/export/validation behavior.

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

Use focused tests under `tests/blender/` first. Full CI also includes Blender 5.2.1 integration, real save/reopen, release ZIP build, and isolated packaged add-on verification.

## Human geometry

`object_core/geometry/surface_human_builder.py` builds and audits geometry for
`HumanProvider`. Standalone study scripts are development tools, not a second
plugin workflow. See `docs/human-workflow.md` for the current code map.
