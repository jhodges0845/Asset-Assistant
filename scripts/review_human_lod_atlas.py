# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure fresh Human face-atlas cell crossings before/after LOD reduction.

blender --background --factory-startup --python-exit-code 1 --python
scripts/review_human_lod_atlas.py -- --output REPORT.json [--sample contrasting]
This diagnostic is specific to the generated per-face atlas, not arbitrary UVs.
"""
import argparse
import json
from math import ceil, floor, isfinite, sqrt
from pathlib import Path
import sys


def atlas_report(mesh, columns):
    """Read triangle UVs without changing mesh data or judging artistic quality."""
    if not isinstance(columns, int) or isinstance(columns, bool) or columns < 1:
        raise ValueError('Atlas columns must be a positive integer')
    uv = mesh.uv_layers.active
    if uv is None:
        raise ValueError('Atlas review requires an active UV layer')
    mesh.calc_loop_triangles()
    counts = {'triangles': len(mesh.loop_triangles), 'cross_cell_triangles': 0,
              'outside_atlas_triangles': 0, 'zero_uv_area_triangles': 0,
              'smooth_polygons': sum(p.use_smooth for p in mesh.polygons)}
    for triangle in mesh.loop_triangles:
        points = [tuple(uv.data[index].uv) for index in triangle.loops]
        if not all(isfinite(value) for point in points for value in point):
            raise ValueError('Atlas review requires finite UV coordinates')
        if any(value < 0 or value >= 1 for point in points for value in point):
            counts['outside_atlas_triangles'] += 1
        cells = {(floor(u * columns), floor(v * columns)) for u, v in points}
        counts['cross_cell_triangles'] += len(cells) > 1
        a, b, c = points
        twice_area = (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        counts['zero_uv_area_triangles'] += twice_area == 0
    return counts


def source_atlas_columns(mesh):
    """Require the current generated face-index layout before interpreting cells."""
    if not mesh.polygons or mesh.uv_layers.active is None:
        raise ValueError('Expected a nonempty per-face atlas')
    columns = ceil(sqrt(len(mesh.polygons)))
    for polygon in mesh.polygons:
        expected = (polygon.index % columns, polygon.index // columns)
        for index in polygon.loop_indices:
            values = tuple(mesh.uv_layers.active.data[index].uv)
            if (not all(isfinite(value) for value in values) or
                    tuple(floor(value * columns) for value in values) != expected):
                raise ValueError('Fresh Human no longer matches the per-face atlas assumption')
    return columns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sample', choices=('default', 'contrasting'), default='contrasting')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.output.exists():
        parser.error('Choose a new report path')
    import bpy
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from object_core.objects import get_provider
    from blender_adapter.adapter import create_asset
    from blender_adapter.lod import preview_static_lods
    from scripts.anatomy_baseline import SAMPLES
    provider = get_provider('human')
    values = {parameter.key: parameter.default for parameter in provider.parameters}
    if args.sample == 'contrasting':
        values.update(SAMPLES['human'])
    # Rest-only diagnostic: same static reduction path used by skinned LOD proxies.
    root = create_asset(provider.mesh(values))
    body = next(obj for obj in root.children if obj.type == 'MESH')
    columns = source_atlas_columns(body.data)
    source = atlas_report(body.data, columns)
    if any(source[key] for key in ('cross_cell_triangles', 'outside_atlas_triangles')):
        raise ValueError('Fresh Human no longer matches the per-face atlas assumption')
    preview = preview_static_lods(body, bpy.context.scene, ratios=(.5, .25))
    try:
        report = {'sample': args.sample, 'parameters': values, 'atlas_columns': columns,
                  'blender_version': bpy.app.version_string, 'ratios': [1, .5, .25],
                  'levels': [source] + [atlas_report(obj.data, columns) for obj in preview.objects],
                  'scope': 'Fresh Human rest atlas only; crossings diagnose mixing original cells, '
                           'not UV corner correspondence, shading, skin playback or artistic acceptance.'}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        preview.cancel()


if __name__ == '__main__':
    main()
