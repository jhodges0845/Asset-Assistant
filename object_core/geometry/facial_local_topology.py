# SPDX-License-Identifier: GPL-3.0-or-later
"""Localized Human facial feature topology for eyes, mouth, and nose."""

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


_EPSILON = 1e-7


def _average(points):
    count = float(len(points))
    return tuple(sum(point[i] for point in points) / count for i in range(len(points[0])))


def _bell(value, center, radius):
    distance = abs(value - center)
    if distance >= radius:
        return 0.0
    t = distance / radius
    smooth = t * t * (3.0 - 2.0 * t)
    return 1.0 - smooth


def _feature_weights(vertex, proportions, chin_z, crown_z):
    x, y, z = vertex
    if y <= _EPSILON:
        return (0.0, 0.0, 0.0)
    height = max(crown_z - chin_z, _EPSILON)
    half_width = max(proportions.head_width_cm * 0.5, _EPSILON)
    level = max(0.0, min(1.0, (z - chin_z) / height))
    lateral = max(0.0, min(1.0, abs(x) / half_width))

    eye = _bell(level, 0.61, 0.095) * _bell(lateral, 0.48, 0.30)
    mouth = _bell(level, 0.29, 0.075) * _bell(lateral, 0.0, 0.46)
    nose = _bell(level, 0.44, 0.13) * _bell(lateral, 0.0, 0.32)
    return (eye, mouth, nose)


def _shape_feature_center(vertex, proportions, chin_z, crown_z, weights):
    x, y, z = vertex
    eye, mouth, nose = weights
    height = max(crown_z - chin_z, _EPSILON)
    half_width = max(proportions.head_width_cm * 0.5, _EPSILON)
    level = max(0.0, min(1.0, (z - chin_z) / height))
    lateral = max(0.0, min(1.0, abs(x) / half_width))
    depth = proportions.head_depth_cm

    # Eye centers recess while their surrounding face boundary remains forward,
    # producing an eyelid/orbital plane that can later support identity edits.
    y -= depth * 0.030 * eye
    if eye:
        x *= 1.0 + 0.012 * eye

    # Mouth centers establish a shallow oral groove between the lip-support
    # levels without cutting the neutral mesh open.
    y -= depth * 0.020 * mouth * _bell(level, 0.29, 0.040)

    # The central lower nose gets extra projection while lateral support stays
    # restrained, giving the tip/alar region localized geometry instead of one
    # broad head section.
    nose_tip = nose * _bell(level, 0.43, 0.075) * _bell(lateral, 0.0, 0.20)
    y += depth * 0.055 * nose_tip
    return (x, y, z)


def refine_human_local_feature_topology(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Subdivide only facial cells that carry eye, mouth, or nose anatomy.

    Selected triangles gain a shared interior support vertex and are split into
    three triangles. Existing edges are never split, so this adds localized
    control without T-junctions or changes to the head/neck boundary. UVs are
    interpolated at the new center and remain one coordinate per face corner.
    """
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("local facial topology expects one generated ObjectMesh part")
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
        face_uvs = part.uvs[face_index] if part.uvs else ()
        if len(face) != 3:
            faces.append(face)
            if part.uvs:
                uvs.append(face_uvs)
            continue

        points = [part.vertices[index] for index in face]
        center = _average(points)
        weights = _feature_weights(center, proportions, chin_z, crown_z)
        if max(weights) <= 0.12:
            faces.append(face)
            if part.uvs:
                uvs.append(face_uvs)
            continue

        center_index = len(vertices)
        vertices.append(_shape_feature_center(center, proportions, chin_z, crown_z, weights))
        a, b, c = face
        faces.extend(((a, b, center_index), (b, c, center_index), (c, a, center_index)))
        if part.uvs:
            ua, ub, uc = face_uvs
            uv_center = _average((ua, ub, uc))
            uvs.extend(((ua, ub, uv_center), (ub, uc, uv_center), (uc, ua, uv_center)))

    return ObjectMesh((MeshPart(part.name, tuple(vertices), tuple(faces), tuple(uvs) if part.uvs else ()),))
