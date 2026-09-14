# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-specific cranium cross-section refinement."""

from math import cos, pi

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


_EPSILON = 1e-7
_OCTAGON_CHORD_CORRECTION = 1.0 / cos(pi / 8.0)


def _edge_key(first, second):
    return (first, second) if first < second else (second, first)


def _midpoint(first, second):
    return tuple((first[index] + second[index]) * 0.5 for index in range(len(first)))


def _eligible_head_edge(first, second, chin_z, crown_z):
    """Return whether an edge is an interior horizontal cranium-ring chord."""
    if abs(first[2] - second[2]) > _EPSILON:
        return False
    z = (first[2] + second[2]) * 0.5
    return chin_z + _EPSILON < z < crown_z - _EPSILON


def refine_human_cranium_cross_sections(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Round generated Human head-ring chords without changing the neck seam.

    The Human head is still organized around eight-point horizontal sections.
    Facial refinement already adds local interior support, so this pass runs
    after it and touches only surviving horizontal boundary chords. Each chord
    gains one shared midpoint projected radially toward the original ellipse.
    New points are clamped inside the pre-refinement head bounds so standing
    height, head width/depth and export assumptions remain unchanged.
    """
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("cranium refinement expects one generated ObjectMesh part")
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")

    part = mesh.parts[0]
    landmarks = generate_landmarks(proportions)
    chin_z = landmarks["chin"][2]
    crown_z = landmarks["crown"][2]

    head_vertices = [vertex for vertex in part.vertices if chin_z - _EPSILON <= vertex[2] <= crown_z + _EPSILON]
    if not head_vertices:
        return mesh
    min_x = min(vertex[0] for vertex in head_vertices)
    max_x = max(vertex[0] for vertex in head_vertices)
    min_y = min(vertex[1] for vertex in head_vertices)
    max_y = max(vertex[1] for vertex in head_vertices)

    selected_edges = set()
    for face in part.faces:
        for index, first_index in enumerate(face):
            second_index = face[(index + 1) % len(face)]
            first = part.vertices[first_index]
            second = part.vertices[second_index]
            if _eligible_head_edge(first, second, chin_z, crown_z):
                selected_edges.add(_edge_key(first_index, second_index))

    if not selected_edges:
        return mesh

    vertices = list(part.vertices)
    edge_vertices = {}
    for first_index, second_index in sorted(selected_edges):
        first = part.vertices[first_index]
        second = part.vertices[second_index]
        x, y, z = _midpoint(first, second)
        corrected = (
            max(min_x, min(max_x, x * _OCTAGON_CHORD_CORRECTION)),
            max(min_y, min(max_y, y * _OCTAGON_CHORD_CORRECTION)),
            z,
        )
        edge = (first_index, second_index)
        edge_vertices[edge] = len(vertices)
        vertices.append(corrected)

    faces = []
    uvs = []
    for face_index, face in enumerate(part.faces):
        face_uvs = part.uvs[face_index] if part.uvs else ()
        refined_face = []
        refined_uvs = []
        for index, first_index in enumerate(face):
            second_index = face[(index + 1) % len(face)]
            refined_face.append(first_index)
            if part.uvs:
                refined_uvs.append(face_uvs[index])

            midpoint_index = edge_vertices.get(_edge_key(first_index, second_index))
            if midpoint_index is None:
                continue
            refined_face.append(midpoint_index)
            if part.uvs:
                refined_uvs.append(_midpoint(face_uvs[index], face_uvs[(index + 1) % len(face)]))

        faces.append(tuple(refined_face))
        if part.uvs:
            uvs.append(tuple(refined_uvs))

    refined = MeshPart(part.name, tuple(vertices), tuple(faces), tuple(uvs) if part.uvs else ())
    return ObjectMesh((refined,))
