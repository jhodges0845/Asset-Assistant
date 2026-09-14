# Asset Assistant agent instructions

This repository uses lightweight context indexes so coding agents can navigate the project without repeatedly scanning the entire tree.

## Context-first workflow

1. Read the nearest applicable `context.md` before broad repo exploration.
2. Treat `context.md` as an index and navigation aid, not as a substitute for source code or tests.
3. Follow links/pointers from the index and inspect only the files needed for the task.
4. When implementation details conflict with a context index, source code/tests win and the context index should be corrected.
5. Do not load every linked document by default. Read deeper sources only when relevant.

## User commands

The following phrases are project commands. They may appear alone or inside a longer request.

### `CONTEXT RESCAN`
Perform a local/repository scan and synchronize the context index.

- Inspect current repository structure, architecture boundaries, active roadmap/milestone state, important tests, and recent durable decisions.
- Update the root `context.md` and any scoped `context.md` files whose summaries or pointers have drifted.
- Prefer concise facts, file ownership, invariants, and pointers over narrative history.
- Remove stale facts rather than accumulating old state.
- Keep indexes small enough to save context, not consume it.
- Report material changes and any uncertainty after the rescan.

### `CONTEXT STATUS`
Check whether the context index is still trustworthy without rewriting it unless the user also asks for a rescan.

- Compare indexed claims/pointers against relevant source files and current repository state.
- Report stale, missing, misleading, oversized, or conflicting context.

### `CONTEXT BYPASS`
For the current task, bypass repository context indexes.

- Do not rely on `context.md` summaries for conclusions.
- Inspect source code, tests, docs, and current repository state directly.
- Existing `AGENTS.md` instructions still apply unless the user explicitly overrides them.

## Scanner responsibility

When acting as the user's local scanner, maintain these indexes as part of repository health.

If the context-index approach ever causes a problem — including stale guidance, incorrect assumptions, hidden coupling, excessive token use, ambiguous ownership, or worse task performance — tell the user explicitly. Do not silently work around a bad index or continue trusting it.

A rescan should improve signal-to-noise. It should not turn the index into a second copy of the repository.

## Architecture guardrails

- Keep `object_core` and provider logic host-independent. Do not import Blender adapter code into core/providers.
- Keep Blender-specific behavior in `blender_adapter`.
- Preserve artist ownership and explicit preview/apply behavior.
- Do not bypass validation or create a second implementation inside a performance fastpath.
- Do not change shared primitive assumptions such as global Human/blockout ring resolution casually; follow the Human-specific refinement seams where possible.

## Validation

Use the tests relevant to the files changed. If an applicable context file points to a narrower test set, prefer that set first, then run broader required CI checks as appropriate.
