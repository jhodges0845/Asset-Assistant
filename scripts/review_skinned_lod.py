# SPDX-License-Identifier: GPL-3.0-or-later
"""Diagnostic posed-surface comparison; no automatic artistic acceptance."""
import json
import sys
from pathlib import Path
from math import floor
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from object_core.objects import get_provider
from blender_adapter.adapter import create_character
from blender_adapter.animation import add_locomotion, add_idle, add_run, add_flight
from blender_adapter.lod_skin import build_reduced_skin_lod_candidates
from blender_adapter.lod_quality import _surface
from blender_adapter.lod import _triangles


def review(key):
    provider = get_provider(key)
    values = {field.key: field.default for field in provider.parameters}
    scene = bpy.data.scenes.new('LOD diagnostic ' + key)
    bpy.context.window.scene = scene
    mesh = provider.mesh(values)
    root = create_character(mesh, scene=scene, skeleton=provider.skeleton(values),
                            skin_weights=provider.skin_weights(mesh, values))
    root['object_type'] = key
    for name, value in values.items():
        root[name] = value
    body = next(obj for obj in root.children if obj.type == 'MESH')
    bpy.context.view_layer.update()
    diagonal = body.dimensions.length
    candidate, = build_reduced_skin_lod_candidates(body, scene, ratios=(.5,), max_distance=diagonal * .02)
    clips = {}
    cases = [('idle', add_idle, 4.), ('walk', add_locomotion, 1.2),
             ('flight', add_flight, 1.2) if key == 'avian' else ('run', add_run, .72)]
    for clip, create, duration in cases:
        create(root, scene, duration=duration, strength=1)
        rows = []
        for phase in (0, .25, .5, .75, 1):
            frame = 1 + duration * scene.render.fps / scene.render.fps_base * phase
            scene.frame_set(floor(frame), subframe=frame-floor(frame))
            graph = bpy.context.evaluated_depsgraph_get()
            a_tree, a_points = _surface(body.evaluated_get(graph))
            b_tree, b_points = _surface(candidate.evaluated_get(graph))
            distances = [tree.find_nearest(point)[3] for tree, points in
                         ((a_tree, b_points), (b_tree, a_points)) for point in points]
            rows.append({'phase': phase, 'sample_max_world_units': max(distances),
                         'sample_rms_world_units': (sum(d*d for d in distances)/len(distances))**.5})
        clips[clip] = rows
    return {'provider': key, 'source_triangles': _triangles(body.data),
            'level_triangles': _triangles(candidate.data), 'source_diagonal': diagonal,
            'schema_version': 2, 'clip_samples': clips, 'acceptance': 'diagnostic only'}


if __name__ == '__main__':
    output = Path(sys.argv[sys.argv.index('--') + 1])
    results = []
    for key in ('human', 'quadruped', 'avian'):
        try:
            results.append(review(key))
        except Exception as exc:
            results.append({'provider': key, 'error': str(exc), 'acceptance': 'blocked'})
        output.write_text(json.dumps(results, indent=2))
        print(json.dumps(results[-1]), flush=True)
