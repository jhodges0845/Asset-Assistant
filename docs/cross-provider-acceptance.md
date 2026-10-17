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
exit code 1 despite unittest reporting OK and no traceback; treat remote CI as the
remaining process-level confirmation rather than claiming a clean full-suite exit.
Local full-suite log: `artifacts/shared-anatomy/cross-provider-full-blender.log`.

Scope is one generated asset-root rigid accessory per provider. Bone attachments,
skinned/imported components and rebuilding with attachments are not established
by these new cases; their existing narrower tests and restrictions still apply.

## Remaining acceptance work

- Review before/after silhouettes artistically; coordinate inequality alone is
  not visual acceptance.
- Complete the separate final artistic/motion and release-hardening gates from
  `shared-anatomy-alpha-plan.md`.

These proofs cover the automated external-file, parameter, component-preservation,
manual-edit and persistence checks. Artistic acceptance remains open; milestone 4
is not complete.
