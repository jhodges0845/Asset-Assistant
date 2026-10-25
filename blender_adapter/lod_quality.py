# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only sampled surface deviation for static LOD inspection."""
from math import sqrt, isfinite
from mathutils.bvhtree import BVHTree
from .lod import _validate_source, _triangles


def _surface(obj):
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    if any(not isfinite(value) for vertex in vertices for value in vertex):
        raise ValueError('Surface contains non-finite world coordinates')
    obj.data.calc_loop_triangles()
    triangles = [tuple(triangle.vertices) for triangle in obj.data.loop_triangles]
    if not triangles:
        raise ValueError('Surface must contain triangles')
    tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
    samples = vertices + [sum((vertices[index] for index in triangle), vertices[0] * 0) / 3
                          for triangle in triangles]
    return tree, samples


def inspect_static_lod(source, level):
    """Sample both directions in world-space Blender units; not a Hausdorff bound.

    Vertices and triangle centroids are sampled. No artist geometry is modified,
    no quality threshold is implied, and unsampled surface detail may be missed.
    """
    _validate_source(source)
    _validate_source(level)
    return _measure_surfaces(source, level)


def _measure_surfaces(source, level):
    source_tree, source_samples = _surface(source)
    level_tree, level_samples = _surface(level)
    distances = []
    for tree, samples in ((level_tree, source_samples), (source_tree, level_samples)):
        for point in samples:
            result = tree.find_nearest(point)
            if result is None or result[0] is None or not isfinite(result[3]):
                raise ValueError('Could not measure surface distance')
            distances.append(result[3])
    return {
        'source_triangles': _triangles(source.data),
        'level_triangles': _triangles(level.data),
        'sample_count': len(distances),
        'max_distance': max(distances),
        'rms_distance': sqrt(sum(value * value for value in distances) / len(distances)),
        'units': 'world-space Blender units',
    }


def inspect_posed_skin_lod(source, level, depsgraph):
    """Measure the currently evaluated pose without changing frame or actions."""
    from .lod_skin import inspect_skin_lod_source
    source_skin = inspect_skin_lod_source(source)
    level_skin = inspect_skin_lod_source(level)
    if source_skin.armature != level_skin.armature:
        raise ValueError('Compare skinned meshes bound to the same rig')
    return _measure_surfaces(source.evaluated_get(depsgraph), level.evaluated_get(depsgraph))
