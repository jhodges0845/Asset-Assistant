# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic head-only topology refinement for generated Human meshes."""

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


def _average(points):
    count = float(len(points))
    return tuple(sum(point[index] for point in points) / count for index in range(len(points[0])))


def refine_human_facial_topology(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Add local support vertices to head quads without splitting boundary edges.

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
        vertices.append(_average((part.vertices[a], part.vertices[b], part.vertices[c], part.vertices[d])))
        faces.extend(((a, b, center), (b, c, center), (c, d, center), (d, a, center)))

        if part.uvs:
            ua, ub, uc, ud = face_uvs
            ucenter = _average((ua, ub, uc, ud))
            uvs.extend(((ua, ub, ucenter), (ub, uc, ucenter), (uc, ud, ucenter), (ud, ua, ucenter)))

    refined = MeshPart(part.name, tuple(vertices), tuple(faces), tuple(uvs) if part.uvs else ())
    return ObjectMesh((refined,))
