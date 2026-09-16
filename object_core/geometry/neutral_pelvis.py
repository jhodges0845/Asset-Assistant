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
    return (
        "width", "depth", "height", "waist_width", "waist_depth", "hip_fullness",
        "glute_projection", "crotch_width", "crotch_depth", "crotch_drop",
        "thigh_opening_width", "thigh_opening_depth", "thigh_spacing",
    )


def _ring(z, width, depth, rear_projection=0.0, lateral_fullness=0.0,
          front_softness=0.0, lower_side_drop=0.0, quarter_fullness=0.0):
    points = []
    for i in range(SIDES):
        a = 2.0 * pi * i / SIDES
        c, s = cos(a), sin(a)
        lateral = abs(c)
        quarter = 4.0 * lateral * abs(s)
        x = width * .5 * c * (1.0 + lateral_fullness * lateral + quarter_fullness * quarter)
        y = depth * .5 * s * (1.0 - front_softness * max(0.0, s) * lateral)
        y *= 1.0 + quarter_fullness * .30 * quarter
        y -= rear_projection * max(0.0, -s)
        zz = z - lower_side_drop * lateral * lateral
        points.append((x, y, zz))
    return tuple(points)


def _leg_loop(center_x, z, width, depth, side, medial_drop=0.0,
              outer_lift=0.0, rear_projection=0.0, outer_flare=0.0,
              medial_fill=0.0):
    sign = 1.0 if side == "left" else -1.0
    points = []
    for i in range(SIDES):
        a = 2.0 * pi * i / SIDES
        c, s = cos(a), sin(a)
        medial = max(0.0, -sign * c)
        outer = max(0.0, sign * c)
        front = max(0.0, s)
        rear = max(0.0, -s)
        x = center_x + width * .5 * c
        x += sign * outer_flare * outer * (.65 + .35 * (1.0 - abs(s)))
        x -= sign * medial_fill * medial * (.70 + .30 * front)
        y = depth * .5 * s - rear_projection * rear
        zz = z + outer_lift * outer * (.58 + .42 * front)
        zz -= medial_drop * medial * (.66 + .18 * front)
        zz += outer_lift * .28 * front * (1.0 - medial)
        points.append((x, y, zz))
    return tuple(points)


def _append_loop(vertices, points):
    start = len(vertices)
    vertices.extend(points)
    return tuple(range(start, start + len(points)))


def _bridge_loops(faces, a, b):
    if len(a) != len(b):
        raise ValueError("Cannot bridge loops with different vertex counts")
    for i in range(len(a)):
        j = (i + 1) % len(a)
        faces.append((a[i], a[j], b[j], b[i]))


def _bridge_paths(faces, a, b):
    if len(a) != len(b):
        raise ValueError("Cannot bridge paths with different vertex counts")
    for i in range(len(a) - 1):
        faces.append((a[i], a[i + 1], b[i + 1], b[i]))


def generate_neutral_pelvis(shape=None):
    """Return vertices, faces and three named open boundaries."""
    p = _validated(shape or NeutralPelvisShape())
    vertices, faces = [], []

    upper = _ring(
        p.height * .50, p.waist_width * 1.015, p.waist_depth,
        front_softness=.025, quarter_fullness=.010,
    )
    iliac = _ring(
        p.height * .17, p.width * .945, p.depth * .945,
        rear_projection=p.depth * .030 * p.glute_projection,
        lateral_fullness=.035 * p.hip_fullness, front_softness=.040,
        lower_side_drop=p.height * .030, quarter_fullness=.014 * p.hip_fullness,
    )
    # Extra vertical resolution where the silhouette changes fastest.  This
    # body loop carries the iliac flare into the full hip gradually while the
    # existing hip loop remains the stable parent of Astra's socket branches.
    body = _ring(
        -p.height * .015, p.width * .990, p.depth * .985,
        rear_projection=p.depth * .060 * p.glute_projection,
        lateral_fullness=.052 * p.hip_fullness, front_softness=.050,
        lower_side_drop=p.height * .055, quarter_fullness=.021 * p.hip_fullness,
    )
    hip = _ring(
        -p.height * .19, p.width * .975, p.depth * 1.020,
        rear_projection=p.depth * .105 * p.glute_projection,
        lateral_fullness=.032 * p.hip_fullness, front_softness=.060,
        lower_side_drop=p.height * .090, quarter_fullness=.020 * p.hip_fullness,
    )

    upper_loop = _append_loop(vertices, upper)
    iliac_loop = _append_loop(vertices, iliac)
    body_loop = _append_loop(vertices, body)
    hip_loop = _append_loop(vertices, hip)
    _bridge_loops(faces, upper_loop, iliac_loop)
    _bridge_loops(faces, iliac_loop, body_loop)
    _bridge_loops(faces, body_loop, hip_loop)

    center_offset = p.thigh_spacing * .5 + p.thigh_opening_width * .5
    transition_z = -p.height * .38
    transition_width = min(p.width * .46, p.thigh_opening_width * 1.24)
    transition_depth = min(p.depth * .72, p.thigh_opening_depth * 1.14)
    medial_drop = p.height * .045 * p.crotch_drop
    outer_lift = p.height * .040
    rear_projection = p.depth * .065 * p.glute_projection
    outer_flare = p.width * .018 * p.hip_fullness
    medial_fill = min(p.crotch_width * .055, p.thigh_spacing * .10)

    left_transition = _append_loop(vertices, _leg_loop(
        center_offset, transition_z, transition_width, transition_depth, "left",
        medial_drop=medial_drop, outer_lift=outer_lift,
        rear_projection=rear_projection, outer_flare=outer_flare,
        medial_fill=medial_fill,
    ))
    right_transition = _append_loop(vertices, _leg_loop(
        -center_offset, transition_z, transition_width, transition_depth, "right",
        medial_drop=medial_drop, outer_lift=outer_lift,
        rear_projection=rear_projection, outer_flare=outer_flare,
        medial_fill=medial_fill,
    ))

    left_hip_path = tuple(hip_loop[i % SIDES] for i in range(12, 21))
    left_outer_path = tuple(left_transition[i % SIDES] for i in range(12, 21))
    right_hip_path = tuple(hip_loop[i] for i in range(4, 13))
    right_outer_path = tuple(right_transition[i] for i in range(4, 13))
    _bridge_paths(faces, left_hip_path, left_outer_path)
    _bridge_paths(faces, right_hip_path, right_outer_path)

    left_medial_path = tuple(left_transition[i] for i in range(4, 13))
    right_medial_path = tuple(right_transition[i % SIDES] for i in (4, 3, 2, 1, 0, 15, 14, 13, 12))

    rail_half_width = min(p.crotch_width * .18, p.thigh_spacing * .22,
                          max(0.01, center_offset - transition_width * .5) * .5)
    left_rail_points = []
    right_rail_points = []
    for left_index, right_index in zip(left_medial_path, right_medial_path):
        lx, ly, lz = vertices[left_index]
        rx, ry, rz = vertices[right_index]
        y = (ly + ry) * .5
        z = (lz + rz) * .5 + p.height * .010 * (1.0 - min(1.0, abs(y) / max(1.0, p.crotch_depth)))
        left_rail_points.append((rail_half_width, y, z))
        right_rail_points.append((-rail_half_width, y, z))
    left_rail = _append_loop(vertices, left_rail_points)
    right_rail = _append_loop(vertices, right_rail_points)

    saddle_faces = []
    _bridge_paths(saddle_faces, left_medial_path, left_rail)
    _bridge_paths(saddle_faces, left_rail, right_rail)
    _bridge_paths(saddle_faces, right_rail, right_medial_path)
    faces.extend(tuple(reversed(face)) for face in saddle_faces)

    for end, hip_index in ((0, 4), (-1, 12)):
        seam = (left_medial_path[end], left_rail[end],
                right_rail[end], right_medial_path[end])
        for a, b in zip(seam, seam[1:]):
            face = (hip_loop[hip_index], a, b)
            faces.append(tuple(reversed(face)) if end == 0 else face)

    leg_z = -p.height * .50 * p.crotch_drop
    left_thigh = _append_loop(vertices, _leg_loop(
        center_offset, leg_z, p.thigh_opening_width, p.thigh_opening_depth, "left",
        medial_drop=p.height * .030 * p.crotch_drop,
        outer_lift=p.height * .020,
        rear_projection=p.depth * .025 * p.glute_projection,
        outer_flare=outer_flare * .35, medial_fill=medial_fill * .45,
    ))
    right_thigh = _append_loop(vertices, _leg_loop(
        -center_offset, leg_z, p.thigh_opening_width, p.thigh_opening_depth, "right",
        medial_drop=p.height * .030 * p.crotch_drop,
        outer_lift=p.height * .020,
        rear_projection=p.depth * .025 * p.glute_projection,
        outer_flare=outer_flare * .35, medial_fill=medial_fill * .45,
    ))
    _bridge_loops(faces, left_transition, left_thigh)
    _bridge_loops(faces, right_transition, right_thigh)

    boundaries = {
        "torso": upper_loop,
        "left_thigh": left_thigh,
        "right_thigh": right_thigh,
    }
    return tuple(vertices), tuple(tuple(reversed(face)) for face in faces), boundaries
