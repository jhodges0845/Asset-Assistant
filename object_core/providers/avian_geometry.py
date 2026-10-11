# SPDX-License-Identifier: GPL-3.0-or-later
"""Connected Avian surface generation."""

from dataclasses import replace

from ..anatomy import AnatomyConnection, AnatomyRegion
from .avian_anatomy import AvianRecipe

from math import cos, pi, sin, sqrt

from ..models import MeshPart, ObjectMesh


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


def generate_avian_deformable_mesh(dimensions):
    """Compatibility entry point using the single Avian recipe constructor."""
    return _build_avian_mesh(AvianRecipe().resolve(dimensions))[0]


def _build_avian_mesh(anatomy):
    """Bind authored surface ownership and attachment boundaries to the recipe."""
    points = {p.name: p.position for p in anatomy.landmarks}
    vertices, faces = [], []
    body = anatomy.tubes[0]
    _append_tube(vertices, faces, tuple(points[n] for n in body.landmarks), body.widths, body.depths)
    regions = [AnatomyRegion('body', 'avian', tuple(range(len(vertices))))]
    openings = {
        "wing.left": faces[1 + 4 * _RING_SIDES + 3],
        "wing.right": faces[1 + 4 * _RING_SIDES + 7],
        "leg.left": faces[1 + 3 * _RING_SIDES + 7],
        "leg.right": faces[1 + 3 * _RING_SIDES + 4],
    }
    removed = set(openings.values())
    faces = [face for face in faces if face not in removed]
    connections = []
    for tube in anatomy.tubes[1:]:
        start = len(vertices)
        _append_branch(vertices, faces, openings[tube.name],
                       tuple(points[n] for n in tube.landmarks), tube.widths, tube.depths)
        regions.append(AnatomyRegion(tube.name, 'avian', tuple(range(start, len(vertices)))))
        connections.append(AnatomyConnection('body.' + tube.name, ('body', tube.name), 'connected',
                           (openings[tube.name], tuple(range(start, start + _RING_SIDES)))))
    vertices, faces = tuple(vertices), tuple(faces)
    mesh = ObjectMesh((MeshPart('avian', vertices, faces, _project_uvs(vertices, faces)),))
    bound = replace(anatomy, regions=regions, connections=connections)
    bound.validate_mesh(mesh)
    return mesh, bound
