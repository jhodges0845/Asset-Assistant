# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-specific neutral pelvis, glute, and upper-leg shaping."""

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


def _shape_for_side(vertex, side_sign, hip, proportions):
    """Round one hip into the upper thigh without changing connectivity.

    The field gives the pelvis a restrained lateral crest, adds posterior glute
    volume, softens the hard hip-to-thigh corner, and narrows the medial upper
    thigh just below the crotch. The same equations are mirrored across X so
    the neutral Human remains exactly left/right symmetric.
    """
    x, y, z = vertex
    # Generated rings can contain tiny floating-point X values at the intended
    # center line (for example cos(pi/2)). Treat those as exactly central so a
    # numerically positive/negative residue cannot select only one hip field
    # and introduce visible/as-tested left-right asymmetry.
    if abs(x) <= _EPSILON:
        return vertex

    lateral = side_sign * x
    hip_lateral = abs(hip[0])
    if lateral <= _EPSILON:
        return vertex

    radius = max(
        proportions.thigh_thickness_cm * 1.85,
        proportions.hip_width_cm * 0.24,
    )
    distance = _distance(vertex, hip)
    if distance >= radius:
        return vertex

    proximity = _smoothstep(1.0 - distance / radius)
    vertical_delta = z - hip[2]
    upper_band = max(proportions.torso_length_cm * 0.13, proportions.thigh_thickness_cm * 0.90)
    lower_band = max(proportions.upper_leg_length_cm * 0.16, proportions.thigh_thickness_cm * 1.20)
    if vertical_delta > upper_band or vertical_delta < -lower_band:
        return vertex

    outer_reference = max(proportions.hip_width_cm * 0.5, hip_lateral + proportions.thigh_thickness_cm * 0.30)
    outward = _smoothstep(
        (lateral - hip_lateral * 0.55)
        / max(outer_reference - hip_lateral * 0.55, _EPSILON)
    )
    below = _smoothstep(_clamp01((-vertical_delta) / max(lower_band, _EPSILON)))
    above = _smoothstep(_clamp01(vertical_delta / max(upper_band, _EPSILON)))

    # A small iliac/upper-hip breadth keeps the pelvis from collapsing directly
    # into two vertical thigh tubes. Fade this before the actual thigh shaft.
    crest = proportions.hip_width_cm * 0.018 * proximity * (0.55 + 0.45 * outward) * (1.0 - 0.70 * below)
    x += side_sign * crest

    # Posterior volume establishes a neutral glute break in side/3/4/back views.
    # Keep the front comparatively restrained so the result remains generic.
    if y < -_EPSILON:
        glute = proportions.hip_depth_cm * 0.055 * proximity * (0.70 + 0.30 * outward) * (1.0 - 0.45 * below)
        y -= glute
    elif y > _EPSILON:
        front = proportions.hip_depth_cm * 0.015 * proximity * (1.0 - 0.55 * below)
        y += front

    # Just below the joint, pull medial upper-thigh points slightly outward from
    # the center line. This replaces the abrupt rectangular crotch/leg split with
    # a gentler inverted-V transition without introducing sex-specific anatomy.
    medial = 1.0 - outward
    if vertical_delta < 0.0:
        thigh_blend = proportions.thigh_thickness_cm * 0.045 * proximity * below * (0.50 + 0.50 * medial)
        x += side_sign * thigh_blend

    # Above the hip, keep the upper pelvis from forming a shelf by easing the
    # outermost contour inward as it approaches the torso.
    if vertical_delta > 0.0:
        shelf_soften = proportions.hip_width_cm * 0.010 * proximity * above * outward
        x -= side_sign * shelf_soften

    return (x, y, z)


def refine_human_pelvis(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Shape connected pelvis/upper-leg geometry into a neutral human transition."""
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("pelvis refinement expects one generated ObjectMesh part")
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
                landmarks["hip." + side],
                proportions,
            )
        vertices[index] = shaped

    refined = MeshPart(part.name, tuple(vertices), part.faces, part.uvs)
    return ObjectMesh((refined,))
