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
    # Sagittal bends can change the Y sign of the tangent. A fixed lateral axis
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


def _append_tube(vertices, faces, centers, widths, depths, *, cap_start=True, cap_end=True, sagittal=False, upright_from=None):
    rings = []
    for index, center in enumerate(centers):
        if upright_from is not None and index >= upright_from:
            # Facial profiles are vertical cross sections. Following the steep
            # neck bend can roll a short head's underside back through itself.
            tangent = (0.0, 1.0, 0.0)
        elif index == 0:
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
    """Bridge one body quad to an eight-sided branch with symmetric triangles."""
    if len(root) != 4:
        raise ValueError("branch root must contain four vertices")
    rings = _append_tube(vertices, faces, centers, widths, depths, cap_start=False, cap_end=True, sagittal=sagittal)
    # Match the cyclic boundary phase without changing winding or ownership.
    offset = min(range(_RING_SIDES), key=lambda shift: sum(
        sum((vertices[root[j]][k] - vertices[rings[0][(2*j+shift) % _RING_SIDES]][k])**2
            for k in range(3)) for j in range(4)))
    rings = tuple(tuple(ring[(i+offset) % _RING_SIDES] for i in range(_RING_SIDES)) for ring in rings)
    first = rings[0]
    for index in range(4):
        root_start = root[index]
        root_end = root[(index + 1) % 4]
        ring_start = first[(2 * index) % _RING_SIDES]
        ring_mid = first[(2 * index + 1) % _RING_SIDES]
        ring_end = first[(2 * index + 2) % _RING_SIDES]
        faces.append((root_start, root_end, ring_mid))
        faces.append((root_end, ring_end, ring_mid))
        faces.append((root_start, ring_mid, ring_start))
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


def _build_quadruped_cage(anatomy):
    """Construct once from resolved anatomy, binding authored region indices."""
    landmarks = {landmark.name: landmark.position for landmark in anatomy.landmarks}
    dimensions = dict(anatomy.parameters)
    width = dimensions["body_width_cm"]
    centers = tuple(landmarks[section.landmark] for section in anatomy.body_sections)
    widths = tuple(section.width_cm for section in anatomy.body_sections)
    depths = tuple(section.depth_cm for section in anatomy.body_sections)

    vertices, faces = [], []
    body_rings = _append_tube(vertices, faces, centers, widths, depths, sagittal=True, upright_from=8)
    limb_rings = {}

    openings = {}
    level_by_pair = {"hind": 3, "fore": 6}
    for region, level in level_by_pair.items():
        for side, segment in (("left", 7), ("right", 4)):
            index = 1 + level * _RING_SIDES + segment
            openings[(region, side)] = faces[index]
    ear_openings = {side: faces[1 + 8 * _RING_SIDES + segment]
                    for side, segment in (("left", 0), ("right", 3))}
    removed = set(openings.values()) | set(ear_openings.values())
    faces = [face for face in faces if face not in removed]

    for side in ("left", "right"):
        for region, family, upper_name, joint_name in (
            ("fore", "front", "shoulder", "elbow"), ("hind", "hind", "hip", "knee"),
        ):
            suffix = family + "." + side
            upper = landmarks[upper_name + "." + suffix]
            # The surface starts at the body opening; the rig shoulder/hip
            # remains its anatomical pivot above that opening.
            root = openings[(region, side)]
            upper = (upper[0], upper[1], sum(vertices[i][2] for i in root) / len(root))
            knee = landmarks[joint_name + "." + suffix]
            paw = landmarks["paw." + suffix]
            base = max(width * 0.24, 2.0)
            if family == "hind":
                hock = landmarks["hock." + suffix]
                base = min(base, dimensions["shoulder_height_cm"] * .13)
                centers_leg = (upper, _lerp(upper, knee, .35), knee,
                               _lerp(knee, hock, .25), hock,
                               _lerp(hock, paw, .25), _lerp(hock, paw, .80), paw)
                widths_leg = tuple(base * v for v in (1.6, 1.45, .95, .85, .60, .55, .85, 1.35))
                depths_leg = tuple(base * v for v in (1.4, 1.25, .90, .78, .60, .55, .65, .80))
            else:
                ankle = landmarks["ankle." + suffix]
                centers_leg = (upper, _lerp(upper, knee, .18), knee,
                               _lerp(knee, ankle, .18), ankle, paw)
                widths_leg = tuple(base * v for v in (1.50, 1.20, .88, .78, .85, 1.35))
                depths_leg = tuple(base * v for v in (1.40, 1.15, .88, .78, .65, .80))
            rings = _append_branch(vertices, faces, openings[(region, side)], centers_leg,
                                   widths_leg, depths_leg, sagittal=family == "hind")
            limb_rings["leg." + suffix] = rings

    ear_rings = {}
    for side in ("left", "right"):
        base = landmarks["ear.base." + side]
        tip = landmarks["ear.tip." + side]
        size = dimensions["head_length_cm"]
        ear_rings["ear." + side] = _append_branch(
            vertices, faces, ear_openings[side],
            (base, _lerp(base, tip, .55), _lerp(base, tip, .90), tip),
            (size*.25, size*.20, size*.07, size*.02),
            (size*.12, size*.07, size*.035, size*.015))

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
    memberships.update({name: indices(rings) for name, rings in ear_rings.items()})
    memberships["head"] += tuple(i for rings in ear_rings.values() for ring in rings for i in ring)
    connections = []
    for connection in anatomy.connections:
        name = connection.regions[1]
        if name.startswith("ear."):
            side = name.split(".")[1]
            connections.append(replace(connection, boundaries=(ear_openings[side], ear_rings[name][0])))
            continue
        _, family, side = name.split(".")
        region = "fore" if family == "front" else "hind"
        connections.append(replace(connection, boundaries=(openings[(region, side)], limb_rings[name][0])))
    resolved = replace(anatomy,
                       regions=tuple(AnatomyRegion(r.name, r.mesh_part, memberships[r.name]) for r in anatomy.regions),
                       connections=tuple(connections))
    resolved.validate_mesh(mesh)
    return mesh, resolved


def _ground_paw_surfaces(vertices, anatomy):
    """Resolve refined soles to recipe ground below fixed ankle/hock heights.

    Subdivision lifts the capped paw ends. A monotone height map below the
    ankle/hock restores contact, with unit slope at that fixed transition.
    A cubic sole profile broadens the near-ground underside without flattening
    faces: its derivative is positive above the sole and one at the transition.
    Only authored limb vertices participate; this runs during construction,
    never on an artist-edited surface or during semantic Modify.
    """
    result = list(vertices)
    points = {point.name: point.position for point in anatomy.landmarks}
    for region in anatomy.regions:
        if not region.name.startswith('leg.'):
            continue
        suffix = region.name[4:]
        ground = points['ground.' + suffix][2]
        upper = points[('ankle.' if suffix.startswith('front.') else 'hock.') + suffix][2]
        lowest = min(vertices[i][2] for i in region.vertex_indices)
        if not lowest < upper or not ground < upper:
            raise ValueError('Paw contact requires a sole below the ankle/hock')
        if lowest == ground:
            continue
        span = upper - lowest
        ratio = span / (upper - ground)
        for index in region.vertex_indices:
            x, y, z = vertices[index]
            if z >= upper:
                continue
            t = (z - lowest) / span
            # Positive denominator and derivative preserve vertical ordering.
            # Unlike clamping, this does not collapse sole faces to a plane.
            height = ground + (upper - ground) * t / (ratio + (1 - ratio) * t)
            sole = (height - ground) / (upper - ground)
            height = ground + (upper - ground) * sole * sole * (2 - sole)
            result[index] = (x, y, height)
    return tuple(result)


def _build_quadruped_mesh(anatomy):
    """Build and refine the one canonical canine surface, retaining ownership."""
    from .quadruped_refinement import refine_canine_surface
    cage, resolved = _build_quadruped_cage(anatomy)
    mesh, resolved = refine_canine_surface(cage, resolved)
    part = mesh.parts[0]
    vertices = _ground_paw_surfaces(part.vertices, resolved)
    result = ObjectMesh((MeshPart(part.name, vertices, part.faces,
                                  _project_uvs(vertices, part.faces)),))
    resolved.validate_mesh(result)
    return result, resolved
