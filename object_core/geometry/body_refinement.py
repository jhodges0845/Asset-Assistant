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


def _eligible_torso_edge(first, second, hip_z, shoulder_z):
    """Return whether an edge is a horizontal interior torso-ring chord."""
    if abs(first[2] - second[2]) > _EPSILON:
        return False
    z = (first[2] + second[2]) * 0.5
    # Keep the actual hip and shoulder opening rings unchanged. This refinement
    # improves the torso between those branch seams without changing limb
    # stitching assumptions.
    return hip_z + _EPSILON < z < shoulder_z - _EPSILON


def _shape_anatomical_torso(vertex, proportions, hip_z, shoulder_z):
    """Give the neutral torso directional ribcage/waist/pelvis contour.

    This deliberately is not another radial subdivision pass. Front, back and
    side surfaces receive different restrained contour so the connected torso
    reads as ribcage -> waist -> pelvis rather than a stack of box-like rings.
    The hip and shoulder seam planes themselves are left unchanged.
    """
    x, y, z = vertex
    torso_height = max(shoulder_z - hip_z, 1e-9)
    if z <= hip_z + _EPSILON or z >= shoulder_z - _EPSILON:
        return vertex

    level = max(0.0, min(1.0, (z - hip_z) / torso_height))
    half_width = max(proportions.shoulder_width_cm * 0.5, proportions.hip_width_cm * 0.5, 1e-9)
    half_depth = max(proportions.chest_depth_cm * 0.5, proportions.hip_depth_cm * 0.5, 1e-9)
    lateral = max(0.0, min(1.0, abs(x) / half_width))
    depthward = max(0.0, min(1.0, abs(y) / half_depth))

    pelvis = _bell(level, 0.12, 0.20)
    waist = _bell(level, 0.34, 0.22)
    ribcage = _bell(level, 0.68, 0.28)
    upper_chest = _bell(level, 0.84, 0.16)

    # Side contour: retain hip breadth, define the waist, then open into the
    # lower ribcage before easing back toward the shoulder seam.
    side_scale = 1.0 + 0.035 * pelvis - 0.055 * waist + 0.035 * ribcage - 0.018 * upper_chest
    x *= side_scale

    # Front/back are intentionally asymmetric in profile. A small abdominal
    # front volume and stronger ribcage/chest projection keep the torso from
    # reading as a uniform prism, while a restrained lumbar/glute-side contour
    # gives the back view a neutral human break without encoding character sex.
    if y >= 0.0:
        front_scale = 1.0 + 0.018 * pelvis + 0.028 * waist + 0.055 * ribcage + 0.035 * upper_chest
        y *= front_scale
    else:
        back_scale = 1.0 + 0.045 * pelvis + 0.018 * waist + 0.025 * ribcage + 0.012 * upper_chest
        y *= back_scale

    # Diagonal points blend the directional changes rather than inheriting a
    # full side and full front/back adjustment simultaneously.
    blend = max(lateral, depthward)
    if blend < 0.35:
        return vertex
    return (x, y, z)


def refine_human_torso_cross_sections(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Add curved support points and neutral anatomy to the Human torso.

    Horizontal torso-ring chords receive shared midpoint support, then all
    interior torso vertices receive restrained directional anatomy. The actual
    hip and shoulder opening rings remain unchanged, preserving branch seams
    and provider architecture while improving ribcage, waist and pelvis read.
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
        vertex = (
            x * _OCTAGON_CHORD_CORRECTION,
            y * _OCTAGON_CHORD_CORRECTION,
            z,
        )
        edge_vertices[(first_index, second_index)] = len(vertices)
        vertices.append(vertex)

    # Shape both the original interior ring points and their new support points.
    # Limb vertices lie outside the hip/shoulder z span and are therefore not
    # touched by this pass.
    vertices = [
        _shape_anatomical_torso(vertex, proportions, hip_z, shoulder_z)
        for vertex in vertices
    ]

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
