# SPDX-License-Identifier: GPL-3.0-or-later
"""Anatomy-oriented macro contour for the generated Human base mesh.

This pass runs immediately after the connected deformation mesh is created and
before local refinement. It establishes continuous torso and leg contour from
landmarks so later refinement polishes anatomy instead of inventing it.
"""

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


def _shape_torso(vertex, proportions, hip_z, shoulder_z):
    x, y, z = vertex
    if z < hip_z - _EPSILON or z > shoulder_z + _EPSILON:
        return vertex

    height = max(shoulder_z - hip_z, _EPSILON)
    level = _clamp01((z - hip_z) / height)
    half_width = max(proportions.shoulder_width_cm * 0.5, proportions.hip_width_cm * 0.5)

    # Avoid pulling arm-root geometry into the trunk. The center body is shaped
    # strongly; vertices approaching the lateral shoulder/hip opening fade out.
    central = 1.0 - _smoothstep(max(0.0, abs(x) / max(half_width, _EPSILON) - 0.72) / 0.28)
    if central <= 0.0:
        return vertex

    # Establish pelvis -> waist -> ribcage -> shoulder flow by narrowing the
    # intermediate sections. Existing hip/shoulder extrema remain untouched.
    waist = _bell(level, 0.36, 0.24)
    lower_rib = _bell(level, 0.62, 0.22)
    upper_chest = _bell(level, 0.82, 0.18)
    x_scale = 1.0 - central * (0.070 * waist + 0.020 * lower_rib + 0.012 * upper_chest)
    x *= x_scale

    # The side silhouette needs distinct front/back contour. Keep changes
    # inward-only so the generator's published dimensions remain global bounds.
    if y > _EPSILON:
        abdomen_tuck = _bell(level, 0.36, 0.25)
        under_chest = _bell(level, 0.62, 0.20)
        y *= 1.0 - central * (0.050 * abdomen_tuck + 0.025 * under_chest)
    elif y < -_EPSILON:
        lumbar_tuck = _bell(level, 0.34, 0.26)
        upper_back = _bell(level, 0.76, 0.22)
        y *= 1.0 - central * (0.035 * lumbar_tuck + 0.015 * upper_back)

    return (x, y, z)


def _shape_leg(vertex, proportions, landmarks, hip_z):
    x, y, z = vertex
    if z >= hip_z - _EPSILON:
        return vertex

    side = "left" if x >= 0.0 else "right"
    hip = landmarks["hip." + side]
    knee = landmarks["knee." + side]
    ankle = landmarks["ankle." + side]
    center_x = hip[0]

    # Exclude the foot region and unrelated center geometry. The branch remains
    # centered on its landmark chain while only its cross-section changes.
    if z <= ankle[2] + proportions.foot_height_cm * 0.85:
        return vertex
    reach = max(proportions.thigh_thickness_cm, proportions.calf_thickness_cm) * 1.25
    if abs(x - center_x) > reach:
        return vertex

    if z >= knee[2]:
        span = max(hip_z - knee[2], _EPSILON)
        level = _clamp01((z - knee[2]) / span)
        knee_taper = 1.0 - 0.16 * (1.0 - level)
        inner_thigh = 1.0 - 0.045 * _bell(level, 0.48, 0.34)
        scale = knee_taper * inner_thigh
    else:
        span = max(knee[2] - ankle[2], _EPSILON)
        level = _clamp01((z - ankle[2]) / span)
        ankle_taper = 0.76 + 0.24 * _smoothstep(level / 0.35)
        knee_taper = 1.0 - 0.12 * _smoothstep((level - 0.72) / 0.28)
        calf = 1.0 - 0.025 * _bell(level, 0.48, 0.28)
        scale = ankle_taper * knee_taper * calf

    local_x = (x - center_x) * scale
    # Front/back depth follows the same large-form taper slightly more strongly,
    # helping the side silhouette read thigh/knee/calf/ankle rather than column.
    y *= 0.97 * scale + 0.03
    return (center_x + local_x, y, z)


def refine_human_anatomical_base_contour(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Establish torso and leg macro anatomy before local Human refinement."""
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("anatomical base contour expects one generated ObjectMesh part")
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")

    part = mesh.parts[0]
    landmarks = generate_landmarks(proportions)
    hip_z = landmarks["hip_center"][2]
    shoulder_z = landmarks["shoulder_center"][2]

    vertices = []
    for vertex in part.vertices:
        shaped = _shape_torso(vertex, proportions, hip_z, shoulder_z)
        shaped = _shape_leg(shaped, proportions, landmarks, hip_z)
        vertices.append(shaped)

    return ObjectMesh((MeshPart(part.name, tuple(vertices), part.faces, part.uvs),))
