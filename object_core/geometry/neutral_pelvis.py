# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone, sex-neutral Human V2 pelvis prototype.

The pelvis is intentionally generated independently from the torso and thighs. It
exposes three named open boundaries so later constructors can extend topology up
into the abdomen and down into each thigh. Shape controls are semantic rather
than sex-specific so Modify can request targeted changes without replacing the
construction strategy.
"""
from dataclasses import dataclass
from math import cos, pi, sin

SIDES = 16


@dataclass(frozen=True)
class NeutralPelvisShape:
    width: float = 34.0
    depth: float = 24.0
    height: float = 20.0
    waist_width: float = 28.0
    waist_depth: float = 20.0
    hip_fullness: float = 1.0
    glute_projection: float = 1.0
    crotch_width: float = 7.0
    crotch_depth: float = 8.0
    crotch_drop: float = 1.0
    thigh_opening_width: float = 12.0
    thigh_opening_depth: float = 13.0
    thigh_spacing: float = 4.0


def _clamp(value, low, high):
    return max(low, min(high, value))


def _validated(shape):
    """Keep semantic edits inside a structurally useful neutral range."""
    return NeutralPelvisShape(
        width=max(20.0, shape.width), depth=max(12.0, shape.depth), height=max(12.0, shape.height),
        waist_width=max(16.0, shape.waist_width), waist_depth=max(10.0, shape.waist_depth),
        hip_fullness=_clamp(shape.hip_fullness, .55, 1.55),
        glute_projection=_clamp(shape.glute_projection, .55, 1.65),
        crotch_width=_clamp(shape.crotch_width, 3.0, 12.0),
        crotch_depth=_clamp(shape.crotch_depth, 4.0, 14.0),
        crotch_drop=_clamp(shape.crotch_drop, .55, 1.55),
        thigh_opening_width=_clamp(shape.thigh_opening_width, 7.0, 18.0),
        thigh_opening_depth=_clamp(shape.thigh_opening_depth, 8.0, 20.0),
        thigh_spacing=_clamp(shape.thigh_spacing, 1.5, 10.0),
    )


def semantic_controls():
    """Stable controls intended for Modify/JSON round-trip integration."""
    return (
        "width", "depth", "height", "waist_width", "waist_depth", "hip_fullness",
        "glute_projection", "crotch_width", "crotch_depth", "crotch_drop",
        "thigh_opening_width", "thigh_opening_depth", "thigh_spacing",
    )


def _ring(z, width, depth, rear_projection=0.0, lateral_fullness=0.0):
    points = []
    for i in range(SIDES):
        a = 2.0 * pi * i / SIDES
        c, s = cos(a), sin(a)
        x = width * .5 * c * (1.0 + lateral_fullness * abs(c))
        y = depth * .5 * s - rear_projection * max(0.0, -s)
        points.append((x, y, z))
    return tuple(points)


def _leg_loop(center_x, z, width, depth, side, medial_drop=0.0,
              outer_lift=0.0, rear_projection=0.0):
    """Create an anatomically biased loop around one leg socket.

    The outside of the socket sits slightly higher than the medial side, while
    the rear half receives a small gluteal projection. This avoids the old
    straight tube look without making the attachment boundary irregular enough
    to become difficult to extend into a thigh later.
    """
    sign = 1.0 if side == "left" else -1.0
    points = []
    for i in range(SIDES):
        a = 2.0 * pi * i / SIDES
        c, s = cos(a), sin(a)
        medial = max(0.0, -sign * c)
        outer = max(0.0, sign * c)
        x = center_x + width * .5 * c
        y = depth * .5 * s - rear_projection * max(0.0, -s)
        zz = z + outer_lift * outer - medial_drop * medial
        points.append((x, y, zz))
    return tuple(points)


def _append_loop(vertices, points):
    start = len(vertices)
    vertices.extend(points)
    return tuple(range(start, start + len(points)))


def _bridge_loops(faces, a, b):
    """Bridge two equally sized closed loops with consistently wound quads."""
    if len(a) != len(b):
        raise ValueError("Cannot bridge loops with different vertex counts")
    for i in range(len(a)):
        j = (i + 1) % len(a)
        faces.append((a[i], a[j], b[j], b[i]))


def _bridge_paths(faces, a, b):
    """Bridge two equally sized open paths with quads."""
    if len(a) != len(b):
        raise ValueError("Cannot bridge paths with different vertex counts")
    for i in range(len(a) - 1):
        faces.append((a[i], a[i + 1], b[i + 1], b[i]))


def generate_neutral_pelvis(shape=None):
    """Return vertices, faces and three named open boundaries.

    The construction deliberately keeps the torso and both thigh interfaces open.
    Unlike the first prototype, the hip shell no longer collapses directly into
    two leg holes. A dedicated lower-pelvis/inguinal row creates a readable
    transition into two separate sockets and a controlled central crotch saddle.
    """
    p = _validated(shape or NeutralPelvisShape())
    vertices, faces = [], []

    # Broad torso-to-hip mass. These rows establish the waist, iliac flare and
    # widest hip before the mesh separates toward the two leg sockets.
    upper = _ring(p.height * .50, p.waist_width, p.waist_depth)
    iliac = _ring(
        p.height * .18,
        p.width * .94,
        p.depth * .94,
        rear_projection=p.depth * .025 * p.glute_projection,
        lateral_fullness=.045 * p.hip_fullness,
    )
    hip = _ring(
        -p.height * .12,
        p.width,
        p.depth,
        rear_projection=p.depth * .085 * p.glute_projection,
        lateral_fullness=.070 * p.hip_fullness,
    )

    upper_loop = _append_loop(vertices, upper)
    iliac_loop = _append_loop(vertices, iliac)
    hip_loop = _append_loop(vertices, hip)
    _bridge_loops(faces, upper_loop, iliac_loop)
    _bridge_loops(faces, iliac_loop, hip_loop)

    # Two transition loops form the lower pelvis before the actual thigh
    # attachment loops. Their slightly larger footprint gives the surface room
    # to describe gluteal volume, inguinal flow and the crotch split rather than
    # pinching a single hip ring directly into two holes.
    center_offset = p.thigh_spacing * .5 + p.thigh_opening_width * .5
    transition_z = -p.height * .34
    transition_width = min(p.width * .46, p.thigh_opening_width * 1.24)
    transition_depth = min(p.depth * .72, p.thigh_opening_depth * 1.14)
    medial_drop = p.height * .075 * p.crotch_drop
    outer_lift = p.height * .030
    rear_projection = p.depth * .055 * p.glute_projection

    left_transition_points = _leg_loop(
        center_offset, transition_z, transition_width, transition_depth, "left",
        medial_drop=medial_drop, outer_lift=outer_lift,
        rear_projection=rear_projection,
    )
    right_transition_points = _leg_loop(
        -center_offset, transition_z, transition_width, transition_depth, "right",
        medial_drop=medial_drop, outer_lift=outer_lift,
        rear_projection=rear_projection,
    )
    left_transition = _append_loop(vertices, left_transition_points)
    right_transition = _append_loop(vertices, right_transition_points)

    # Split the bottom half of the hip ring into left and right 180-degree paths.
    # With the ring indexing used here, index 0 is +X, 4 is front, 8 is -X,
    # and 12 is rear. These paths meet only at the front/rear centerline and cover
    # the complete hip circumference exactly once.
    left_hip_path = tuple(hip_loop[i % SIDES] for i in range(12, 21))   # 12..15,0..4
    right_hip_path = tuple(hip_loop[i] for i in range(4, 13))          # 4..12

    # Use the outer halves of each transition loop to receive the hip shell.
    left_outer_path = tuple(left_transition[i % SIDES] for i in range(12, 21))
    right_outer_path = tuple(right_transition[i] for i in range(4, 13))
    _bridge_paths(faces, left_hip_path, left_outer_path)
    _bridge_paths(faces, right_hip_path, right_outer_path)

    # The medial halves face one another. Bridge them front-to-back to create a
    # shallow crotch saddle instead of the previous fan-like index collapse.
    left_medial_path = tuple(left_transition[i] for i in range(4, 13))
    right_medial_path = tuple(right_transition[i % SIDES] for i in (4, 3, 2, 1, 0, 15, 14, 13, 12))
    _bridge_paths(faces, left_medial_path, right_medial_path)

    # Final open thigh interfaces. They are a little narrower/deeper than the
    # transition loops and descend medially, producing a cleaner leg socket while
    # preserving simple 16-vertex loops for downstream thigh generation.
    leg_z = -p.height * .50 * p.crotch_drop
    left_thigh_points = _leg_loop(
        center_offset, leg_z, p.thigh_opening_width, p.thigh_opening_depth, "left",
        medial_drop=p.height * .050 * p.crotch_drop,
        outer_lift=p.height * .018,
        rear_projection=p.depth * .020 * p.glute_projection,
    )
    right_thigh_points = _leg_loop(
        -center_offset, leg_z, p.thigh_opening_width, p.thigh_opening_depth, "right",
        medial_drop=p.height * .050 * p.crotch_drop,
        outer_lift=p.height * .018,
        rear_projection=p.depth * .020 * p.glute_projection,
    )
    left_thigh = _append_loop(vertices, left_thigh_points)
    right_thigh = _append_loop(vertices, right_thigh_points)
    _bridge_loops(faces, left_transition, left_thigh)
    _bridge_loops(faces, right_transition, right_thigh)

    boundaries = {
        "torso": upper_loop,
        "left_thigh": left_thigh,
        "right_thigh": right_thigh,
    }
    return tuple(vertices), tuple(faces), boundaries
