# Contributing to Asset Assistant

Thank you for helping improve Asset Assistant. The project is an artist-first, open-source Blender add-on with a Python core.

## Before starting

- Read [README.md](README.md), [docs/roadmap.md](docs/roadmap.md), and [LICENSE](LICENSE).
- Check existing issues and pull requests to avoid duplicate work.
- For significant changes, open an issue to discuss scope and acceptance criteria before implementing.
- Be respectful of artists' edits: avoid destructive changes to existing assets and saved work.

## Development and testing

- Target Blender **5.2.1** for Blender integration behavior.
- Keep reusable logic in the independent Python core and Blender-specific behavior in the adapter.
- Add or update focused automated tests for changed behavior. Use the existing repository test commands and CI configuration rather than introducing a new test runner.
- When changing geometry, rigging, animation, materials, UI, or export, include relevant visual or downstream-engine validation evidence when feasible.
- Do not treat passing automated tests as proof of artistic quality.
- Keep documentation and roadmap claims aligned with actual behavior.

## Pull requests

- Make small, reviewable changes with a clear problem statement.
- Explain user-visible effects, compatibility implications, tests run, and any tests not run.
- Link related issues and attach screenshots or recordings when visual behavior changes.
- Do not submit secrets, personal data, copyrighted third-party assets without permission, or generated artifacts that are not needed for review.

## Licensing

Contributions submitted for inclusion are expected to be compatible with the repository's **GPL-3.0-or-later** license. By contributing, you represent that you have the rights needed to submit your work under that license. Copyright remains with its respective holders unless separately agreed in writing.

## Security reports

Please follow [SECURITY.md](SECURITY.md) for suspected vulnerabilities rather than posting exploitable details in a public issue.

## Community

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
