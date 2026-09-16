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
    """Create an anatomically biased loop around one leg socket."""
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
    """Return vertices, faces and three named open boundaries."""
    p = _validated(shape or NeutralPelvisShape())
    vertices, faces = [], []

    upper = _ring(p.height * .50, p.waist_width, p.waist_depth)
    iliac = _ring(
        p.height * .18, p.width * .94, p.depth * .94,
        rear_projection=p.depth * .025 * p.glute_projection,
        lateral_fullness=.045 * p.hip_fullness,
    )
    hip = _ring(
        -p.height * .12, p.width, p.depth,
        rear_projection=p.depth * .085 * p.glute_projection,
        lateral_fullness=.070 * p.hip_fullness,
    )

    upper_loop = _append_loop(vertices, upper)
    iliac_loop = _append_loop(vertices, iliac)
    hip_loop = _append_loop(vertices, hip)
    _bridge_loops(faces, upper_loop, iliac_loop)
    _bridge_loops(faces, iliac_loop, hip_loop)

    center_offset = p.thigh_spacing * .5 + p.thigh_opening_width * .5
    transition_z = -p.height * .34
    transition_width = min(p.width * .46, p.thigh_opening_width * 1.24)
    transition_depth = min(p.depth * .72, p.thigh_opening_depth * 1.14)
    medial_drop = p.height * .075 * p.crotch_drop
    outer_lift = p.height * .030
    rear_projection = p.depth * .055 * p.glute_projection

    left_transition = _append_loop(vertices, _leg_loop(
        center_offset, transition_z, transition_width, transition_depth, "left",
        medial_drop=medial_drop, outer_lift=outer_lift,
        rear_projection=rear_projection,
    ))
    right_transition = _append_loop(vertices, _leg_loop(
        -center_offset, transition_z, transition_width, transition_depth, "right",
        medial_drop=medial_drop, outer_lift=outer_lift,
        rear_projection=rear_projection,
    ))

    # Both hip-to-transition paths must describe their outside half in the same
    # anatomical direction: front -> outer side -> rear.  The previous left path
    # ran rear -> outer -> front while its transition partner was interpreted in
    # the opposite direction by the split construction.  That mismatch produced
    # the long diagonal/fan visible only on the left review view.  Make the left
    # pairing explicit and directionally mirror the right side.
    left_hip_path = tuple(hip_loop[i % SIDES] for i in (4, 3, 2, 1, 0, 15, 14, 13, 12))
    left_outer_path = tuple(left_transition[i % SIDES] for i in (4, 3, 2, 1, 0, 15, 14, 13, 12))
    right_hip_path = tuple(hip_loop[i] for i in range(4, 13))
    right_outer_path = tuple(right_transition[i] for i in range(4, 13))
    _bridge_paths(faces, left_hip_path, left_outer_path)
    _bridge_paths(faces, right_hip_path, right_outer_path)

    left_medial_path = tuple(left_transition[i] for i in range(4, 13))
    right_medial_path = tuple(right_transition[i % SIDES] for i in (4, 3, 2, 1, 0, 15, 14, 13, 12))

    rail_half_width = min(p.crotch_width * .18, p.thigh_spacing * .22)
    left_rail_points = []
    right_rail_points = []
    for left_index, right_index in zip(left_medial_path, right_medial_path):
        lx, ly, lz = vertices[left_index]
        rx, ry, rz = vertices[right_index]
        y = (ly + ry) * .5
        z = (lz + rz) * .5
        left_rail_points.append((rail_half_width, y, z))
        right_rail_points.append((-rail_half_width, y, z))
    left_rail = _append_loop(vertices, left_rail_points)
    right_rail = _append_loop(vertices, right_rail_points)

    _bridge_paths(faces, left_medial_path, left_rail)
    _bridge_paths(faces, left_rail, right_rail)
    _bridge_paths(faces, right_rail, right_medial_path)

    leg_z = -p.height * .50 * p.crotch_drop
    left_thigh = _append_loop(vertices, _leg_loop(
        center_offset, leg_z, p.thigh_opening_width, p.thigh_opening_depth, "left",
        medial_drop=p.height * .050 * p.crotch_drop,
        outer_lift=p.height * .018,
        rear_projection=p.depth * .020 * p.glute_projection,
    ))
    right_thigh = _append_loop(vertices, _leg_loop(
        -center_offset, leg_z, p.thigh_opening_width, p.thigh_opening_depth, "right",
        medial_drop=p.height * .050 * p.crotch_drop,
        outer_lift=p.height * .018,
        rear_projection=p.depth * .020 * p.glute_projection,
    ))
    _bridge_loops(faces, left_transition, left_thigh)
    _bridge_loops(faces, right_transition, right_thigh)

    boundaries = {
        "torso": upper_loop,
        "left_thigh": left_thigh,
        "right_thigh": right_thigh,
    }
    return tuple(vertices), tuple(faces), boundaries
