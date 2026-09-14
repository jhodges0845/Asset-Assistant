# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic head-only topology refinement for generated Human meshes."""

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


def _midpoint(a, b):
    return tuple((a[index] + b[index]) * 0.5 for index in range(len(a)))


def _average(points):
    count = float(len(points))
    return tuple(sum(point[index] for point in points) / count for index in range(len(points[0])))


def refine_human_facial_topology(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Subdivide head-side quads while preserving the connected Human surface.

    The base generator remains responsible for anatomy, proportions and the
    unified body surface. This pass only increases local topology between chin
    and crown so later face/jaw/cheek operations have smaller, more controllable
    regions to work with. Geometry edge midpoints are shared across neighboring
    refined faces, keeping the result watertight and deterministic.
    """
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("facial refinement expects one generated ObjectMesh part")
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")

    part = mesh.parts[0]
    landmarks = generate_landmarks(proportions)
    chin_z = landmarks["chin"][2]
    crown_z = landmarks["crown"][2]

    vertices = list(part.vertices)
    faces = []
    uvs = []
    edge_midpoints = {}

    def midpoint_index(first, second):
        key = tuple(sorted((first, second)))
        if key not in edge_midpoints:
            edge_midpoints[key] = len(vertices)
            vertices.append(_midpoint(part.vertices[first], part.vertices[second]))
        return edge_midpoints[key]

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
        ab = midpoint_index(a, b)
        bc = midpoint_index(b, c)
        cd = midpoint_index(c, d)
        da = midpoint_index(d, a)
        center = len(vertices)
        vertices.append(_average((part.vertices[a], part.vertices[b], part.vertices[c], part.vertices[d])))
        faces.extend(((a, ab, center, da), (ab, b, bc, center), (center, bc, c, cd), (da, center, cd, d)))

        if part.uvs:
            ua, ub, uc, ud = face_uvs
            uab = _midpoint(ua, ub)
            ubc = _midpoint(ub, uc)
            ucd = _midpoint(uc, ud)
            uda = _midpoint(ud, ua)
            ucenter = _average((ua, ub, uc, ud))
            uvs.extend(((ua, uab, ucenter, uda), (uab, ub, ubc, ucenter), (ucenter, ubc, uc, ucd), (uda, ucenter, ucd, ud)))

    refined = MeshPart(part.name, tuple(vertices), tuple(faces), tuple(uvs) if part.uvs else ())
    return ObjectMesh((refined,))
