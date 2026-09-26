# SPDX-License-Identifier: GPL-3.0-or-later
"""Connected quadruped surface generation."""

from dataclasses import replace
from math import cos, pi, sin, sqrt

from ..models import MeshPart, ObjectMesh
from ..anatomy import AnatomyRegion
from .quadruped_anatomy import QuadrupedFrontRecipe


_RING_SIDES = 8


def _normalize(vector):
    length = sqrt(sum(value * value for value in vector))
    if length == 0:
        raise ValueError("ring tangent must have nonzero length")
    return tuple(value / length for value in vector)


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _subtract(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _lerp(a, b, amount):
    return tuple(a[i] + (b[i] - a[i]) * amount for i in range(3))


def _ring(center, width, depth, tangent):
    tangent = _normalize(tangent)
    reference = (0.0, 0.0, 1.0)
    if abs(sum(tangent[i] * reference[i] for i in range(3))) > 0.95:
        reference = (0.0, 1.0, 0.0)
    width_axis = _normalize(_cross(reference, tangent))
    depth_axis = _normalize(_cross(tangent, width_axis))
    return tuple(
        tuple(
            center[axis]
            + width_axis[axis] * width * 0.5 * cos(2 * pi * index / _RING_SIDES)
            + depth_axis[axis] * depth * 0.5 * sin(2 * pi * index / _RING_SIDES)
            for axis in range(3)
        )
        for index in range(_RING_SIDES)
    )


def _append_tube(vertices, faces, centers, widths, depths, *, cap_start=True, cap_end=True):
    rings = []
    for index, center in enumerate(centers):
        if index == 0:
            tangent = _subtract(centers[1], center)
        elif index == len(centers) - 1:
            tangent = _subtract(center, centers[index - 1])
        else:
            tangent = _subtract(centers[index + 1], centers[index - 1])
        start = len(vertices)
        vertices.extend(_ring(center, widths[index], depths[index], tangent))
        rings.append(tuple(range(start, start + _RING_SIDES)))

    if cap_start:
        faces.append(tuple(reversed(rings[0])))
    for level in range(len(rings) - 1):
        first, second = rings[level], rings[level + 1]
        for segment in range(_RING_SIDES):
            nxt = (segment + 1) % _RING_SIDES
            faces.append((first[segment], first[nxt], second[nxt], second[segment]))
    if cap_end:
        faces.append(tuple(rings[-1]))
    return rings


def _append_branch(vertices, faces, root, centers, widths, depths):
    """Replace one torso quad with an eight-sided deformable limb chain."""
    if len(root) != 4:
        raise ValueError("branch root must contain four vertices")
    rings = _append_tube(vertices, faces, centers, widths, depths, cap_start=False, cap_end=True)
    first = rings[0]
    for index in range(4):
        root_start = root[index]
        root_end = root[(index + 1) % 4]
        ring_start = first[(2 * index) % _RING_SIDES]
        ring_mid = first[(2 * index + 1) % _RING_SIDES]
        ring_end = first[(2 * index + 2) % _RING_SIDES]
        faces.append((root_start, root_end, ring_end))
        faces.append((root_start, ring_end, ring_mid, ring_start))
    return rings


def _project_uvs(vertices, faces):
    """Create deterministic box-projected UVs inside the unit square."""
    minimum = tuple(min(vertex[axis] for vertex in vertices) for axis in range(3))
    maximum = tuple(max(vertex[axis] for vertex in vertices) for axis in range(3))
    spans = tuple(max(maximum[axis] - minimum[axis], 1e-9) for axis in range(3))

    def normalized(vertex, axis):
        return (vertex[axis] - minimum[axis]) / spans[axis]

    face_uvs = []
    for face in faces:
        a, b, c = (vertices[index] for index in face[:3])
        normal = _cross(_subtract(b, a), _subtract(c, a))
        dominant = max(range(3), key=lambda axis: abs(normal[axis]))
        if dominant == 0:
            axes = (1, 2)
        elif dominant == 1:
            axes = (0, 2)
        else:
            axes = (0, 1)
        face_uvs.append(tuple(
            (normalized(vertices[index], axes[0]), normalized(vertices[index], axes[1]))
            for index in face
        ))
    return tuple(face_uvs)


def generate_quadruped_deformable_mesh(dimensions):
    """Return one connected quadruped mesh shaped by validated dimensions."""
    anatomy = QuadrupedFrontRecipe().resolve(dimensions)
    return _build_quadruped_mesh(dimensions, anatomy)[0]


def _build_quadruped_mesh(dimensions, anatomy):
    """One construction path, returning the mesh and its authored proof regions."""
    landmarks = {landmark.name: landmark.position for landmark in anatomy.landmarks}
    length = dimensions["body_length_cm"]
    shoulder = dimensions["shoulder_height_cm"]
    width = dimensions["body_width_cm"]
    head_length = dimensions["head_length_cm"]
    tail_length = dimensions["tail_length_cm"]

    torso_height = shoulder * 0.42
    back_z = shoulder - torso_height * 0.30
    fore_y = length * 0.32
    hind_y = -length * 0.32
    leg_height = shoulder - torso_height * 0.45
    side_x = width * 0.34
    knee_z = leg_height * 0.48

    tail_tip = (0.0, -length * 0.5 - tail_length, back_z + torso_height * 0.36)
    tail_mid = (0.0, -length * 0.5 - tail_length * 0.48, back_z + torso_height * 0.22)
    tail_base = (0.0, -length * 0.5, back_z)
    rear = landmarks["torso.rear"]
    hind = landmarks["torso.hind"]
    mid = landmarks["torso.center"]
    fore = landmarks["torso.fore"]
    chest = landmarks["chest.center"]
    neck = (0.0, length * 0.52, shoulder + torso_height * 0.05)
    head = (0.0, length * 0.5 + head_length * 0.34, shoulder + torso_height * 0.13)
    muzzle = (0.0, length * 0.5 + head_length * 0.82, shoulder + torso_height * 0.06)

    centers = (tail_tip, tail_mid, tail_base, rear, hind, mid, fore, chest, neck, head, muzzle)
    widths = (
        width * 0.08, width * 0.12, width * 0.18,
        width * 0.82, width * 0.96, width, width,
        width * 0.90, width * 0.58, width * 0.72, width * 0.48,
    )
    depths = (
        width * 0.08, width * 0.12, width * 0.18,
        torso_height * 0.82, torso_height, torso_height, torso_height * 1.04,
        torso_height * 0.94, torso_height * 0.62, torso_height * 0.72, torso_height * 0.42,
    )

    vertices, faces = [], []
    body_rings = _append_tube(vertices, faces, centers, widths, depths)
    front_rings = ()

    openings = {}
    level_by_pair = {"hind": 3, "fore": 5}
    for region, level in level_by_pair.items():
        for side, segment in (("left", 3), ("right", 7)):
            index = 1 + level * _RING_SIDES + segment
            openings[(region, side)] = faces[index]
    removed = {face for face in openings.values()}
    faces = [face for face in faces if face not in removed]

    for side, x in (("left", -side_x), ("right", side_x)):
        for region, y, top_z in (
            ("fore", fore_y, shoulder),
            ("hind", hind_y, shoulder * 0.86),
        ):
            upper = (x, y, top_z)
            knee = (x, y, knee_z)
            ankle = (x, y, max(width * 0.12, 1.5))
            paw = (x, y + width * 0.10, max(width * 0.07, 1.0))
            if (region, side) == ("fore", "left"):
                upper = landmarks["shoulder.front.left"]
                knee = landmarks["elbow.front.left"]
                ankle = landmarks["ankle.front.left"]
                paw = landmarks["paw.front.left"]
            centers_leg = (
                upper,
                _lerp(upper, knee, 0.18),
                knee,
                _lerp(knee, ankle, 0.18),
                ankle,
                paw,
            )
            base = max(width * 0.18, 2.0)
            widths_leg = (base * 1.12, base, base * 0.88, base * 0.78, base * 0.70, base * 0.94)
            depths_leg = (base * 1.12, base, base * 0.88, base * 0.78, base * 0.70, base * 0.58)
            rings = _append_branch(vertices, faces, openings[(region, side)], centers_leg, widths_leg, depths_leg)
            if (region, side) == ("fore", "left"):
                front_rings = rings

    vertices, faces = tuple(vertices), tuple(faces)
    mesh = ObjectMesh((MeshPart("quadruped", vertices, faces, _project_uvs(vertices, faces)),))
    resolved = replace(
        anatomy,
        regions=(AnatomyRegion("torso", "quadruped", tuple(i for ring in body_rings[3:8] for i in ring)),
                 AnatomyRegion("leg.front.left", "quadruped", tuple(i for ring in front_rings for i in ring))),
        connections=(replace(anatomy.connections[0],
                             boundaries=(openings[("fore", "left")], front_rings[0])),),
    )
    resolved.validate_mesh(mesh)
    return mesh, resolved
