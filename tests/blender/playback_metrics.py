# SPDX-License-Identifier: GPL-3.0-or-later
"""Bulk test measurements; no changes to production evaluation or sampling."""
import numpy as np


def world_points(obj):
    coordinates = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', coordinates)
    coordinates = coordinates.reshape((-1, 3))
    matrix = np.asarray(obj.matrix_world, dtype=np.float32)
    # Keep float32 Blender coordinates and explicit affine term order.
    points = coordinates[:, 0, None] * matrix[:3, 0]
    points += coordinates[:, 1, None] * matrix[:3, 1]
    points += coordinates[:, 2, None] * matrix[:3, 2]
    points += matrix[:3, 3]
    if not np.isfinite(points).all():
        raise ValueError('Playback surface contains non-finite coordinates')
    return points


def maximum_distance(left, right):
    if left.shape != right.shape or left.ndim != 2 or left.shape[1] != 3 or not len(left):
        raise ValueError('Playback comparison requires matching nonempty point arrays')
    delta = left - right
    if not np.isfinite(delta).all():
        raise ValueError('Playback displacement must be finite')
    # Double accumulation measures the supplied float32 displacements accurately.
    squared = np.einsum('ij,ij->i', delta, delta, dtype=np.float64)
    return float(np.sqrt(squared.max()))
