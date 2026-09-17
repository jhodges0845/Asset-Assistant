# SPDX-License-Identifier: GPL-3.0-or-later
"""Smooth curve helpers for landmark-driven procedural surfaces."""
from math import sqrt

from .patch_surface import add, mul, normalized, sub


def _length(vector):
    return sqrt(sum(value * value for value in vector))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _forward_direction(hint, chord_direction, blend):
    """Blend a local tangent hint toward the span chord to prevent hook-backs."""
    hint_direction = normalized(hint)
    direction = normalized(
        add(mul(hint_direction, 1.0 - blend), mul(chord_direction, blend))
    )
    # A short noisy edge can otherwise produce a handle that points backwards.
    # Reblend toward the chord rather than flipping it, preserving local intent.
    if _dot(direction, chord_direction) < 0.20:
        direction = normalized(add(direction, mul(chord_direction, 0.80)))
    return direction


def bezier_curve_points(a, b, segments, start_handle, end_handle, max_handle_ratio=0.45):
    """Sample a cubic Bezier span with explicit endpoint handles.

    ``start_handle`` points from ``a`` toward its first control point.
    ``end_handle`` points from the second control point toward ``b``.  Handles
    are capped relative to chord length so semantic parameters cannot easily
    create loops or overshoot while experimenting with body proportions.
    """
    if segments < 1:
        raise ValueError("curve requires at least one segment")
    chord = sub(b, a)
    chord_length = _length(chord)
    if chord_length <= 1e-12:
        raise ValueError("curve endpoints must be distinct")

    maximum = chord_length * max_handle_ratio
    handles = []
    for handle in (start_handle, end_handle):
        length = _length(handle)
        if length > maximum and length > 1e-12:
            handle = mul(handle, maximum / length)
        handles.append(handle)
    start_handle, end_handle = handles

    p0 = tuple(float(value) for value in a)
    p1 = add(p0, start_handle)
    p3 = tuple(float(value) for value in b)
    p2 = sub(p3, end_handle)
    result = []
    for index in range(segments + 1):
        t = index / segments
        u = 1.0 - t
        result.append(
            tuple(
                u * u * u * p0[axis]
                + 3.0 * u * u * t * p1[axis]
                + 3.0 * u * t * t * p2[axis]
                + t * t * t * p3[axis]
                for axis in range(3)
            )
        )
    # Keep landmark identity exact rather than accepting floating-point drift.
    result[0] = p0
    result[-1] = p3
    return tuple(result)


def fit_landmark_arc(points, tangent_blend=0.28, handle_ratio=0.34):
    """Refit sampled points as one clean cubic arc between their endpoints.

    The endpoint-adjacent samples act only as tangent hints.  The landmarks
    themselves remain fixed.  Tangents are softly biased toward the endpoint
    chord, and equal handle lengths are used at both ends, which suppresses the
    small asymmetric bumps that can accumulate when many independently sampled
    points are connected across a patch network.
    """
    points = tuple(tuple(float(value) for value in point) for point in points)
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    chord = sub(b, a)
    chord_length = _length(chord)
    if chord_length <= 1e-12:
        return points
    chord_direction = normalized(chord)
    start_hint = sub(points[1], a)
    end_hint = sub(b, points[-2])
    start_direction = _forward_direction(start_hint, chord_direction, tangent_blend)
    end_direction = _forward_direction(end_hint, chord_direction, tangent_blend)

    # Keep enough handle length to express the intended arc, but cap it well
    # below half the chord so closely spaced landmarks cannot form loops.
    local_step = (_length(start_hint) + _length(end_hint)) * 0.5
    desired = max(chord_length * 0.22, min(chord_length * handle_ratio, local_step * 1.55))
    desired = min(desired, chord_length * 0.40)

    return bezier_curve_points(
        a,
        b,
        len(points) - 1,
        mul(start_direction, desired),
        mul(end_direction, desired),
        max_handle_ratio=0.40,
    )
