# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared validated numeric transforms for provider-owned semantic regions."""
from math import isfinite


def _number(arguments, key, default):
    value = arguments.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(key + " must be a number")
    value = float(value)
    if not isfinite(value):
        raise ValueError(key + " must be finite")
    return value


def _scale_value(arguments, axis):
    factor = _number(arguments, "factor", 1.0)
    value = _number(arguments, axis, arguments.get("scale_" + axis, factor))
    if not 0.1 <= value <= 4.0:
        raise ValueError(axis + " scale must be between 0.1 and 4.0")
    return value


def _transform(vertices, indices, arguments):
    if not indices:
        raise ValueError("Semantic target did not resolve to generated vertices")
    center = tuple(sum(vertices[index][axis] for index in indices) / len(indices) for axis in range(3))
    scales = tuple(_scale_value(arguments, axis) for axis in ("x", "y", "z"))
    offsets = tuple(_number(arguments, "offset_" + axis, 0.0) for axis in ("x", "y", "z"))
    result = list(vertices)
    for index in indices:
        vertex = vertices[index]
        result[index] = tuple(
            center[axis] + (vertex[axis] - center[axis]) * scales[axis] + offsets[axis]
            for axis in range(3)
        )
    return result


def _blend_region_transform(vertices, faces, indices, arguments):
    """Fade a profile to zero at its authored region boundary along mesh edges.

    Preserve the ordinary validated transform and its pivot. Only its displacement
    is blended; vertices outside the region and boundary vertices stay untouched.
    """
    from heapq import heappop, heappush
    from math import dist

    transformed = _transform(vertices, indices, arguments)
    selected = set(indices)
    neighbors = {index: set() for index in selected}
    boundary = set()
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1]):
            if a in selected and b in selected:
                neighbors[a].add(b)
                neighbors[b].add(a)
            elif a in selected:
                boundary.add(a)
            elif b in selected:
                boundary.add(b)
    if not boundary:
        return transformed
    distances = {index: 0.0 for index in boundary}
    queue = [(0.0, index) for index in sorted(boundary)]
    while queue:
        distance, index = heappop(queue)
        if distance != distances[index]:
            continue
        for neighbor in neighbors[index]:
            candidate = distance + dist(vertices[index], vertices[neighbor])
            if candidate < distances.get(neighbor, float('inf')):
                distances[neighbor] = candidate
                heappush(queue, (candidate, neighbor))
    radius = max(distances.values()) * .75
    result = list(vertices)
    for index in selected:
        distance = distances.get(index)
        # A disconnected fully selected component has no external seam.
        if distance is None:
            t = 1.0
        elif radius > 0:
            t = min(1.0, distance / radius)
        else:
            t = 0.0
        weight = t * t * (3.0 - 2.0 * t)
        result[index] = tuple(a + (b-a)*weight for a,b in zip(vertices[index], transformed[index]))
    return result
