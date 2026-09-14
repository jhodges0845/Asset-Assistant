# SPDX-License-Identifier: GPL-3.0-or-later
"""Anatomy-oriented connected Human topology construction.

The legacy deformable Human uses one eight-sided ring resolution from pelvis to
crown.  That kept the first deformation foundation simple, but the review
wireframes show that the torso then depends on later midpoint subdivision to
approximate human contour.  This constructor makes torso/pelvis topology a
first-class part of generation while retaining the established eight-sided
neck/head and limb chains for compatibility with current face, rigging, and
animation work.
"""

from math import cos, pi, sin

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks
from .deformable import (
    _append_branch,
    _generate_face_atlas_uvs,
    _human_body_sections,
    _lerp_point,
    _shape_head_surface,
    _supported_joint_chain,
)


_TORSO_RING_SIDES = 16
_LEGACY_RING_SIDES = 8
_HIP_OPENING_LEVEL = 0
_SHOULDER_OPENING_LEVEL = 5
_TORSO_LAST_LEVEL = 6


def _ellipse_ring(z, width, depth, sides):
    return tuple(
        (
            width * 0.5 * cos(2.0 * pi * index / sides),
            depth * 0.5 * sin(2.0 * pi * index / sides),
            z,
        )
        for index in range(sides)
    )


def _append_equal_ring_band(vertices, faces, lower, upper, face_map, level):
    sides = len(lower)
    if sides != len(upper):
        raise ValueError("equal ring band requires matching ring sizes")
    for segment in range(sides):
        nxt = (segment + 1) % sides
        face_map[(level, segment)] = len(faces)
        faces.append((lower[segment], lower[nxt], upper[nxt], upper[segment]))


def _append_16_to_8_transition(faces, lower, upper):
    """Bridge a sixteen-point shoulder ring into the legacy eight-point neck."""
    if len(lower) != _TORSO_RING_SIDES or len(upper) != _LEGACY_RING_SIDES:
        raise ValueError("transition expects a 16-point lower and 8-point upper ring")
    for index in range(_LEGACY_RING_SIDES):
        lower_start = lower[(2 * index) % _TORSO_RING_SIDES]
        lower_mid = lower[(2 * index + 1) % _TORSO_RING_SIDES]
        lower_end = lower[(2 * index + 2) % _TORSO_RING_SIDES]
        upper_start = upper[index]
        upper_end = upper[(index + 1) % _LEGACY_RING_SIDES]
        faces.append((lower_start, lower_mid, upper_start))
        faces.append((lower_mid, lower_end, upper_end, upper_start))


def _build_body(proportions, hip_z, shoulder_z, chin_z, crown_z):
    sections = _human_body_sections(proportions, hip_z, shoulder_z, chin_z, crown_z)
    rings = []
    vertices = []
    for level, (z, width, depth) in enumerate(sections):
        sides = _TORSO_RING_SIDES if level <= _TORSO_LAST_LEVEL else _LEGACY_RING_SIDES
        ring = _ellipse_ring(z, width, depth, sides)
        start = len(vertices)
        vertices.extend(ring)
        rings.append(tuple(range(start, start + sides)))

    faces = [tuple(reversed(rings[0]))]
    face_map = {}
    for level in range(len(rings) - 1):
        lower = rings[level]
        upper = rings[level + 1]
        if len(lower) == len(upper):
            _append_equal_ring_band(vertices, faces, lower, upper, face_map, level)
        else:
            _append_16_to_8_transition(faces, lower, upper)
    faces.append(tuple(rings[-1]))
    return vertices, faces, face_map


def _opening_face(faces, face_map, level, side):
    if side == "left":
        segment = 0
    elif side == "right":
        segment = _TORSO_RING_SIDES // 2 - 1
    else:
        raise ValueError("side must be left or right")
    return face_map[(level, segment)], faces[face_map[(level, segment)]]


def generate_anatomical_human_mesh(proportions: HumanoidProportions) -> ObjectMesh:
    """Generate one connected Human with intentional torso/pelvis edge loops.

    Torso and pelvis bands use sixteen-point cross-sections from the hip through
    the shoulder ring.  Neck/head and limb chains deliberately remain on the
    established eight-point layout for this migration slice.  The result keeps
    the public mesh, UV, rigging, and provider contracts intact while removing
    the need for a post-generation torso midpoint-subdivision step.
    """
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")

    p = proportions
    points = generate_landmarks(p)
    hip_z = points["hip_center"][2]
    shoulder_z = points["shoulder_center"][2]
    chin_z = points["chin"][2]
    crown_z = points["crown"][2]

    vertices, body_faces, face_map = _build_body(p, hip_z, shoulder_z, chin_z, crown_z)
    vertices = _shape_head_surface(vertices, p, chin_z, crown_z)

    openings = {}
    removed = set()
    for level, region in ((_HIP_OPENING_LEVEL, "hip"), (_SHOULDER_OPENING_LEVEL, "shoulder")):
        for side in ("left", "right"):
            face_index, face = _opening_face(body_faces, face_map, level, side)
            openings[(region, side)] = face
            removed.add(face_index)
    faces = [face for index, face in enumerate(body_faces) if index not in removed]

    for side in ("left", "right"):
        shoulder = points["shoulder." + side]
        elbow = points["elbow." + side]
        wrist = points["wrist." + side]
        fingertips = points["fingertips." + side]
        shoulder_exit = _lerp_point(shoulder, elbow, 0.12)
        palm = _lerp_point(wrist, fingertips, 0.42)
        knuckles = _lerp_point(wrist, fingertips, 0.72)
        hand_width = p.forearm_thickness_cm * 0.92
        hand_depth = p.forearm_thickness_cm * 0.40
        arm_centers, arm_widths, arm_depths = _supported_joint_chain(
            (shoulder, shoulder_exit, elbow, wrist, palm, knuckles, fingertips),
            (
                p.upper_arm_thickness_cm * 1.05,
                p.upper_arm_thickness_cm,
                p.upper_arm_thickness_cm * 0.82,
                p.forearm_thickness_cm * 0.72,
                hand_width,
                hand_width * 0.94,
                hand_width * 0.48,
            ),
            (
                p.upper_arm_thickness_cm * 1.05,
                p.upper_arm_thickness_cm,
                p.upper_arm_thickness_cm * 0.82,
                p.forearm_thickness_cm * 0.72,
                hand_depth,
                hand_depth * 0.88,
                hand_depth * 0.54,
            ),
        )
        _append_branch(vertices, faces, openings[("shoulder", side)], arm_centers, arm_widths, arm_depths)

        hip = points["hip." + side]
        knee = points["knee." + side]
        ankle = points["ankle." + side]
        hip_exit = _lerp_point(hip, knee, 0.10)
        foot_height = p.foot_height_cm
        foot_center_z = foot_height * 0.5
        heel = (ankle[0], -p.foot_length_cm * 0.18, foot_center_z)
        midfoot = (ankle[0], p.foot_length_cm * 0.22, foot_center_z)
        ball = (ankle[0], p.foot_length_cm * 0.56, foot_center_z)
        toe = (ankle[0], p.foot_length_cm * 0.82, foot_center_z)
        foot_width = p.calf_thickness_cm * 0.88
        leg_centers, leg_widths, leg_depths = _supported_joint_chain(
            (hip_exit, knee, ankle, heel, midfoot, ball, toe),
            (
                p.thigh_thickness_cm,
                p.calf_thickness_cm,
                p.calf_thickness_cm * 0.6,
                foot_width * 0.82,
                foot_width,
                foot_width * 1.06,
                foot_width * 0.74,
            ),
            (
                p.thigh_thickness_cm,
                p.calf_thickness_cm,
                p.calf_thickness_cm * 0.6,
                foot_height * 0.92,
                foot_height,
                foot_height * 0.82,
                foot_height * 0.56,
            ),
        )
        _append_branch(vertices, faces, openings[("hip", side)], leg_centers, leg_widths, leg_depths)

    vertices = tuple(vertices)
    faces = tuple(faces)
    uvs = _generate_face_atlas_uvs(vertices, faces)
    return ObjectMesh((MeshPart("human", vertices, faces, uvs),))
