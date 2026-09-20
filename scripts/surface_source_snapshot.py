"""Capture the exact local generator dependencies for a portable study package."""
import hashlib
import json
import shutil
from pathlib import Path


def capture_source(root, output, preset):
    root, output = Path(root), Path(output)
    snapshot = output / 'source_snapshot'
    files = list((root / 'object_core').rglob('*.py'))
    files += [root / p for p in (
        'context.md', 'object_core/context.md',
        'blender_adapter/surface_human_study.py',
        'scripts/build_surface_human.py', 'scripts/build_surface_human.ps1',
        'scripts/verify_surface_human.py', 'scripts/surface_source_snapshot.py',
        'docs/mathematical-human-workflow.md',
        'docs/mathematical-human-development.md',
        'docs/prompts/mathematical-human-operator.txt')]
    manifest = {}
    for source in files:
        relative = source.relative_to(root)
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        manifest[relative.as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    target = snapshot / 'presets/human/maxine.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(preset, target)
    manifest['presets/human/maxine.json'] = hashlib.sha256(target.read_bytes()).hexdigest()
    (snapshot / 'source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return snapshot


def verify_source(root):
    root = Path(root)
    for name, expected in json.loads((root / 'source_manifest.json').read_text(encoding='utf-8')).items():
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('Snapshot source changed: ' + name)
