# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-specific local facial anatomy shaping for generated meshes."""

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


_EPSILON = 1e-7


def _clamp01(value):
    return max(0.0, min(1.0, value))


def _smoothstep(value):
    value = _clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def _bell(value, center, radius):
    distance = abs(value - center)
    if distance >= radius:
        return 0.0
    return 1.0 - _smoothstep(distance / radius)


def _shape_front_vertex(vertex, proportions, chin_z, crown_z, bounds):
    x, y, z = vertex
    if y <= _EPSILON:
        return vertex

    height = max(crown_z - chin_z, _EPSILON)
    half_width = max(proportions.head_width_cm * 0.5, _EPSILON)
    depth = proportions.head_depth_cm
    level = _clamp01((z - chin_z) / height)
    lateral = _clamp01(abs(x) / half_width)

    center = _bell(lateral, 0.0, 0.30)
    inner_face = _bell(lateral, 0.22, 0.28)
    eye_band = _bell(lateral, 0.50, 0.24)
    cheek_band = _bell(lateral, 0.62, 0.25)

    # Nose bridge and tip. The bridge is narrower and subtler; the tip carries
    # more projection around the lower-nose level so the profile reads as a
    # connected feature rather than one pushed-forward head ring.
    bridge = _bell(level, 0.56, 0.16) * (0.55 * center + 0.45 * inner_face)
    tip = _bell(level, 0.43, 0.10) * center
    y += depth * (0.040 * bridge + 0.085 * tip)

    # Orbital recess and brow ridge. Include the inner orbital region as well as
    # the lateral eye band so center/inner-eye support points actually sit behind
    # the brow instead of leaving the profile plateau unchanged.
    eye = _bell(level, 0.61, 0.09) * (0.35 * inner_face + 0.65 * eye_band)
    brow = _bell(level, 0.70, 0.09) * (0.35 * inner_face + 0.65 * eye_band)
    y += depth * (-0.035 * eye + 0.030 * brow)

    # Upper/lower lip support with a restrained mouth groove. The lip pair is
    # deliberately close so later semantic edits can control fullness/identity.
    upper_lip = _bell(level, 0.31, 0.045) * (0.65 * center + 0.35 * inner_face)
    lower_lip = _bell(level, 0.265, 0.045) * (0.70 * center + 0.30 * inner_face)
    mouth_groove = _bell(level, 0.287, 0.022) * center
    y += depth * (0.026 * upper_lip + 0.034 * lower_lip - 0.010 * mouth_groove)

    # Chin projection and cheek volume help the lower face stop reading as a
    # tapered mask. Both are restrained so Maxine/other identities remain the
    # job of semantic operations rather than the neutral generator.
    chin = _bell(level, 0.14, 0.09) * center
    cheek = _bell(level, 0.46, 0.13) * cheek_band
    y += depth * (0.030 * chin + 0.018 * cheek)

    # Keep lower-face width controlled and add a small cheekbone break without
    # changing global head dimensions.
    x *= 1.0 - 0.020 * _bell(level, 0.18, 0.13) + 0.015 * cheek

    min_x, max_x, min_y, max_y = bounds
    x = max(min_x, min(max_x, x))
    y = max(min_y, min(max_y, y))
    return (x, y, z)


def refine_human_local_facial_anatomy(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Shape structured Human face topology into neutral local anatomy.

    This pass assumes the Human head already has structured feature loops/local
    support topology. It moves vertices only: connectivity and UVs stay exactly
    unchanged so downstream semantics and export contracts remain stable.
    """
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("facial anatomy refinement expects one generated ObjectMesh part")
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

    vertices = []
    for vertex in part.vertices:
        if chin_z - _EPSILON <= vertex[2] <= crown_z + _EPSILON:
            vertices.append(_shape_front_vertex(vertex, proportions, chin_z, crown_z, bounds))
        else:
            vertices.append(vertex)

    return ObjectMesh((MeshPart(part.name, tuple(vertices), part.faces, part.uvs),))
