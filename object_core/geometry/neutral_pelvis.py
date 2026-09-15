# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone, sex-neutral Human V2 pelvis prototype.

The pelvis is intentionally generated independently from the torso and thighs.  It
exposes three named open boundaries so later constructors can extend topology up
into the abdomen and down into each thigh.  Shape controls are semantic rather
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


def _leg_opening(center_x, z, width, depth, side, medial_bias):
    sign = 1.0 if side == "left" else -1.0
    points = []
    for i in range(SIDES):
        a = 2.0 * pi * i / SIDES
        c, s = cos(a), sin(a)
        medial = max(0.0, -sign * c)
        x = center_x + width * .5 * c - sign * medial_bias * medial
        y = depth * .5 * s
        # Outer hip begins higher; medial crotch descends toward the centerline.
        zz = z + width * .10 * max(0.0, sign * c) - width * .16 * medial
        points.append((x, y, zz))
    return tuple(points)


def generate_neutral_pelvis(shape=None):
    """Return vertices, faces and three named open boundaries.

    This first prototype deliberately leaves all interfaces open.  It is a visual
    anatomy primitive, not yet the active Human constructor.
    """
    p = _validated(shape or NeutralPelvisShape())
    vertices, faces = [], []

    upper = _ring(p.height * .5, p.waist_width, p.waist_depth)
    iliac = _ring(p.height * .15, p.width * .94, p.depth * .94,
                  rear_projection=p.depth * .035 * p.glute_projection,
                  lateral_fullness=.055 * p.hip_fullness)
    hip = _ring(-p.height * .18, p.width, p.depth,
                rear_projection=p.depth * .10 * p.glute_projection,
                lateral_fullness=.075 * p.hip_fullness)

    rings = []
    for points in (upper, iliac, hip):
        start = len(vertices); vertices.extend(points); rings.append(tuple(range(start, start + SIDES)))
    for a, b in zip(rings, rings[1:]):
        for i in range(SIDES):
            j = (i + 1) % SIDES
            faces.append((a[i], a[j], b[j], b[i]))

    # Leg interfaces are deliberately narrower medially than the old thigh tubes.
    center_offset = p.thigh_spacing * .5 + p.thigh_opening_width * .5
    leg_z = -p.height * .5 * p.crotch_drop
    left_points = _leg_opening(center_offset, leg_z, p.thigh_opening_width,
                               p.thigh_opening_depth, "left", p.crotch_width * .18)
    right_points = _leg_opening(-center_offset, leg_z, p.thigh_opening_width,
                                p.thigh_opening_depth, "right", p.crotch_width * .18)
    left_start = len(vertices); vertices.extend(left_points); left = tuple(range(left_start, left_start + SIDES))
    right_start = len(vertices); vertices.extend(right_points); right = tuple(range(right_start, right_start + SIDES))

    # Path-based provisional bridge: outer/anterior/rear sectors descend from the
    # hip mass.  The medial crotch remains a neutral central seam.  The standalone
    # render will tell us where this surface needs another anatomical row.
    for source_slice, target in ((range(0, 8), left), (range(8, 16), right)):
        src = tuple(rings[-1][i] for i in source_slice)
        dst_offset = 0 if target is left else 8
        dst = tuple(target[(dst_offset + i) % SIDES] for i in range(8))
        for i in range(7):
            faces.append((src[i], src[i + 1], dst[i + 1], dst[i]))
    # Close only the central surface between leg openings; keep the three named
    # attachment loops themselves open.
    for i in range(8):
        li = left[7 + i]
        ln = left[(8 + i) % SIDES]
        ri = right[(7 - i) % SIDES]
        rn = right[(6 - i) % SIDES]
        faces.append((li, ln, rn, ri))

    boundaries = {"torso": rings[0], "left_thigh": left, "right_thigh": right}
    return tuple(vertices), tuple(faces), boundaries
