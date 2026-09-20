# SPDX-License-Identifier: GPL-3.0-or-later
"""Structured lower-pelvis surface construction for Human V2.

This module owns the migration from the shared abdominal/pelvic boundary into two
thigh roots. The important contract is that the split is followed by longitudinal
surface rows instead of one long conversion fan terminating directly at the legs.
"""

from .anatomical_pelvis import thigh_opening_ring


def _append_ring(vertices, points):
    ring = []
    for point in points:
        ring.append(len(vertices))
        vertices.append(point)
    return tuple(ring)


def _append_ring_band(faces, upper, lower):
    if len(upper) != 16 or len(lower) != 16:
        raise ValueError("anatomical pelvis rows require 16-point boundaries")
    for i in range(16):
        faces.append((upper[i], upper[(i + 1) % 16], lower[(i + 1) % 16], lower[i]))


def _split_shared_boundary(vertices, faces, pelvis_boundary, left_points, right_points):
    """Create the short pair-of-pants split at the top of the anatomical patch."""
    left = _append_ring(vertices, left_points)
    right = _append_ring(vertices, right_points)
    # With x=cos(a), positive-X is indices 12..4, not 0..7.
    # Match anatomical sides; manifoldness alone cannot detect a twisted patch.
    for ring, start in ((left, 12), (right, 4)):
        for j in range(8):
            a, b = (start + j) % 16, (start + j + 1) % 16
            faces.append((pelvis_boundary[a], pelvis_boundary[b], ring[b], ring[a]))
    # Medial half-rings face each other; reverse their angular traversal.
    for j in range(8):
        a, b = (4 + j) % 16, (5 + j) % 16
        c, d = (-j + 4) % 16, (-j + 3) % 16
        faces.append((left[a], left[b], right[d], right[c]))
    faces.append((pelvis_boundary[4], left[4], right[4]))
    faces.append((pelvis_boundary[12], right[12], left[12]))
    return left, right


def append_anatomical_pelvis_patch(
    vertices,
    faces,
    pelvis_boundary,
    left_centers,
    right_centers,
    thigh_width,
    thigh_depth,
):
    """Build a shared pelvis that resolves into longitudinal left/right thigh rows.

    Three non-planar opening rows distribute the anatomical transition. Only the
    first row participates in the topological split; subsequent rows are quad bands,
    so outer-hip, anterior, posterior/glute and inner-thigh paths continue down the
    surface instead of stretching from abdomen to thigh in a single face.
    """
    if len(pelvis_boundary) != 16:
        raise ValueError("anatomical pelvis patch requires a 16-point upper boundary")
    if len(left_centers) != 3 or len(right_centers) != 3:
        raise ValueError("anatomical pelvis patch requires three longitudinal rows")

    influences = (0.98, 0.93, 0.86)
    left_points = [
        thigh_opening_ring(center, thigh_width, thigh_depth, "left", influence)
        for center, influence in zip(left_centers, influences)
    ]
    right_points = [
        thigh_opening_ring(center, thigh_width, thigh_depth, "right", influence)
        for center, influence in zip(right_centers, influences)
    ]

    left, right = _split_shared_boundary(
        vertices, faces, pelvis_boundary, left_points[0], right_points[0]
    )
    for left_row, right_row in zip(left_points[1:], right_points[1:]):
        next_left = _append_ring(vertices, left_row)
        next_right = _append_ring(vertices, right_row)
        _append_ring_band(faces, left, next_left)
        _append_ring_band(faces, right, next_right)
        left, right = next_left, next_right
    return left, right
