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


def _ring(center, width, depth, tangent, *, stable_width=False):
    tangent = _normalize(tangent)
    reference = (0.0, 0.0, 1.0)
    if abs(sum(tangent[i] * reference[i] for i in range(3))) > 0.95:
        reference = (0.0, 1.0, 0.0)
    width_axis = _normalize(_cross(reference, tangent))
    if stable_width:
        # Project lateral X onto the section plane so near-vertical legs do not
        # switch reference axes between neighboring rings.
        width_axis = _normalize(tuple((1.0 if i == 0 else 0.0) - tangent[0] * tangent[i] for i in range(3)))
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


def _append_tube(vertices, faces, centers, widths, depths, *, cap_start=True, cap_end=True, stable_width=False, ground_end=False):
    rings = []
    for index, center in enumerate(centers):
        if index == 0:
            tangent = _subtract(centers[1], center)
        elif index == len(centers) - 1:
            tangent = _subtract(center, centers[index - 1])
        else:
            tangent = _subtract(centers[index + 1], centers[index - 1])
        start = len(vertices)
        vertices.extend(_ring(center, widths[index], depths[index], tangent, stable_width=stable_width))
        rings.append(tuple(range(start, start + _RING_SIDES)))
        if ground_end and index >= len(centers) - 2:
            # Authored plantar arc of ankle/toe rings forms a finite flat sole.
            # For the leg's lateral frame, positive ring sine points downward.
            for segment in (1, 2, 3):
                x, y, _ = vertices[start + segment]
                vertices[start + segment] = (x, y, 0.0)

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


def _append_toes(vertices, faces, ring, center, width, depth, length):
    """Split the foot end into three quad openings and extrude tapered digits."""
    # Ordered perimeter of a rectangular section with three width bands.
    # Consecutive openings share root edges, keeping the foot one closed surface.
    top = center[2] + depth * .5
    profile = ((.5, top), (.5, 0), (1/6, 0), (-1/6, 0),
               (-.5, 0), (-.5, top), (-1/6, top), (1/6, top))
    for i, (offset, z) in zip(ring, profile):
        vertices[i] = (center[0] + width * offset, center[1], z)
    caps = []
    for digit, slots in enumerate(((0, 1, 2, 7), (7, 2, 3, 6), (6, 3, 4, 5))):
        root = tuple(ring[i] for i in slots)
        middle_x = sum(vertices[i][0] for i in root) / 4
        extension = length * (1.0 if digit == 1 else .82)
        spread = (1 - digit) * width * .30
        end = []
        for i in root:
            x, y, z = vertices[i]
            end.append(len(vertices))
            vertices.append((middle_x + (x - middle_x) * .55 + spread,
                             y + extension, z * .55))
        for j in range(4):
            nxt = (j + 1) % 4
            faces.append((root[j], root[nxt], end[nxt], end[j]))
        faces.append(tuple(end))
        caps.append(tuple(end))
    return caps


def _append_rear_toe(vertices, faces, rings, centers, widths, length):
    """Extrude a rear-facing lower-leg quad into one connected support digit."""
    knee, ankle = rings[2], rings[3]
    sector = 1 if centers[3][0] < 0 else 2
    root = (knee[sector], knee[sector + 1], ankle[sector + 1], ankle[sector])
    faces.remove(root)
    # Inset the opening near the ankle so the whole shin does not become a web.
    inner = []
    for across, down in ((.25, .65), (.75, .65), (.75, .95), (.25, .95)):
        inner.append(len(vertices))
        vertices.append(tuple(
            (1 - down) * ((1 - across) * vertices[root[0]][axis] + across * vertices[root[1]][axis])
            + down * ((1 - across) * vertices[root[3]][axis] + across * vertices[root[2]][axis])
            for axis in range(3)))
    for j in range(4):
        nxt = (j + 1) % 4
        faces.append((root[j], root[nxt], inner[nxt], inner[j]))
    root = tuple(inner)
    x, y, z = centers[3]
    half_width = widths[3] * .18
    end = tuple(range(len(vertices), len(vertices) + 4))
    vertices.extend(((x + half_width, y - length, z * .40),
                     (x - half_width, y - length, z * .40),
                     (x - half_width, y - length, 0.0),
                     (x + half_width, y - length, 0.0)))
    for j in range(4):
        nxt = (j + 1) % 4
        faces.append((root[j], root[nxt], end[nxt], end[j]))
    faces.append(end)
    return end


def _append_claw(vertices, faces, root, length, direction):
    """Replace a toe cap with a raised taper ending above the sole plane."""
    faces.remove(root)
    center = tuple(sum(vertices[i][a] for i in root) / 4 for a in range(3))
    height = max(vertices[i][2] for i in root)
    shoulder = []
    for i in root:
        x, y, z = vertices[i]
        shoulder.append(len(vertices))
        vertices.append((center[0] + (x - center[0]) * .45,
                         center[1] + direction * length * .55,
                         height * .60 + (z - center[2]) * .35))
    tip = len(vertices)
    vertices.append((center[0], center[1] + direction * length, height * .15))
    for j in range(4):
        nxt = (j + 1) % 4
        faces.append((root[j], root[nxt], shoulder[nxt], shoulder[j]))
        faces.append((shoulder[j], shoulder[nxt], tip))


def _append_branch(vertices, faces, root, centers, widths, depths, *, stable_width=False, ground_end=False, toe_length=0.0, rear_toe_length=0.0, claw_length=0.0):
    if len(root) != 4:
        raise ValueError("branch root must contain four vertices")
    rings = _append_tube(vertices, faces, centers, widths, depths, cap_start=False, cap_end=not toe_length, stable_width=stable_width, ground_end=ground_end)
    digits = []
    if toe_length:
        digits.extend((cap, 1) for cap in _append_toes(
            vertices, faces, rings[-1], centers[-1], widths[-1], depths[-1], toe_length))
    if rear_toe_length:
        digits.append((_append_rear_toe(vertices, faces, rings, centers, widths, rear_toe_length), -1))
    if claw_length:
        for cap, direction in digits:
            _append_claw(vertices, faces, cap, claw_length, direction)
    first = rings[0]
    # Match perimeter phase without reversing the tube's outward winding.
    phase = min(range(_RING_SIDES), key=lambda offset: sum(
        sum((vertices[root[i]][axis] - vertices[first[(2 * i + offset) % _RING_SIDES]][axis]) ** 2
            for axis in range(3)) for i in range(4)))
    first = first[phase:] + first[:phase]
    for index in range(4):
        root_start = root[index]
        root_end = root[(index + 1) % 4]
        ring_start = first[(2 * index) % _RING_SIDES]
        ring_mid = first[(2 * index + 1) % _RING_SIDES]
        ring_end = first[(2 * index + 2) % _RING_SIDES]
        if stable_width or index in (0, 1):
            # Use the ring-side diagonal for leg collars and the leading
            # wing collar sectors, reducing fold-induced shoulder crossings.
            faces.append((root_start, root_end, ring_end, ring_mid))
            faces.append((root_start, ring_mid, ring_start))
        else:
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
        "wing.left": faces[1 + 4 * _RING_SIDES + 0],
        "wing.right": faces[1 + 4 * _RING_SIDES + 3],
        "leg.left": faces[1 + 3 * _RING_SIDES + 6],
        "leg.right": faces[1 + 3 * _RING_SIDES + 5],
    }
    removed = set(openings.values())
    faces = [face for face in faces if face not in removed]
    connections = []
    for tube in anatomy.tubes[1:]:
        start = len(vertices)
        _append_branch(vertices, faces, openings[tube.name],
                       tuple(points[n] for n in tube.landmarks), tube.widths, tube.depths,
                       stable_width=tube.name.startswith('leg.'), ground_end=tube.name.startswith('leg.'), toe_length=tube.toe_length, rear_toe_length=tube.rear_toe_length, claw_length=tube.claw_length)
        regions.append(AnatomyRegion(tube.name, 'avian', tuple(range(start, len(vertices)))))
        connections.append(AnatomyConnection('body.' + tube.name, ('body', tube.name), 'connected',
                           (openings[tube.name], tuple(range(start, start + _RING_SIDES)))))
    vertices, faces = tuple(vertices), tuple(faces)
    mesh = ObjectMesh((MeshPart('avian', vertices, faces, _project_uvs(vertices, faces)),))
    bound = replace(anatomy, regions=regions, connections=connections)
    bound.validate_mesh(mesh)
    return mesh, bound
