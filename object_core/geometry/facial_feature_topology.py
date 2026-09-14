# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-specific structured facial feature topology refinement."""

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


_EPSILON = 1e-7


def _edge_key(first, second):
    return (first, second) if first < second else (second, first)


def _midpoint(first, second):
    return tuple((first[index] + second[index]) * 0.5 for index in range(len(first)))


def _is_head_vertical_edge(first, second, chin_z, crown_z):
    if abs(first[2] - second[2]) <= _EPSILON:
        return False
    low = min(first[2], second[2])
    high = max(first[2], second[2])
    return low >= chin_z - _EPSILON and high <= crown_z + _EPSILON


def _shape_feature_midpoint(vertex, proportions, chin_z, crown_z):
    x, y, z = vertex
    # Mirrored side-plane vertices can carry tiny opposite-signed floating
    # values around y == 0. Treat that whole epsilon band as non-front geometry
    # so only genuinely forward-facing feature points are shaped.
    if y <= _EPSILON:
        return vertex

    height = max(crown_z - chin_z, 1e-9)
    level = max(0.0, min(1.0, (z - chin_z) / height))
    half_width = max(proportions.head_width_cm * 0.5, 1e-9)
    lateral = max(0.0, min(1.0, abs(x) / half_width))
    center = max(0.0, 1.0 - lateral / 0.70)
    center *= center

    def bell(center_level, radius):
        distance = abs(level - center_level)
        if distance >= radius:
            return 0.0
        t = distance / radius
        smooth = t * t * (3.0 - 2.0 * t)
        return 1.0 - smooth

    depth = proportions.head_depth_cm
    mouth = bell(0.28, 0.08)
    nose = bell(0.43, 0.11)
    eye = bell(0.59, 0.09)
    brow = bell(0.70, 0.09)
    y += depth * (
        0.020 * mouth * center
        + 0.060 * nose * center
        - 0.030 * eye * (0.45 + 0.55 * center)
        + 0.022 * brow * (0.35 + 0.65 * center)
    )

    jaw = bell(0.18, 0.14)
    cheek = bell(0.45, 0.15)
    eye_width = bell(0.59, 0.10)
    x *= 1.0 - 0.035 * jaw + 0.018 * cheek - 0.012 * eye_width
    return (x, y, z)


def refine_human_facial_feature_loops(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Insert shared horizontal section loops through the Human head.

    Each original head quad is split across its two vertical edges. Shared edge
    midpoints become continuous circumference loops between the generator's
    existing head rings. Chin and crown ring edges remain untouched, so the neck
    seam and crown cap stay compatible with adjacent topology.
    """
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("facial feature refinement expects one generated ObjectMesh part")
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")

    part = mesh.parts[0]
    landmarks = generate_landmarks(proportions)
    chin_z = landmarks["chin"][2]
    crown_z = landmarks["crown"][2]

    selected_edges = set()
    for face in part.faces:
        if len(face) != 4:
            continue
        points = [part.vertices[index] for index in face]
        if min(point[2] for point in points) < chin_z - _EPSILON:
            continue
        if max(point[2] for point in points) > crown_z + _EPSILON:
            continue
        for index, first_index in enumerate(face):
            second_index = face[(index + 1) % len(face)]
            if _is_head_vertical_edge(
                part.vertices[first_index], part.vertices[second_index], chin_z, crown_z
            ):
                selected_edges.add(_edge_key(first_index, second_index))

    if not selected_edges:
        return mesh

    vertices = list(part.vertices)
    edge_vertices = {}
    for first_index, second_index in sorted(selected_edges):
        midpoint = _midpoint(part.vertices[first_index], part.vertices[second_index])
        midpoint = _shape_feature_midpoint(midpoint, proportions, chin_z, crown_z)
        edge_vertices[(first_index, second_index)] = len(vertices)
        vertices.append(midpoint)

    faces = []
    uvs = []
    for face_index, face in enumerate(part.faces):
        face_uvs = part.uvs[face_index] if part.uvs else ()
        if len(face) != 4:
            faces.append(face)
            if part.uvs:
                uvs.append(face_uvs)
            continue

        a, b, c, d = face
        ab = edge_vertices.get(_edge_key(a, b))
        bc = edge_vertices.get(_edge_key(b, c))
        cd = edge_vertices.get(_edge_key(c, d))
        da = edge_vertices.get(_edge_key(d, a))
        names = {
            name
            for name, index in (("ab", ab), ("bc", bc), ("cd", cd), ("da", da))
            if index is not None
        }

        if names == {"ab", "cd"}:
            faces.extend(((a, ab, cd, d), (ab, b, c, cd)))
            if part.uvs:
                ua, ub, uc, ud = face_uvs
                uab = _midpoint(ua, ub)
                ucd = _midpoint(uc, ud)
                uvs.extend(((ua, uab, ucd, ud), (uab, ub, uc, ucd)))
        elif names == {"bc", "da"}:
            faces.extend(((a, b, bc, da), (da, bc, c, d)))
            if part.uvs:
                ua, ub, uc, ud = face_uvs
                ubc = _midpoint(ub, uc)
                uda = _midpoint(ud, ua)
                uvs.extend(((ua, ub, ubc, uda), (uda, ubc, uc, ud)))
        else:
            faces.append(face)
            if part.uvs:
                uvs.append(face_uvs)

    refined = MeshPart(
        part.name,
        tuple(vertices),
        tuple(faces),
        tuple(uvs) if part.uvs else (),
    )
    return ObjectMesh((refined,))
