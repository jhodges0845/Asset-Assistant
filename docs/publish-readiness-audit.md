# Publish readiness audit

Current evidence: [workflow and UI/UX audit](workflow-acceptance-audit.md). Earlier checkpoints below are historical or incomplete; unchecked items are not evidence of missing implementation, and passing tests are not live UI approval.

Reconciled against repository source on 2026-10-19. Status: **pre-alpha quality gates remain open**. The [shared anatomy plan](shared-anatomy-alpha-plan.md) controls sequencing; this inventory does not authorize a tag or publication.

## Existing release infrastructure

- `pyproject.toml` and `blender_adapter/__init__.py` both declare version 0.9.0. This is repository metadata, not approval of a release version.
- `.github/workflows/tests.yml` runs Python 3.9 through 3.12, Blender 5.2.1 integration, packaged ZIP smoke checks and Human visual review. Blender 2.92 is not a current CI target.
- `tests/core/test_release_package.py` covers the package builder. `scripts/test_blender_package.py` extracts the ZIP into an isolated directory, imports/registers it, exercises Human generation/rigging/Idle/materials/validation and Box target exports, then unregisters it. It also generates and rigs Avian, imports an external powerful-chest request, proves preview leaves live geometry unchanged and apply matches preview while preserving the rig, generates Idle/Walk/Flight, checks finite evaluated poses and validates the edited bird.
- `.github/workflows/release.yml` already builds the ZIP twice, compares bytes, writes a checksum and uploads artifacts. A `v*` tag checks the Python version and publishes a GitHub release. The workflow currently does not explicitly set prerelease status or run the full test suite itself.
- GPL-3.0-or-later licensing, NOTICE and install/build documentation exist.

## Remaining quality and candidate gates

1. Complete the outstanding artistic reviews in the shared anatomy plan. Automated Avian motion, destination skin and saved-scene proofs are documented in [cross-provider acceptance](cross-provider-acceptance.md); they do not replace continuous visual approval. Human feedback repairs and actual-action motion diagnosis are active in [Human review notes](human-review-notes.md); Human motion and final canine visual acceptance remain open.
2. Repeat the isolated packaged smoke on the chosen candidate. The Avian semantic-edit, rig and Idle/Walk/Flight path now passes locally in Blender 5.2.1, alongside the existing Human/Box checks. This covers packaged functionality, not artistic motion approval.
3. On the chosen candidate ZIP, record clean install, upgrade, disable/re-enable and uninstall behavior in Blender 5.2.1. Automated registration/unregistration alone is not this manual lifecycle proof.
4. Reconcile README capabilities, supported runtime, known limitations and release notes with that candidate. Capture representative images/clips and repeat destination spot checks on its exact commit.
5. Before an approved alpha tag, explicitly configure prerelease publication and establish successful candidate CI as a release prerequisite. Reproducible ZIP construction alone does not establish functional correctness.
6. Obtain the user's version/tag/publication decision. No release is authorized by this audit.

## Scope limits

Exhaustive species coverage, photoreal anatomy, universal destination certification and a marketing site are not initial alpha requirements. The shared anatomy plan's silhouette, deformation and motion gates still apply. Official Blender Extensions submission is a later distribution decision; check its current requirements if that work is requested.
