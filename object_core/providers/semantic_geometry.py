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


