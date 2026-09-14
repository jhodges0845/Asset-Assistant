# SPDX-License-Identifier: GPL-3.0-or-later
"""Human deformation-oriented geometry foundation."""

from math import ceil, cos, sqrt, pi, sin

from ..models import HumanoidProportions
from ..models.mesh import MeshPart, ObjectMesh
from ..proportions.landmarks import generate_landmarks
from .primitives import RING_SIDES, vertical_loft


_HIP_OPENING_LEVEL = 0
_SHOULDER_OPENING_LEVEL = 5


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalize(vector):
    length = sqrt(sum(component * component for component in vector))
    if length == 0:
        raise ValueError("ring tangent must have nonzero length")
    return tuple(component / length for component in vector)


def _ring(center, width, depth, tangent=(0.0, 0.0, 1.0)):
    """Return an elliptical ring normal to an arbitrary 3D tangent."""
    tangent = _normalize(tangent)
    reference = (0.0, 1.0, 0.0)
    if abs(sum(tangent[i] * reference[i] for i in range(3))) > 0.95:
        reference = (0.0, 0.0, 1.0)
    width_axis = _normalize(_cross(reference, tangent))
    depth_axis = _normalize(_cross(tangent, width_axis))
    return tuple(
        tuple(
            center[axis]
            + width_axis[axis] * width * 0.5 * cos(2 * pi * i / RING_SIDES)
            + depth_axis[axis] * depth * 0.5 * sin(2 * pi * i / RING_SIDES)
            for axis in range(3)
        )
        for i in range(RING_SIDES)
    )


def _lerp_point(a, b, amount):
    return tuple(a[i] + (b[i] - a[i]) * amount for i in range(3))


def _supported_joint_chain(points, widths, depths, support=0.14):
    """Add rings immediately before/after internal joints for deformation."""
    centers = [points[0]]
    out_widths = [widths[0]]
    out_depths = [depths[0]]
    for index in range(1, len(points) - 1):
        joint = points[index]
        centers.extend(
            (
                _lerp_point(joint, points[index - 1], support),
                joint,
                _lerp_point(joint, points[index + 1], support),
            )
        )
        out_widths.extend((widths[index], widths[index], widths[index]))
        out_depths.extend((depths[index], depths[index], depths[index]))
    centers.append(points[-1])
    out_widths.append(widths[-1])
    out_depths.append(depths[-1])
    return tuple(centers), tuple(out_widths), tuple(out_depths)


def _subtract(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _side_face_index(level, segment):
    """Face index for one side quad in the standard 8-sided vertical loft."""
    return 1 + level * RING_SIDES + segment


def _append_branch(vertices, faces, root, centers, widths, depths):
    """Stitch a 4-edge torso opening into an 8-sided deformable chain."""
    if len(root) != 4:
        raise ValueError("branch root must contain four torso vertices")
    if not (len(centers) == len(widths) == len(depths)) or len(centers) < 2:
        raise ValueError("branch inputs must have equal lengths of at least two")

    rings = []
    for index, center in enumerate(centers):
        if index == 0:
            tangent = _subtract(centers[1], center)
        elif index == len(centers) - 1:
            tangent = _subtract(center, centers[index - 1])
        else:
            tangent = _subtract(centers[index + 1], centers[index - 1])
        ring = _ring(center, widths[index], depths[index], tangent)
        start = len(vertices)
        vertices.extend(ring)
        rings.append(tuple(range(start, start + RING_SIDES)))

    first = rings[0]
    for index in range(4):
        root_start = root[index]
        root_end = root[(index + 1) % 4]
        ring_start = first[(2 * index) % RING_SIDES]
        ring_mid = first[(2 * index + 1) % RING_SIDES]
        ring_end = first[(2 * index + 2) % RING_SIDES]
        faces.append((root_start, root_end, ring_end))
        faces.append((root_start, ring_end, ring_mid, ring_start))

    for level in range(len(rings) - 1):
        lower = rings[level]
        upper = rings[level + 1]
        for index in range(RING_SIDES):
            nxt = (index + 1) % RING_SIDES
            faces.append((lower[index], lower[nxt], upper[nxt], upper[index]))

    faces.append(tuple(rings[-1]))


def _smoothstep(edge0, edge1, value):
    if edge0 == edge1:
        return 0.0
    t = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def _bell(value, center, radius):
    distance = abs(value - center)
    if distance >= radius:
        return 0.0
    return 1.0 - _smoothstep(0.0, radius, distance)


def _shape_head_surface(vertices, proportions, chin_z, crown_z):
    """Give the generated head readable neutral facial landmarks.

    The Human mesh remains one connected surface with unchanged topology. This
    pass only moves existing head vertices, strengthening the broad facial
    landmarks that later semantic jaw/cheek/face operations can manipulate.
    """
    result = list(vertices)
    height = max(crown_z - chin_z, 1e-9)
    half_depth = max(proportions.head_depth_cm * 0.5, 1e-9)
    half_width = max(proportions.head_width_cm * 0.5, 1e-9)

    for index, vertex in enumerate(vertices):
        x, y, z = vertex
        if z < chin_z:
            continue

        level = max(0.0, min(1.0, (z - chin_z) / height))

        # Only the forward half of each head ring participates. Side/back skull
        # volume remains governed by the procedural head dimensions.
        front = max(0.0, min(1.0, y / half_depth))
        front = front * front
        if front <= 0.0:
            continue

        # Center weighting lets the bridge/tip/lip landmarks read in profile
        # without pushing the whole face forward like a muzzle.
        center = max(0.0, min(1.0, 1.0 - abs(x) / half_width))
        center = center * center

        # Neutral broad landmarks. These are intentionally stronger than the
        # first face-structure pass so they remain visible at ordinary viewport
        # distance while still leaving character identity to semantic edits.
        chin = _bell(level, 0.10, 0.15) * 0.075
        mouth_plane = _bell(level, 0.27, 0.10) * 0.030
        nose_mass = _bell(level, 0.42, 0.13) * 0.115
        nose_bridge = _bell(level, 0.52, 0.18) * 0.050 * center
        nose_tip = _bell(level, 0.40, 0.08) * 0.090 * center
        lips = _bell(level, 0.27, 0.055) * 0.028 * center
        eye_recess = _bell(level, 0.58, 0.10) * -0.075
        brow = _bell(level, 0.68, 0.10) * 0.070
        forehead = _bell(level, 0.80, 0.15) * 0.025

        y += proportions.head_depth_cm * (
            chin
            + mouth_plane
            + nose_mass
            + nose_bridge
            + nose_tip
            + lips
            + eye_recess
            + brow
            + forehead
        ) * front

        # Separate cheek/jaw width from the central nose bridge. Lower face
        # tapers slightly, cheek level retains breadth, and the eye plane narrows
        # enough to make the brow/cheek break readable from the front.
        jaw_taper = _bell(level, 0.14, 0.16)
        cheek = _bell(level, 0.42, 0.18)
        eye_narrow = _bell(level, 0.58, 0.12)
        width_scale = (
            1.0
            - 0.055 * jaw_taper * front
            + 0.030 * cheek * front
            - 0.030 * eye_narrow * front
        )
        x *= width_scale

        result[index] = (x, y, z)

    return result


def _generate_face_atlas_uvs(vertices, faces, padding=0.08):
    """Pack deterministic per-face UV islands into the 0-1 square.

    This first Human UV layout favors a portable, non-overlapping foundation
    over artist-optimized island continuity. Each polygon is projected on its
    two widest local axes and packed into its own padded atlas cell.
    """
    if not faces:
        return ()
    columns = int(ceil(sqrt(len(faces))))
    cell = 1.0 / columns
    scale = cell * (1.0 - padding * 2.0)
    result = []
    for face_index, face in enumerate(faces):
        points = [vertices[index] for index in face]
        spans = []
        for axis in range(3):
            values = [point[axis] for point in points]
            spans.append((max(values) - min(values), axis))
        axes = [axis for _span, axis in sorted(spans, reverse=True)[:2]]
        first_values = [point[axes[0]] for point in points]
        second_values = [point[axes[1]] for point in points]
        first_min, first_max = min(first_values), max(first_values)
        second_min, second_max = min(second_values), max(second_values)
        first_span = first_max - first_min or 1.0
        second_span = second_max - second_min or 1.0
        column = face_index % columns
        row = face_index // columns
        origin_u = column * cell + cell * padding
        origin_v = row * cell + cell * padding
        result.append(
            tuple(
                (
                    origin_u + ((point[axes[0]] - first_min) / first_span) * scale,
                    origin_v + ((point[axes[1]] - second_min) / second_span) * scale,
                )
                for point in points
            )
        )
    return tuple(result)


def _human_body_sections(p, hip_z, shoulder_z, chin_z, crown_z):
    """Return deterministic anatomical body sections for the Human surface.

    Pelvis and shoulder support levels intentionally sit close to the limb
    openings so later skinning has local geometry to distribute deformation
    across instead of folding one large torso quad.
    """
    torso = p.torso_length_cm
    neck_length = chin_z - shoulder_z
    pelvis_support_width = max(p.waist_width_cm * 1.05, p.hip_width_cm * 0.96)
    pelvis_support_depth = max(p.waist_depth_cm * 1.04, p.hip_depth_cm * 0.96)
    mid_width = (p.waist_width_cm + p.chest_width_cm) * 0.5
    mid_depth = (p.waist_depth_cm + p.chest_depth_cm) * 0.5
    shoulder_support_width = max(p.chest_width_cm, p.shoulder_width_cm * 0.90)

    return (
        (hip_z, p.hip_width_cm, p.hip_depth_cm),
        (hip_z + torso * 0.10, pelvis_support_width, pelvis_support_depth),
        (hip_z + torso * 0.35, p.waist_width_cm, p.waist_depth_cm),
        (hip_z + torso * 0.56, mid_width, mid_depth),
        (hip_z + torso * 0.78, p.chest_width_cm, p.chest_depth_cm),
        (shoulder_z - torso * 0.08, shoulder_support_width, p.chest_depth_cm * 0.90),
        (shoulder_z, p.shoulder_width_cm, p.chest_depth_cm * 0.8),
        (shoulder_z + neck_length * 0.18, p.neck_width_cm * 1.08, p.neck_width_cm * 1.08),
        (shoulder_z + neck_length * 0.38, p.neck_width_cm, p.neck_width_cm),
        (shoulder_z + neck_length * 0.62, p.neck_width_cm * 0.96, p.neck_width_cm * 0.96),
        (shoulder_z + neck_length * 0.82, p.neck_width_cm * 0.92, p.neck_width_cm * 0.92),
        (chin_z, p.neck_width_cm * 0.9, p.neck_width_cm * 0.9),
        (chin_z + p.head_height_cm * 0.12, p.head_width_cm * 0.78, p.head_depth_cm * 0.76),
        (chin_z + p.head_height_cm * 0.24, p.head_width_cm * 0.92, p.head_depth_cm * 0.90),
        (chin_z + p.head_height_cm * 0.38, p.head_width_cm, p.head_depth_cm),
        (chin_z + p.head_height_cm * 0.52, p.head_width_cm * 1.02, p.head_depth_cm),
        (chin_z + p.head_height_cm * 0.66, p.head_width_cm, p.head_depth_cm * 0.98),
        (chin_z + p.head_height_cm * 0.80, p.head_width_cm * 0.94, p.head_depth_cm * 0.92),
        (chin_z + p.head_height_cm * 0.92, p.head_width_cm * 0.82, p.head_depth_cm * 0.82),
        (crown_z, p.head_width_cm * 0.62, p.head_depth_cm * 0.68),
    )


def generate_deformable_mesh(proportions: HumanoidProportions) -> ObjectMesh:
    """Return one connected, UV'd Human deformation-oriented surface."""
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")
    p = proportions
    points = generate_landmarks(p)
    hip_z = points["hip_center"][2]
    shoulder_z = points["shoulder_center"][2]
    chin_z = points["chin"][2]
    crown_z = points["crown"][2]

    body = vertical_loft(
        "human",
        _human_body_sections(p, hip_z, shoulder_z, chin_z, crown_z),
    )

    vertices = _shape_head_surface(body.vertices, p, chin_z, crown_z)
    body_faces = list(body.faces)
    openings = {
        ("hip", "left"): body_faces[_side_face_index(_HIP_OPENING_LEVEL, 0)],
        ("hip", "right"): body_faces[_side_face_index(_HIP_OPENING_LEVEL, 3)],
        ("shoulder", "left"): body_faces[_side_face_index(_SHOULDER_OPENING_LEVEL, 0)],
        ("shoulder", "right"): body_faces[_side_face_index(_SHOULDER_OPENING_LEVEL, 3)],
    }
    removed = {
        _side_face_index(_HIP_OPENING_LEVEL, 0),
        _side_face_index(_HIP_OPENING_LEVEL, 3),
        _side_face_index(_SHOULDER_OPENING_LEVEL, 0),
        _side_face_index(_SHOULDER_OPENING_LEVEL, 3),
    }
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
            (p.upper_arm_thickness_cm * 1.05, p.upper_arm_thickness_cm,
             p.upper_arm_thickness_cm * 0.82, p.forearm_thickness_cm * 0.72,
             hand_width, hand_width * 0.94, hand_width * 0.48),
            (p.upper_arm_thickness_cm * 1.05, p.upper_arm_thickness_cm,
             p.upper_arm_thickness_cm * 0.82, p.forearm_thickness_cm * 0.72,
             hand_depth, hand_depth * 0.88, hand_depth * 0.54),
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
            (p.thigh_thickness_cm, p.calf_thickness_cm,
             p.calf_thickness_cm * 0.6, foot_width * 0.82,
             foot_width, foot_width * 1.06, foot_width * 0.74),
            (p.thigh_thickness_cm, p.calf_thickness_cm,
             p.calf_thickness_cm * 0.6, foot_height * 0.92,
             foot_height, foot_height * 0.82, foot_height * 0.56),
        )
        _append_branch(vertices, faces, openings[("hip", side)], leg_centers, leg_widths, leg_depths)

    vertices = tuple(vertices)
    faces = tuple(faces)
    uvs = _generate_face_atlas_uvs(vertices, faces)
    return ObjectMesh((MeshPart("human", vertices, faces, uvs),))
