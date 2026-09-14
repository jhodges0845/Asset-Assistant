# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic head-only topology refinement for generated Human meshes."""

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


def _average(points):
    count = float(len(points))
    return tuple(sum(point[index] for point in points) / count for index in range(len(points[0])))


def _smoothstep(edge0, edge1, value):
    if edge0 == edge1:
        return 0.0
    amount = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return amount * amount * (3.0 - 2.0 * amount)


def _bell(value, center, radius):
    distance = abs(value - center)
    if distance >= radius:
        return 0.0
    return 1.0 - _smoothstep(0.0, radius, distance)


def _shape_support_vertex(vertex, proportions, chin_z, crown_z, bounds):
    """Shape one interior face support point into neutral Human anatomy.

    Only support vertices added by this refinement pass are moved. Original head
    ring vertices remain unchanged so the established silhouette, watertight
    boundary edges and body topology stay stable while the face gains local
    contour for eyes, brow, nose, mouth, cheeks and jaw.
    """
    x, y, z = vertex
    if y <= 0.0:
        return vertex

    height = max(crown_z - chin_z, 1e-9)
    half_width = max(proportions.head_width_cm * 0.5, 1e-9)
    depth = proportions.head_depth_cm
    level = max(0.0, min(1.0, (z - chin_z) / height))
    lateral = max(0.0, min(1.0, abs(x) / half_width))
    center = _bell(lateral, 0.0, 0.62)
    eye_band = _bell(lateral, 0.48, 0.34)
    cheek_band = _bell(lateral, 0.62, 0.34)

    # The support levels land between the original profile rings: roughly jaw,
    # mouth, nose/cheek, eye, brow and forehead. Shaping these interior points
    # creates local contour rather than pushing an entire 8-sided head ring.
    forward = (
        _bell(level, 0.18, 0.11) * 0.012 * center
        + _bell(level, 0.31, 0.10) * 0.045 * center
        + _bell(level, 0.45, 0.12) * 0.105 * center
        + _bell(level, 0.45, 0.14) * 0.030 * cheek_band
        - _bell(level, 0.59, 0.11) * 0.060 * eye_band
        + _bell(level, 0.73, 0.11) * 0.040 * eye_band
    )
    y += depth * forward

    # Lower-face taper plus cheek prominence gives the front view an actual jaw
    # and cheek break. The change is intentionally restrained because character
    # identity still belongs to semantic edits such as tapered/strong jaw and
    # high/soft cheeks.
    width_scale = (
        1.0
        - _bell(level, 0.18, 0.14) * 0.060
        + _bell(level, 0.45, 0.16) * 0.035 * cheek_band
        - _bell(level, 0.59, 0.12) * 0.018 * eye_band
    )
    x *= width_scale

    # Support vertices must never become new global extrema. Keeping them inside
    # the original generated bounds preserves dimensions and export assumptions.
    min_x, max_x, min_y, max_y = bounds
    x = max(min_x, min(max_x, x))
    y = max(min_y, min(max_y, y))
    return (x, y, z)


def refine_human_facial_topology(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Add and shape local support vertices without splitting boundary edges.

    The base generator remains responsible for anatomy, proportions and the
    unified body surface. This pass increases local topology between chin and
    crown so later face/jaw/cheek operations have smaller, more controllable
    regions to work with. Each refined quad gains one interior support vertex
    and becomes four triangles; the original quad boundary edges stay intact,
    preserving watertight connectivity to neighboring neck/head faces.
    """
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("facial refinement expects one generated ObjectMesh part")
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")

    part = mesh.parts[0]
    landmarks = generate_landmarks(proportions)
    chin_z = landmarks["chin"][2]
    crown_z = landmarks["crown"][2]
    bounds = (
        min(vertex[0] for vertex in part.vertices),
        max(vertex[0] for vertex in part.vertices),
        min(vertex[1] for vertex in part.vertices),
        max(vertex[1] for vertex in part.vertices),
    )

    vertices = list(part.vertices)
    faces = []
    uvs = []

    for face_index, face in enumerate(part.faces):
        points = [part.vertices[index] for index in face]
        refine = (
            len(face) == 4
            and min(point[2] for point in points) >= chin_z - 1e-7
            and max(point[2] for point in points) <= crown_z + 1e-7
        )
        face_uvs = part.uvs[face_index] if part.uvs else ()
        if not refine:
            faces.append(face)
            if part.uvs:
                uvs.append(face_uvs)
            continue

        a, b, c, d = face
        center = len(vertices)
        support = _average((part.vertices[a], part.vertices[b], part.vertices[c], part.vertices[d]))
        vertices.append(_shape_support_vertex(support, proportions, chin_z, crown_z, bounds))
        faces.extend(((a, b, center), (b, c, center), (c, d, center), (d, a, center)))

        if part.uvs:
            ua, ub, uc, ud = face_uvs
            ucenter = _average((ua, ub, uc, ud))
            uvs.extend(((ua, ub, ucenter), (ub, uc, ucenter), (uc, ud, ucenter), (ud, ua, ucenter)))

    refined = MeshPart(part.name, tuple(vertices), tuple(faces), tuple(uvs) if part.uvs else ())
    return ObjectMesh((refined,))
