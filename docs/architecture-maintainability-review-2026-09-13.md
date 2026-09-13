# Architecture Maintainability Review — 2026-09-13

## Scope

This review evaluates the maintainability of Asset Assistant on `main` before the next major Human-quality pass. It focuses on dependency direction, extension points, Blender integration, testability, registration/composition, source-of-truth drift, and future change risk.

## Executive summary

Asset Assistant has a strong fundamental architecture and does **not** need a broad rewrite. The host-independent `object_core`, provider specialization, Blender adapter boundary, ownership/preservation model, validation flow, and target-specific export behavior are all worth preserving.

The primary maintainability risk is localized inside the Blender presentation/integration layer. Several modules currently compose the product by replacing functions or panel callbacks in other modules during `install()` / `prepare()` calls. This makes registration order carry architectural meaning and makes it harder to reason about whether a later installer has replaced an earlier contribution.

Current assessment:

| Area | Health | Assessment |
| --- | --- | --- |
| `object_core` boundary | Strong | Preserve |
| Provider architecture | Strong | Preserve; monitor capability growth |
| Blender translation layer | Strong | Preserve |
| Ownership/preservation contracts | Strong | Protect with tests |
| Validation architecture | Strong | Protect with tests |
| Tests/CI | Strong | Add static/architecture gates |
| Target/export architecture | Strong | Preserve |
| Core gateway | Growing | Watch for facade bloat |
| Module discoverability | Moderate | Improve |
| Compatibility/source-of-truth | Moderate | Align docs and metadata |
| Blender registration | Fragile | Stabilize now |
| Presentation composition | Fragile | Stabilize now |

Overall maintainability is approximately **7/10**: healthy enough to evolve safely, but the Blender composition pattern should be corrected before adding another large workflow layer.

## What should not be rewritten

The following boundaries are healthy and should remain architectural constraints:

1. `object_core` owns host-independent contracts and logic and must not depend on Blender.
2. Providers own anatomy/asset-family behavior.
3. `blender_adapter` translates portable contracts into editable Blender state and owns Blender-specific scene behavior, persistence, inspection, UI, validation orchestration, and export orchestration.
4. Destination-specific behavior remains in target adapters/profiles.
5. Imported and artist-authored work remains preservation-first; Asset Assistant must not silently claim unrelated structures.
6. New abstractions should be justified by real implementations rather than speculative framework work.

## Highest-priority risk: order-dependent Blender composition

The current Blender entry point calls a sequence of `prepare()` and `install()` functions before registration. Several of those functions replace module-level draw functions or panel callbacks in another module.

Examples include workspace navigation, Create presentation, asset identity, and the final workspace panel draw callback. The visible behavior works, but the dependency graph is implicit:

- install order affects the final renderer;
- later installers can replace earlier behavior;
- feature modules need knowledge of another module's private functions;
- UI regressions can be caused by composition order rather than business logic;
- new contributors or agents must understand a growing sequence of mutations before changing one screen.

This is the main architecture debt to pay down now.

## Stabilization direction

Introduce an explicit presentation/workspace registry. Feature modules should contribute renderers or sections to named slots/workspaces rather than replacing functions in `workflow_ui`.

Conceptually:

```text
PresentationRegistry
  shared
    workspace_navigation
    asset_summary
  CREATE
    generate
    modify
    rig
  ANIMATE
    workflow
    clip_library
    adoption
  COMPONENTS
    inventory
    add
    modify
  EXPORT
    destination
    validation
    export
```

The registry should make duplicate ownership visible and deterministic. `workflow_ui` should consume the registry rather than being mutated by other presentation modules.

The first migration should be intentionally narrow: workspace navigation, Create workspace rendering, and asset summary/identity. Once proven by tests and Blender CI, the same pattern can be extended to the remaining presentation modules.

## Secondary maintainability findings

### Provider capabilities

The provider model is healthy, but capability booleans are increasing. Do not redesign them yet. If capability combinations become substantially more complex, introduce small explicit capability objects/protocols rather than continuing to grow a flat flag list.

### Core gateway

`blender_adapter/core_gateway.py` is useful as a packaging/import boundary, but it now re-exports contracts from assets, validation, targets, components, animation, modification, and JSON exchange. Treat this as a watch item. Split it only when concrete maintenance pain appears; it is not a current blocker.

### Human naming/history

`HumanExperimentalProvider` is now the provider used for new Human assets. Internal naming can eventually become clearer while preserving serialized/legacy provider keys through compatibility aliases. Do not mix this rename into the presentation stabilization work.

### Source-of-truth drift

Support claims should match automated evidence. Current documentation/metadata should be aligned with the Python and Blender versions actually exercised by CI. Compatibility statements should distinguish "tested" from "expected/legacy" support.

## Test and policy improvements

After the presentation registry foundation lands, add architecture/static checks that make important rules executable rather than dependent on memory. Candidate checks:

- `object_core` must not import `bpy`;
- `object_core` must not import `blender_adapter`;
- providers must not import Blender adapter code;
- new implementation must not move into `humanoid_blender` compatibility code;
- presentation modules should not replace another module's private draw callback once migrated to registry composition;
- lint/static checks should run in CI;
- coverage should have an intentional minimum once a realistic baseline is measured;
- support metadata and CI matrix should remain consistent.

## Recommended sequence

1. Introduce presentation registry foundation.
2. Migrate navigation, asset summary/identity, and Create presentation without intended visible changes.
3. Add registry/composition tests and run full CI.
4. Continue migrating remaining order-dependent presentation installers in small PRs.
5. Add architecture boundary/static checks.
6. Align support metadata/documentation.
7. Re-run architecture checkpoint.
8. Begin Human V2 topology/anatomy work.
9. Follow with rig/weighting V2 and locomotion semantics.
10. Defer final UI/UX restructuring and visual polish until feature/character architecture is stable.

## Architectural guardrails for future changes

- Prefer explicit registration over callback monkey-patching.
- Keep dependency direction visible and one-way.
- Do not place provider/anatomy rules in shared Blender workflow code.
- Do not place Blender rules in `object_core`.
- Preserve artist ownership and explicit preview/apply behavior.
- Favor small, reversible architecture PRs with no intended visible behavior change.
- When a new feature cannot be clearly placed in the architecture diagram, review its boundary before merging.

## Review conclusion

Asset Assistant is not in a rewrite state. The core architecture is a strength. The immediate goal is to make the Blender presentation layer as explicit and maintainable as the underlying core/provider architecture before deeper Human V2 work begins.
