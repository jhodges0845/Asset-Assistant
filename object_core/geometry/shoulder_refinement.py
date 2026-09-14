# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-specific neutral shoulder and deltoid shaping."""

from math import sqrt

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


_EPSILON = 1e-7


def _clamp01(value):
    return max(0.0, min(1.0, value))


def _smoothstep(value):
    value = _clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def _distance(first, second):
    return sqrt(sum((first[index] - second[index]) ** 2 for index in range(3)))


def _shape_for_side(vertex, side_sign, shoulder, proportions):
    """Round one neutral shoulder without changing connectivity.

    The field spans the outer upper chest and the first arm rings. It lowers the
    hard outer shoulder corner, adds restrained deltoid front/back volume and
    tucks the lower medial armpit. The same equations are mirrored across X so
    the neutral Human remains exactly left/right symmetric.
    """
    x, y, z = vertex
    lateral = side_sign * x
    shoulder_lateral = abs(shoulder[0])
    if lateral <= 0.0:
        return vertex

    shoulder_radius = max(
        proportions.upper_arm_thickness_cm * 1.65,
        proportions.shoulder_width_cm * 0.18,
    )
    distance = _distance(vertex, shoulder)
    if distance >= shoulder_radius:
        return vertex

    inner_lateral = shoulder_lateral - max(
        proportions.upper_arm_thickness_cm * 1.10,
        proportions.shoulder_width_cm * 0.12,
    )
    if lateral < inner_lateral:
        return vertex

    proximity = _smoothstep(1.0 - distance / shoulder_radius)
    outward = _smoothstep(
        (lateral - inner_lateral) / max(shoulder_lateral - inner_lateral, _EPSILON)
    )

    shoulder_z = shoulder[2]
    vertical_delta = z - shoulder_z
    upper_band = max(proportions.upper_arm_thickness_cm * 0.90, proportions.torso_length_cm * 0.08)
    lower_band = max(proportions.upper_arm_thickness_cm * 1.10, proportions.torso_length_cm * 0.10)
    if vertical_delta > upper_band or vertical_delta < -lower_band:
        return vertex

    # A human shoulder slopes into the deltoid rather than terminating in a
    # horizontal torso corner. The drop is strongest at the outer seam and
    # fades into both chest and upper arm.
    upper_weight = _clamp01((vertical_delta + lower_band * 0.35) / max(upper_band + lower_band * 0.35, _EPSILON))
    corner_drop = proportions.torso_length_cm * 0.040 * outward * proximity * upper_weight
    z -= corner_drop

    # Deltoid volume is primarily front/back around the shoulder joint. Keep it
    # restrained and proportional so this remains a neutral base rather than a
    # muscular character profile.
    if abs(y) > _EPSILON:
        deltoid = proportions.upper_arm_thickness_cm * 0.075 * proximity * (0.55 + 0.45 * outward)
        y += (1.0 if y > 0.0 else -1.0) * deltoid

    # Just below and medial to the joint, create a small armpit indentation.
    # This is the visual break that prevents the arm from reading like a tube
    # plugged into a rectangular torso.
    if vertical_delta < 0.0 and lateral <= shoulder_lateral:
        lower = _smoothstep(_clamp01((-vertical_delta) / max(lower_band, _EPSILON)))
        medial = 1.0 - outward
        tuck = proportions.upper_arm_thickness_cm * 0.055 * proximity * lower * (0.45 + 0.55 * medial)
        x -= side_sign * tuck

    return (x, y, z)


def refine_human_shoulders(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Shape connected shoulder/upper-arm geometry into a neutral deltoid transition."""
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("shoulder refinement expects one generated ObjectMesh part")
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")

    part = mesh.parts[0]
    landmarks = generate_landmarks(proportions)
    vertices = list(part.vertices)

    for index, vertex in enumerate(part.vertices):
        shaped = vertex
        for side, sign in (("left", 1.0), ("right", -1.0)):
            shaped = _shape_for_side(
                shaped,
                sign,
                landmarks["shoulder." + side],
                proportions,
            )
        vertices[index] = shaped

    refined = MeshPart(part.name, tuple(vertices), part.faces, part.uvs)
    return ObjectMesh((refined,))
