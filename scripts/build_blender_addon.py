# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a self-contained, reproducible Asset Assistant Blender add-on."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_FILE_MODE = 0o644


def _write_file(archive, source, destination):
    """Write one file with stable metadata so identical sources produce identical ZIP bytes."""
    info = ZipInfo(str(destination), date_time=_ZIP_TIMESTAMP)
    info.compress_type = ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (_FILE_MODE & 0xFFFF) << 16
    archive.writestr(info, Path(source).read_bytes())


def _release_entries(root):
    entries = []
    # Source uses the host-neutral name blender_adapter. Keep the historical
    # installed module ID humanoid_blender for Blender/saved-file compatibility.
    for package in ("blender_adapter", "object_core"):
        destination = Path("humanoid_blender")
        if package == "object_core":
            destination /= "object_core"
        for source in sorted((root / package).rglob("*.py")):
            entries.append((source, destination / source.relative_to(root / package)))
    entries.extend((
        (root / "docs" / "blender.md", Path("humanoid_blender/README.md")),
        (root / "docs" / "rigging.md", Path("humanoid_blender/rigging.md")),
        (root / "docs" / "workflow.md", Path("humanoid_blender/workflow.md")),
        (root / "docs" / "human-workflow.md", Path("humanoid_blender/human-workflow.md")),
        (root / "docs" / "animation.md", Path("humanoid_blender/animation.md")),
        (root / "LICENSE", Path("humanoid_blender/LICENSE")),
        (root / "NOTICE", Path("humanoid_blender/NOTICE")),
    ))
    return tuple(sorted(entries, key=lambda entry: entry[1].as_posix()))


def build_addon(output=None):
    """Build the installable ZIP and return its path.

    ``output`` is optional so release/CI tests can build into an isolated temporary
    directory without mutating the repository's normal ``dist`` output.
    """
    root = Path(__file__).resolve().parents[1]
    output = Path(output) if output is not None else root / "dist" / "asset_assistant.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for source, destination in _release_entries(root):
            _write_file(archive, source, destination.as_posix())
    return output


def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Output ZIP path; defaults to dist/asset_assistant.zip")
    args = parser.parse_args()
    print(build_addon(args.output))


if __name__ == "__main__":
    _main()
