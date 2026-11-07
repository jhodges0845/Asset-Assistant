# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only corner-normal versus triangle-face diagnostics for imported LODs.

Blender: --python scripts/review_lod_normals.py -- BUNDLE --output NEW.json
[--clip Run --phase .25]. These measurements do not certify shading quality.
"""
import argparse
from hashlib import sha256
import json
from math import acos, degrees, isfinite
from pathlib import Path
import sys


def normal_report(mesh):
    """Measure angular agreement; only the derived triangulation cache is updated."""
    mesh.calc_loop_triangles()
    angles = []
    degenerate = 0
    worst = []
    for triangle in mesh.loop_triangles:
        points = [mesh.vertices[index].co for index in triangle.vertices]
        if not all(isfinite(value) for point in points for value in point):
            raise ValueError('Nonfinite vertex coordinates')
        face = (points[1] - points[0]).cross(points[2] - points[0])
        if face.length == 0:
            degenerate += 1
            continue
        face.normalize()
        values = []
        for index in triangle.loops:
            normal = mesh.corner_normals[index].vector.copy()
            if not all(isfinite(value) for value in normal) or normal.length == 0:
                raise ValueError('Invalid corner normal')
            normal.normalize()
            values.append(degrees(acos(max(-1.0, min(1.0, face.dot(normal))))))
        angles.extend(values)
        worst.append((max(values), triangle.index))
    angles.sort()
    return {
        'triangles': len(mesh.loop_triangles), 'degenerate_triangles': degenerate,
        'measured_corners': len(angles),
        'median_degrees': angles[len(angles) // 2] if angles else None,
        'p95_degrees': angles[min(int(len(angles) * .95), len(angles) - 1)] if angles else None,
        'opposed_corners': sum(angle > 90 for angle in angles),
        'worst_triangles': [{'index': index, 'maximum_degrees': angle}
                            for angle, index in sorted(worst, reverse=True)[:20]],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--clip', choices=('Idle', 'Walk', 'Run', 'Flight'))
    parser.add_argument('--phase', type=float, default=.25)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.output.exists() or not isfinite(args.phase) or not 0 <= args.phase <= 1:
        parser.error('Choose a new output path and a finite phase within [0, 1]')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import bpy
    from scripts.render_lod_review import import_snapshot
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle / 'lod-manifest.json').read_text())
    rows = []
    for level in manifest['levels']:
        path = (bundle / level['file']).resolve()
        if path.parent != bundle or path.suffix.lower() != '.glb':
            raise ValueError('Expected a GLB directly inside the bundle')
        digest = sha256(path.read_bytes()).hexdigest()
        mesh, metadata = import_snapshot(path, args.clip, args.phase)
        try:
            if metadata['triangles'] != level['triangles']:
                raise ValueError('Imported triangle count differs from manifest')
            rows.append(dict(level=level['index'], file=path.name, sha256=digest,
                             **normal_report(mesh)))
        finally:
            bpy.data.meshes.remove(mesh)
    args.output.write_text(json.dumps({
        'scope': 'Corner/face angular agreement only; not shading acceptance.',
        'clip': args.clip or 'rest', 'phase': args.phase, 'levels': rows,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
