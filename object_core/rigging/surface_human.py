# SPDX-License-Identifier: GPL-3.0-or-later
"""Rest rig for surface-human-1, preserving the existing animation bone names.

Landmarks follow the authored arm/leg centerlines in surface_human.py. Both
mesh and skeleton use the same continuous body-control transform.
"""
from math import pi, sin
from ..models import BodyType, HumanoidSpec
from ..models.skeleton import Bone, Skeleton
from ..proportions import generate_proportions


def shape_surface_point(point, proportions, reference):
    """Apply existing weight/body-type girth ratios smoothly along height."""
    x, y, z = point
    t = z / proportions.standing_height_cm
    rows = (
        (0.0, "hip"),
        (0.55, "hip"),
        (0.66, "waist"),
        (0.77, "chest"),
        (0.82, "shoulder"),
        (0.90, "head"),
        (1.0, "head"),
    )

    def ratios(name):
        width = name + "_width_cm"
        depth = ("chest" if name == "shoulder" else name) + "_depth_cm"
        return (
            getattr(proportions, width) / getattr(reference, width),
            getattr(proportions, depth) / getattr(reference, depth),
        )

    for (a, first), (b, second) in zip(rows, rows[1:]):
        if t <= b:
            blend = max(0.0, min(1.0, (t - a) / (b - a)))
            blend = blend * blend * (3 - 2 * blend)
            u, v = ratios(first), ratios(second)
            return (
                x * (u[0] + (v[0] - u[0]) * blend),
                y * (u[1] + (v[1] - u[1]) * blend),
                z,
            )
    u = ratios("head")
    return x * u[0], y * u[1], z


def surface_skeleton(proportions):
    height = proportions.standing_height_cm
    reference = generate_proportions(HumanoidSpec(height, 95.0, BodyType.AVERAGE))
    # Same sampled foot minimum and crown used by surface-human-1's final
    # floor-to-crown normalization (the model is authored in meters).
    floor = min(
        0.09
        - 0.059 * min((k / 32) / 0.24, 1)
        - 0.003 * (k / 32)
        - (0.026 * (1 - k / 32) + 0.014 * (k / 32)) * sin(pi / 2 * min(1, k / 16))
        for k in range(1, 33)
    )

    def point(x, y, z):
        return shape_surface_point(
            (
                x * height / 1.75,
                y * height / 1.75,
                (z - floor) * height / (1.75 - floor),
            ),
            proportions,
            reference,
        )

    hip, shoulder = point(0, 0.008, 0.99), point(0, 0, 1.465)
    chin, crown = point(0, 0, 1.548), point(0, 0, 1.75)
    bones = [
        Bone("root", hip, point(0, 0.008, 1.04)),
        Bone("torso", hip, shoulder, "root"),
        Bone("neck", shoulder, chin, "torso"),
        Bone("head", chin, crown, "neck"),
    ]
    for side, sign in (("left", 1), ("right", -1)):
        arm = [
            point(sign * x, 0, z)
            for x, z in ((0.192, 1.385), (0.263, 1.19), (0.308, 0.923), (0.316, 0.78))
        ]
        leg = [
            point(sign * x, y, z)
            for x, y, z in (
                (0.089, 0.008, 0.965),
                (0.155, 0.008, 0.50),
                (0.187, 0.005, 0.09),
                (0.187, 0.174, 0.028),
            )
        ]
        for names, points, parent in (
            (("upper_arm", "forearm", "hand"), arm, "torso"),
            (("upper_leg", "lower_leg", "foot"), leg, "root"),
        ):
            for i, name in enumerate(names):
                full_name = name + "." + side
                bones.append(Bone(full_name, points[i], points[i + 1], parent))
                parent = full_name
    return Skeleton(tuple(bones))
