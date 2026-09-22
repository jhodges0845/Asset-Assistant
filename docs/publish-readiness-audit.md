# Publish readiness audit

> Scope update (2026-09-21): [Shared anatomy and animation](shared-anatomy-alpha-plan.md) is the active pre-alpha plan. Complete the Human/Quadruped/Avian recipe and animation quality milestones before final release hardening. The older checklist below contains historical claims and must be reconciled against source before treating an item as outstanding.


Status: **release hardening active**

Asset Assistant has completed the Human, Quadruped, and Avian provider foundations. This audit tracks the remaining work before the first public release candidate.

## Current release strengths

- Host-independent `object_core` separated from Blender-specific integration.
- Canonical public providers: Human, Quadruped, Avian, and Box.
- Human/Quadruped/Avian deforming-provider foundations with rigging, generated animation, UV/material intent, and automated Blender coverage.
- Godot, Unity, Unreal, and Cura target adapters with existing smoke or provider-specific evidence.
- CI coverage across standalone Python plus Blender 2.92 and Blender 5.2.1.
- GPL-3.0-or-later licensing, NOTICE, source build script, and install documentation.
- Protected main branch and PR-based development workflow.

## P0 release blockers

1. **Public documentation drift.** README status text must stay synchronized with completed provider capabilities and destination evidence.
2. **Version metadata consistency.** Blender add-on metadata and Python project metadata must use the same release version.
3. **Release artifact verification.** The generated ZIP needs automated checks so packaging regressions fail before a release.
4. **Tagged release automation.** CI tests the project, but a tagged GitHub Release artifact workflow is not yet established.
5. **Manual release-candidate smoke pass.** Blender 5.2.1 still needs one fresh install-from-ZIP pass covering Generate -> Rig -> Animate -> Validate -> Export, including Avian Idle/Flight visual review.

## P1 hardening before broader publication

- Add release notes/changelog for the first tagged release.
- Confirm clean install, upgrade, disable, and uninstall behavior from a packaged ZIP.
- Confirm generated package contains only intended source/docs/license files and no development artifacts.
- Capture representative screenshots from the actual release candidate.
- Run destination spot checks for the release candidate rather than relying only on earlier development evidence.
- Review current official Blender Extensions requirements immediately before any official submission.

## Not release blockers for an initial alpha

- Finished anatomy or production-quality character art.
- Exhaustive morphology presets.
- Human Run motion-quality polish beyond the current functional first pass.
- Exhaustive destination certification for every provider/target pair.
- Cura certification for every deforming provider.
- A standalone marketing website, telemetry, sponsorship, or paid promotion.

## Recommended release sequence

1. Synchronize version metadata and public documentation.
2. Add package verification tests around `scripts.build_blender_addon`.
3. Add a reproducible tagged GitHub Release workflow.
4. Produce a release-candidate ZIP from CI.
5. Perform the manual Blender 5.2.1 release-candidate smoke pass and Avian animation visual review.
6. Fix any release-candidate issues and tag the first alpha.
7. Treat official Blender Extensions submission as the next distribution milestone after the GitHub alpha is stable.

## Current quality gate

The codebase is **close to a first GitHub alpha**, but it should not be called publish-ready until public docs/version metadata are synchronized, the release artifact path is reproducible and verified, and the final packaged-install smoke pass is complete.
