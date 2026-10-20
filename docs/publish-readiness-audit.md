# Publish readiness audit

Reconciled against repository source on 2026-10-19. Status: **pre-alpha quality gates remain open**. The [shared anatomy plan](shared-anatomy-alpha-plan.md) controls sequencing; this inventory does not authorize a tag or publication.

## Existing release infrastructure

- `pyproject.toml` and `blender_adapter/__init__.py` both declare version 0.9.0. This is repository metadata, not approval of a release version.
- `.github/workflows/tests.yml` runs Python 3.9 through 3.12, Blender 5.2.1 integration, packaged ZIP smoke checks and Human visual review. Blender 2.92 is not a current CI target.
- `tests/core/test_release_package.py` covers the package builder. `scripts/test_blender_package.py` extracts the ZIP into an isolated directory, imports/registers it, exercises Human generation/rigging/Idle/materials/validation and Box target exports, then unregisters it.
- `.github/workflows/release.yml` already builds the ZIP twice, compares bytes, writes a checksum and uploads artifacts. A `v*` tag checks the Python version and publishes a GitHub release. The workflow currently does not explicitly set prerelease status or run the full test suite itself.
- GPL-3.0-or-later licensing, NOTICE and install/build documentation exist.

## Remaining quality and candidate gates

1. Complete the outstanding artistic reviews in the shared anatomy plan. Automated Avian motion, destination skin and saved-scene proofs are documented in [cross-provider acceptance](cross-provider-acceptance.md); they do not replace continuous visual approval. Human feedback remains deferred, and final canine visual acceptance remains open.
2. Extend the isolated packaged smoke coverage to the Avian semantic-edit, rig and animation path. Current package smoke coverage is Human/Box; broader source-tree tests do not prove those modules survive packaging.
3. On the chosen candidate ZIP, record clean install, upgrade, disable/re-enable and uninstall behavior in Blender 5.2.1. Automated registration/unregistration alone is not this manual lifecycle proof.
4. Reconcile README capabilities, supported runtime, known limitations and release notes with that candidate. Capture representative images/clips and repeat destination spot checks on its exact commit.
5. Before an approved alpha tag, explicitly configure prerelease publication and establish successful candidate CI as a release prerequisite. Reproducible ZIP construction alone does not establish functional correctness.
6. Obtain the user's version/tag/publication decision. No release is authorized by this audit.

## Scope limits

Exhaustive species coverage, photoreal anatomy, universal destination certification and a marketing site are not initial alpha requirements. The shared anatomy plan's silhouette, deformation and motion gates still apply. Official Blender Extensions submission is a later distribution decision; check its current requirements if that work is requested.
