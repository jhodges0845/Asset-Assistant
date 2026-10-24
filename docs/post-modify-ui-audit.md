# Post-Modify / UI regression and architecture audit

Current evidence: [workflow and UI/UX audit](workflow-acceptance-audit.md). Earlier checkpoints below are historical or incomplete; unchecked items are not evidence of missing implementation, and passing tests are not live UI approval.

This audit is the release checkpoint after the first usable Modify workflow and the unified Asset Assistant sidebar landed.

## Scope reviewed

The audit reviewed the shared provider registry, Blender workflow/UI registration, Modify inspect/plan/apply boundaries, preservation checks, release-package tests, and the existing Human / Quadruped / Avian / Box regression coverage.

The intended artist flow is now:

`Generate -> Modify -> Rig -> Animate -> Validate -> Export`

The adapter/core boundary remains intact: provider geometry, rigging, materials, animation intent, validation contracts, and modification planning remain host-independent; Blender scene inspection and mutation remain under `blender_adapter`.

## Regression status

Automated coverage now exercises all public provider shapes through the shared architecture:

- Human: connected deforming generation, rigging, Idle/Walk/Run, materials/UVs, game exports, Cura, and Modify regeneration.
- Quadruped: connected deforming generation, rigging, Idle/Walk/Run, materials/UVs, export behavior, and Modify regeneration.
- Avian: connected deforming generation including legs/feet, rigging, Idle/Walk/Flight, materials/UVs, representative Godot/Unity exports, and Modify regeneration/preservation.
- Box: shared generation plus static validation/export behavior.

The Modify release boundary is now explicitly covered by a representative parameter regeneration test for each deforming public provider. The existing deeper Avian case additionally verifies generated rig/material/animation replacement and preservation of an artist-facing animation export name.

## Preservation / safety review

Current Modify behavior is intentionally conservative.

- Inspection is non-mutating.
- Parameter changes require a reviewable core plan before Blender mutation.
- Omitted parameters are preserved.
- Geometry ownership is reproduced and compared against provider output before destructive replacement.
- Rig replacement is blocked when NLA, drivers, artist-owned active actions, or pose constraints make ownership/preservation ambiguous.
- Generated materials use an explicit ownership marker for new assets, with exact-name compatibility for older generated files.
- Generated animation export-name edits are metadata-only and reject duplicate final names.
- Parameter regeneration stages replacement generated data before swapping it onto the live root.
- The original root identity and transform are preserved by regression coverage.
- Legacy assets without a stable Asset Assistant asset id remain inspectable but are warned as unsafe for destructive automatic migration.

No release-severity preservation defect was identified in this pass.

## Architecture findings

### Healthy boundaries

1. `object_core` remains host-independent and provider-driven.
2. `blender_adapter` owns Blender translation, scene inspection/mutation, UI, and target orchestration.
3. New anatomy remains in provider modules rather than shared Blender branches.
4. Destination-specific behavior stays in target profiles/adapters.
5. Historical `humanoid_blender` and `humanoid.*` identifiers remain compatibility surfaces rather than a second implementation.
6. The unified sidebar changes presentation without pushing UI concepts into core contracts.

### Follow-up architecture debt

The current parameter-impact planner uses a conservative shared fallback: any changed provider parameter rebuilds generated geometry and whichever generated rig/material/animation components already exist. This is safe for the alpha boundary, but it is broader than the long-term design goal where providers can declare finer-grained invalidation impact. Do not add anatomy-specific conditions to the shared planner. Introduce provider-specific impact declarations only when a real optimization or preservation case requires them.

`docs/architecture.md` still contains pre-Avian wording in a few places (for example, an older canonical-provider list and future-tense Avian language). This is documentation drift, not an implementation boundary failure, and should be corrected during release-documentation hardening.

## Test-coverage finding fixed by this audit

Before this audit, destructive provider-parameter regeneration had deep Blender coverage only through Avian. The release contract says Human, Quadruped, and Avian must all support a targeted safe change. This audit adds a shared regression that performs one real parameter regeneration for each of those three providers while verifying:

- plan safety;
- geometry-only impact when the asset has no later generated components;
- preservation of the root object identity and transform;
- preservation of every unrequested provider parameter; and
- post-apply geometry ownership.

## Remaining manual visual checkpoint

The new sidebar organization is structurally covered by Blender tests, but automated tests cannot judge spacing, discoverability, label clarity, or whether the six panels feel comfortable in a real Blender workspace. A short Blender 5.2.1 visual pass remains required before release hardening is considered closed.

The visual pass should confirm that one **Asset Assistant** sidebar tab presents the six stages in this order and that each stage remains usable at normal sidebar widths:

`Generate / Modify / Rig / Animate / Validate / Export`

## Release gate after this audit

After this PR is green and the visual sidebar pass is accepted, the remaining release blockers are release/distribution work rather than provider architecture work:

1. tagged release automation;
2. deterministic/reproducible release artifact verification;
3. release-facing documentation sync, including stale architecture wording;
4. clean install-from-ZIP smoke test in Blender 5.2.1; and
5. first public alpha publication only after those gates pass.

No new provider, animation family, anatomy polish milestone, or destination certification expansion should be inserted ahead of that release sequence unless testing exposes a release-severity defect.
