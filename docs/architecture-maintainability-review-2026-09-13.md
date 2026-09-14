# Architecture Maintainability Review — 2026-09-13

## Scope

This review evaluates the maintainability of Asset Assistant on `main` before the next major Human-quality pass. It focuses on dependency direction, extension points, Blender integration, testability, registration/composition, source-of-truth drift, and future change risk.

## Executive summary

Asset Assistant has a strong fundamental architecture and does **not** need a broad rewrite. The host-independent `object_core`, provider specialization, Blender adapter boundary, ownership/preservation model, validation flow, and target-specific export behavior are all worth preserving.

The primary maintainability risk identified by this review was localized inside the Blender presentation/integration layer, where feature installers replaced functions or panel callbacks in other modules and made registration order carry architectural meaning.

That risk has now been materially reduced through the stabilization series:

- #245 introduced `PresentationRegistry` and migrated major workspace composition.
- #246 added architecture dependency guards, coverage floor, and support-source-of-truth alignment.
- #247 removed normalized imported-animation callback replacement.
- #248 introduced explicit Create > Modify composition and guarded against callback regression.
- #249 isolated required Blender panel `draw`/`poll` attachment behind a named host boundary.

Current assessment after stabilization:

| Area | Health | Assessment |
| --- | --- | --- |
| `object_core` boundary | Strong | Preserve |
| Provider architecture | Strong | Preserve; monitor capability growth |
| Blender translation layer | Strong | Preserve |
| Ownership/preservation contracts | Strong | Protect with tests |
| Validation architecture | Strong | Protect with tests |
| Tests/CI | Strong | Coverage + architecture guards + syntax gate |
| Target/export architecture | Strong | Preserve |
| Presentation composition | Strong | Explicit registry composition |
| Blender panel host binding | Strong | Isolated named host boundary |
| Core gateway | Growing | Watch for facade bloat |
| Module discoverability | Moderate/Good | Improved; continue local cleanup only |
| Runtime fastpaths | Acceptable | Keep narrow and semantics-preserving |

Overall maintainability is now approximately **8–8.5/10**. The architecture is healthy enough to freeze for feature work. Future cleanup should be driven by concrete pain rather than continued preemptive refactoring.

## What should not be rewritten

The following boundaries are healthy and should remain architectural constraints:

1. `object_core` owns host-independent contracts and logic and must not depend on Blender.
2. Providers own anatomy/asset-family behavior.
3. `blender_adapter` translates portable contracts into editable Blender state and owns Blender-specific scene behavior, persistence, inspection, UI, validation orchestration, and export orchestration.
4. Destination-specific behavior remains in target adapters/profiles.
5. Imported and artist-authored work remains preservation-first; Asset Assistant must not silently claim unrelated structures.
6. New abstractions should be justified by real implementations rather than speculative framework work.

## Stabilized Blender presentation model

Presentation composition now uses explicit named slots rather than install-order callback replacement. Feature modules register base renderers or deterministic decorators through `PresentationRegistry`. Duplicate ownership is visible and testable.

Blender panel class callback attachment is deliberately **not** modeled as presentation composition. Blender requires `draw`/`poll` callbacks on classes, so those mutations are treated as host integration and isolated in `workspace_panel_host` rather than spread across workflow modules.

The resulting mental model is:

```text
object_core + providers
        |
        v
 Blender adapter behavior
        |
        +--> PresentationRegistry --> workspace renderers/decorators
        |                              |
        |                              v
        +----------------------> workspace_panel_host --> Blender panel classes

 Runtime optimizations:
   ui_fastpath       -> redraw/performance seam
   modify_fastpath   -> execution/performance seam
```

The fastpaths are acceptable implementation seams because they are narrow and preserve validation/ownership semantics. They should not be forced through `PresentationRegistry`. Revisit them only if they start changing product semantics, accumulating unrelated behavior, or becoming difficult to remove.

## Secondary maintainability findings

### Provider capabilities

The provider model is healthy, but capability booleans are increasing. Do not redesign them yet. If capability combinations become substantially more complex, introduce small explicit capability objects/protocols rather than continuing to grow a flat flag list.

### Core gateway

`blender_adapter/core_gateway.py` is useful as a packaging/import boundary, but it now re-exports contracts from assets, validation, targets, components, animation, modification, and JSON exchange. Treat this as a watch item. Split it only when concrete maintenance pain appears; it is not a current blocker.

### Human naming/history

`HumanExperimentalProvider` is now the provider used for new Human assets. Internal naming can eventually become clearer while preserving serialized/legacy provider keys through compatibility aliases. Do not mix this rename into Human V2 topology/rig quality work unless it becomes necessary for that implementation.

### Source-of-truth drift

Support claims now follow automated evidence: Python 3.9–3.12 for the portable core and Blender 5.2.1 for current Blender integration. Keep compatibility documentation and CI changes together.

## Executable guardrails

The stabilization pass moved important rules from memory into CI:

- `object_core` must not import `bpy`, `blender_adapter`, or `humanoid_blender`.
- providers must remain Blender/adapter-independent.
- migrated Modify presentation cannot resume direct `workflow_ui` callback patching.
- `workflow_ui` cannot directly bind panel `draw`/`poll` callbacks after the host-boundary migration.
- core coverage has an intentional minimum.
- supported Python/Blender ranges are tied to tested CI evidence.
- Python sources are compiled in CI before the heavy Blender integration job.

## Architecture freeze checkpoint

Architecture stabilization is complete enough to begin Human V2.

**Freeze rule:** do not continue broad architecture cleanup while implementing Human V2 unless a concrete feature cannot fit the current model or a test exposes a real boundary problem.

For every major Human V2 PR, ask:

> Did we make Asset Assistant better without making it harder to maintain?

Flag a change before merge if it requires any of the following:

- Blender imports inside `object_core` or providers;
- anatomy-specific logic inside shared workflow code;
- direct cross-module presentation callback replacement;
- a new global installer whose order changes behavior invisibly;
- silent ownership transfer of artist/imported data;
- bypassing validation to improve convenience or performance;
- expanding a runtime fastpath into a second implementation of the workflow.

## Recommended next sequence

1. Merge this final stabilization checkpoint if CI is green.
2. Freeze architecture.
3. Begin Human V2 topology/anatomy work.
4. Follow with rig/deformation and weighting improvements.
5. Introduce semantic locomotion phases/contact handling and improve generated Walk/Run motion.
6. Perform one end-to-end Maxine quality pass through Blender and at least one game-engine destination.
7. Return to UI/UX density/progressive disclosure and final visual polish afterward.

## Review conclusion

Asset Assistant is not in a rewrite state. The stabilization series corrected the main Blender composition weakness without disturbing the strong core/provider/ownership/export architecture. The codebase is now in a good position to stop refactoring architecture and invest in the largest remaining product-quality gap: **Human V2 character quality and deformation/motion fidelity**.
