# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture portable pre-migration output fingerprints and generation timings.

Run: python scripts/anatomy_baseline.py --output anatomy-baseline.json
Each sample runs in a fresh process so Human caches do not hide initial cost.
This report does not replace Blender silhouette, pose or playback reviews.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from object_core.objects import get_provider

SAMPLES = {
    'human': {'height_cm': 155, 'weight_kg': 65, 'body_type': 'average'},
    'quadruped': {'body_length_cm': 95, 'shoulder_height_cm': 40,
                  'body_width_cm': 28, 'head_length_cm': 30, 'tail_length_cm': 50},
    'avian': {'body_length_cm': 55, 'body_width_cm': 22, 'body_height_cm': 28,
              'wingspan_cm': 140, 'tail_length_cm': 35},
}


def fingerprint(value):
    return sha256(json.dumps(value, default=asdict, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode('utf-8')).hexdigest()


def capture(provider_key, sample):
    provider = get_provider(provider_key)
    values = {p.key: p.default for p in provider.parameters}
    if sample == 'contrasting':
        values.update(SAMPLES[provider_key])
    timings = {}

    def timed(name, call):
        start = perf_counter()
        result = call()
        timings[name] = perf_counter() - start
        return result

    mesh = timed('mesh', lambda: provider.mesh(values))
    skeleton = timed('skeleton', lambda: provider.skeleton(values))
    weights = timed('weights', lambda: provider.skin_weights(mesh, values))
    # A second call measures the public warmed path without clearing caches.
    warm = timed('mesh_warm', lambda: provider.mesh(values))
    if mesh != warm:
        raise ValueError('provider mesh output is not deterministic')
    clips = {}
    for capability, method in (('supports_idle', 'idle'),
                               ('supports_locomotion', 'locomotion'),
                               ('supports_run', 'run'), ('supports_flight', 'flight')):
        if getattr(provider, capability, False):
            kwargs = {'values': values} if getattr(provider, 'animation_uses_parameters', False) and method in ('locomotion', 'run') else {}
            clip = timed(method, lambda: getattr(provider, method)(2.0, 1.0, **kwargs))
            clips[method] = fingerprint(clip)
    return {
        'provider': provider_key, 'sample': sample, 'parameters': values,
        'parts': [{'name': p.name, 'vertices': len(p.vertices), 'faces': len(p.faces)}
                  for p in mesh.parts],
        'bones': len(skeleton.bones),
        'fingerprints': {'mesh': fingerprint(mesh), 'skeleton': fingerprint(skeleton),
                         'weights': fingerprint(weights), 'clips': clips},
        'seconds': timings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--worker', choices=tuple(SAMPLES), help=argparse.SUPPRESS)
    parser.add_argument('--sample', choices=('default', 'contrasting'), default='default')
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(capture(args.worker, args.sample), allow_nan=False))
        return
    reports = []
    for key in SAMPLES:
        for sample in ('default', 'contrasting'):
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), '--worker', key,
                 '--sample', sample], check=False, capture_output=True, text=True, cwd=ROOT)
            if result.returncode:
                raise RuntimeError(result.stderr)
            reports.append(json.loads(result.stdout))
    report = {
        'schema_version': 1,
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'working_tree_changes': subprocess.check_output(
            ['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines(),
        'python': sys.version, 'platform': platform.platform(),
        'timing_policy': 'Each sample uses a fresh process; seconds are observations, not thresholds.',
        'animation_parameters': {'duration': 2.0, 'strength': 1.0},
        'visual_review': 'Not captured: clay, silhouette, wireframe, bend poses and Blender playback remain required before migration acceptance.',
        'samples': reports,
    }
    encoded = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(encoded, encoding='utf-8')
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
