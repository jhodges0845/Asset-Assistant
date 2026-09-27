# SPDX-License-Identifier: GPL-3.0-or-later
"""Connected quadruped surface generation."""

from dataclasses import replace
from math import cos, pi, sin, sqrt

from ..models import MeshPart, ObjectMesh
from ..anatomy import AnatomyRegion
from .quadruped_anatomy import CanineRecipe


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


def _ring(center, width, depth, tangent, *, sagittal=False):
    tangent = _normalize(tangent)
    reference = (0.0, 0.0, 1.0)
    if abs(sum(tangent[i] * reference[i] for i in range(3))) > 0.95:
        reference = (0.0, 1.0, 0.0)
    # Hind-leg bends change the Y sign of the tangent. A fixed lateral axis
    # prevents a 180-degree frame flip between knee and hock rings.
    width_axis = (-1.0, 0.0, 0.0) if sagittal else _normalize(_cross(reference, tangent))
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


def _append_tube(vertices, faces, centers, widths, depths, *, cap_start=True, cap_end=True, sagittal=False):
    rings = []
    for index, center in enumerate(centers):
        if index == 0:
            tangent = _subtract(centers[1], center)
        elif index == len(centers) - 1:
            tangent = _subtract(center, centers[index - 1])
        elif sagittal:
            # Bisect the two segment directions rather than weighting by their
            # unequal lengths. A long incoming segment otherwise tilts the hock
            # ring back across its short outgoing support section.
            incoming = _normalize(_subtract(center, centers[index - 1]))
            outgoing = _normalize(_subtract(centers[index + 1], center))
            tangent = tuple(a + b for a, b in zip(incoming, outgoing))
        else:
            tangent = _subtract(centers[index + 1], centers[index - 1])
        start = len(vertices)
        vertices.extend(_ring(center, widths[index], depths[index], tangent, sagittal=sagittal))
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


def _append_branch(vertices, faces, root, centers, widths, depths, *, sagittal=False):
    """Replace one torso quad with an eight-sided deformable limb chain."""
    if len(root) != 4:
        raise ValueError("branch root must contain four vertices")
    rings = _append_tube(vertices, faces, centers, widths, depths, cap_start=False, cap_end=True, sagittal=sagittal)
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
    anatomy = CanineRecipe().resolve(dimensions)
    return _build_quadruped_mesh(anatomy)[0]


def _build_quadruped_mesh(anatomy):
    """Construct once from resolved anatomy, binding authored region indices."""
    landmarks = {landmark.name: landmark.position for landmark in anatomy.landmarks}
    dimensions = dict(anatomy.parameters)
    width = dimensions["body_width_cm"]
    torso_height = dimensions["shoulder_height_cm"] * 0.42
    centers = tuple(landmarks[name] for name in (
        "tail.tip", "tail.mid", "tail.base", "torso.rear", "torso.hind",
        "torso.center", "torso.fore", "chest.center", "neck.center", "head.center", "muzzle.tip"))
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
    limb_rings = {}

    openings = {}
    level_by_pair = {"hind": 3, "fore": 5}
    for region, level in level_by_pair.items():
        for side, segment in (("left", 3), ("right", 7)):
            index = 1 + level * _RING_SIDES + segment
            openings[(region, side)] = faces[index]
    removed = {face for face in openings.values()}
    faces = [face for face in faces if face not in removed]

    for side in ("left", "right"):
        for region, family, upper_name, joint_name in (
            ("fore", "front", "shoulder", "elbow"), ("hind", "hind", "hip", "knee"),
        ):
            suffix = family + "." + side
            upper = landmarks[upper_name + "." + suffix]
            knee = landmarks[joint_name + "." + suffix]
            paw = landmarks["paw." + suffix]
            base = max(width * 0.18, 2.0)
            if family == "hind":
                hock = landmarks["hock." + suffix]
                base = min(base, dimensions["shoulder_height_cm"] * .13)
                centers_leg = (upper, _lerp(upper, knee, .35), knee,
                               _lerp(knee, hock, .25), hock,
                               _lerp(hock, paw, .25), _lerp(hock, paw, .80), paw)
                widths_leg = tuple(base * v for v in (1.6, 1.45, .95, .85, .60, .55, .72, .95))
                depths_leg = tuple(base * v for v in (1.4, 1.25, .90, .78, .60, .55, .60, .58))
            else:
                ankle = landmarks["ankle." + suffix]
                centers_leg = (upper, _lerp(upper, knee, .18), knee,
                               _lerp(knee, ankle, .18), ankle, paw)
                widths_leg = tuple(base * v for v in (1.12, 1, .88, .78, .70, .94))
                depths_leg = tuple(base * v for v in (1.12, 1, .88, .78, .70, .58))
            rings = _append_branch(vertices, faces, openings[(region, side)], centers_leg,
                                   widths_leg, depths_leg, sagittal=family == "hind")
            limb_rings["leg." + suffix] = rings

    vertices, faces = tuple(vertices), tuple(faces)
    mesh = ObjectMesh((MeshPart("quadruped", vertices, faces, _project_uvs(vertices, faces)),))
    def indices(rings):
        return tuple(i for ring in rings for i in ring)

    memberships = {
        "body": tuple(range(len(vertices))), "torso": indices(body_rings[3:8]),
        "chest": indices(body_rings[6:8]), "waist": indices(body_rings[4:6]),
        "head": indices(body_rings[8:]), "muzzle": indices(body_rings[10:]),
        "tail": indices(body_rings[:3]),
    }
    memberships.update({name: indices(rings) for name, rings in limb_rings.items()})
    connections = []
    for connection in anatomy.connections:
        name = connection.regions[1]
        _, family, side = name.split(".")
        region = "fore" if family == "front" else "hind"
        connections.append(replace(connection, boundaries=(openings[(region, side)], limb_rings[name][0])))
    resolved = replace(anatomy,
                       regions=tuple(AnatomyRegion(r.name, r.mesh_part, memberships[r.name]) for r in anatomy.regions),
                       connections=tuple(connections))
    resolved.validate_mesh(mesh)
    return mesh, resolved
