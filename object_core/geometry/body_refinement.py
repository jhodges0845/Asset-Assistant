# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-specific neutral body topology refinement."""

from math import cos, pi

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


_EPSILON = 1e-7
# The current Human torso is generated from eight-point rings. A midpoint on
# one ring chord reaches the corresponding ellipse at this radial correction.
_OCTAGON_CHORD_CORRECTION = 1.0 / cos(pi / 8.0)


def _edge_key(first, second):
    return (first, second) if first < second else (second, first)


def _midpoint(first, second):
    return tuple((first[index] + second[index]) * 0.5 for index in range(len(first)))


def _eligible_torso_edge(first, second, hip_z, shoulder_z):
    """Return whether an edge is a horizontal interior torso-ring chord."""
    if abs(first[2] - second[2]) > _EPSILON:
        return False
    z = (first[2] + second[2]) * 0.5
    # Keep the actual hip and shoulder opening rings unchanged. This first
    # refinement slice deliberately improves the torso between those branch
    # seams without changing limb stitching assumptions.
    return hip_z + _EPSILON < z < shoulder_z - _EPSILON


def refine_human_torso_cross_sections(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Add curved support points to the generated Human torso silhouette.

    The base generator currently uses eight-sided horizontal torso rings. This
    pass splits only the circumferential chords between the hip and shoulder
    seams and projects their new midpoint onto the corresponding ellipse. It
    therefore doubles visible cross-sectional silhouette resolution where the
    torso looked most box-like while preserving the existing hip/shoulder
    openings, branch stitching, overall bounds and provider architecture.

    Geometry midpoints are shared by every adjacent face. UV midpoints remain
    face-local, matching the existing atlas contract.
    """
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("torso refinement expects one generated ObjectMesh part")
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")

    part = mesh.parts[0]
    landmarks = generate_landmarks(proportions)
    hip_z = landmarks["hip_center"][2]
    shoulder_z = landmarks["shoulder_center"][2]

    selected_edges = set()
    for face in part.faces:
        for index, first_index in enumerate(face):
            second_index = face[(index + 1) % len(face)]
            first = part.vertices[first_index]
            second = part.vertices[second_index]
            if _eligible_torso_edge(first, second, hip_z, shoulder_z):
                selected_edges.add(_edge_key(first_index, second_index))

    if not selected_edges:
        return mesh

    vertices = list(part.vertices)
    edge_vertices = {}
    for first_index, second_index in sorted(selected_edges):
        first = part.vertices[first_index]
        second = part.vertices[second_index]
        x, y, z = _midpoint(first, second)
        # Torso rings are centered on the model origin. Correcting the chord
        # midpoint radially places the new vertex on the original ellipse rather
        # than leaving the silhouette on the old octagonal flat.
        vertex = (
            x * _OCTAGON_CHORD_CORRECTION,
            y * _OCTAGON_CHORD_CORRECTION,
            z,
        )
        edge_vertices[(first_index, second_index)] = len(vertices)
        vertices.append(vertex)

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

            edge = _edge_key(first_index, second_index)
            midpoint_index = edge_vertices.get(edge)
            if midpoint_index is None:
                continue
            refined_face.append(midpoint_index)
            if part.uvs:
                refined_uvs.append(_midpoint(face_uvs[index], face_uvs[(index + 1) % len(face)]))

        faces.append(tuple(refined_face))
        if part.uvs:
            uvs.append(tuple(refined_uvs))

    refined = MeshPart(
        part.name,
        tuple(vertices),
        tuple(faces),
        tuple(uvs) if part.uvs else (),
    )
    return ObjectMesh((refined,))
