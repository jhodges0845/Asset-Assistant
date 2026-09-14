# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-specific anatomy-oriented vertical loft generation.

This module keeps the established 8-vertex ring indexing so limb openings,
rigging assumptions, and downstream refinement remain compatible, while
allowing each body section to describe front/back and diagonal contour instead
of being forced to a perfect ellipse.
"""

from math import cos, pi, sin

from ..models.mesh import MeshPart
from .primitives import RING_SIDES


_EPSILON = 1e-9


def _loft(name, rings):
    vertices = tuple(vertex for ring in rings for vertex in ring)
    faces = [tuple(reversed(range(RING_SIDES)))]
    for level in range(len(rings) - 1):
        lower = level * RING_SIDES
        upper = lower + RING_SIDES
        for index in range(RING_SIDES):
            nxt = (index + 1) % RING_SIDES
            faces.append((lower + index, lower + nxt, upper + nxt, upper + index))
    faces.append(tuple(range(len(vertices) - RING_SIDES, len(vertices))))
    return MeshPart(name, vertices, tuple(faces))


def anatomical_vertical_loft(name, sections, center_x=0.0, center_y=0.0):
    """Create an 8-sided Human body loft from anatomy-aware cross sections.

    Each section is:
      (z, width, depth, front_scale, back_scale, diagonal_scale)

    Width and depth remain the nominal full dimensions. ``front_scale`` and
    ``back_scale`` bias only the positive/negative Y halves, while
    ``diagonal_scale`` rounds or tucks the four diagonal points. The left/right
    X extrema stay at the requested width, preserving bilateral dimensions and
    the existing ring index convention used by branch stitching.
    """
    if not sections:
        raise ValueError("sections must not be empty")

    rings = []
    for section in sections:
        if len(section) != 6:
            raise ValueError("anatomical sections must contain six values")
        z, width, depth, front_scale, back_scale, diagonal_scale = section
        if width <= 0 or depth <= 0:
            raise ValueError("section width and depth must be positive")
        if min(front_scale, back_scale, diagonal_scale) <= 0:
            raise ValueError("section contour scales must be positive")

        ring = []
        for index in range(RING_SIDES):
            angle = 2 * pi * index / RING_SIDES
            x_unit = cos(angle)
            y_unit = sin(angle)
            depth_scale = front_scale if y_unit > _EPSILON else back_scale if y_unit < -_EPSILON else 1.0
            diagonal = diagonal_scale if abs(x_unit) > _EPSILON and abs(y_unit) > _EPSILON else 1.0
            ring.append((
                center_x + width * 0.5 * x_unit * diagonal,
                center_y + depth * 0.5 * y_unit * depth_scale * diagonal,
                z,
            ))
        rings.append(tuple(ring))

    return _loft(name, rings)
