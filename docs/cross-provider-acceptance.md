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

## Remaining acceptance work

- Review before/after silhouettes artistically; coordinate inequality alone is
  not visual acceptance.
- Combine a representative attached component and parameter regeneration with
  this external-file workflow for each provider.
- Save/reopen the resulting assets in a fresh Blender process and validate their
  persisted ownership, component attachment and semantic metadata.
- Complete the separate final artistic/motion and release-hardening gates from
  `shared-anatomy-alpha-plan.md`.

This checkpoint covers the semantic external-file and manual-edit protection
portion of milestone 4, not the entire milestone.
