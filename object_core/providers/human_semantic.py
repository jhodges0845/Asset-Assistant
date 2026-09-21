# SPDX-License-Identifier: GPL-3.0-or-later
"""Provider-owned semantic mesh edits for Human assets."""

from math import isfinite

from ..models import MeshPart, ObjectMesh
from ..proportions.landmarks import generate_landmarks


def _number(arguments, key, default):
    value = arguments.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(key + " must be a number")
    value = float(value)
    if not isfinite(value):
        raise ValueError(key + " must be finite")
    return value


def _scale_value(arguments, axis):
    factor = _number(arguments, "factor", 1.0)
    value = _number(arguments, axis, arguments.get("scale_" + axis, factor))
    if not 0.1 <= value <= 4.0:
        raise ValueError(axis + " scale must be between 0.1 and 4.0")
    return value


def _bounds(proportions, skeleton=None):
    points = generate_landmarks(proportions)
    if skeleton is not None:
        bones = {bone.name: bone for bone in skeleton.bones}
        points = dict(points, chin=bones["head"].head, crown=bones["head"].tail,
                      hip_center=bones["torso"].head,
                      shoulder_center=bones["upper_arm.left"].head)
        points["shoulder.right"] = bones["upper_arm.right"].head
        points["hip.right"] = bones["upper_leg.right"].head
    chin_z = points["chin"][2]
    crown_z = points["crown"][2]
    head_span = max(crown_z - chin_z, 1e-9)
    return {
        "hip_z": points["hip_center"][2],
        "shoulder_z": points["shoulder_center"][2],
        "chin_z": chin_z,
        "crown_z": crown_z,
        "jaw_top_z": chin_z + head_span * 0.34,
        "cheek_low_z": chin_z + head_span * 0.28,
        "cheek_high_z": chin_z + head_span * 0.66,
        "shoulder_x": abs(points["shoulder.right"][0]),
        "hip_x": abs(points["hip.right"][0]),
    }


def _selected(target, vertex, proportions, bounds):
    x, y, z = vertex
    hip_z = bounds["hip_z"]
    shoulder_z = bounds["shoulder_z"]
    chin_z = bounds["chin_z"]

    if target == "body":
        return True
    if target == "torso":
        return hip_z <= z <= shoulder_z + proportions.neck_length_cm * 0.15
    if target == "shoulders":
        band = proportions.upper_arm_thickness_cm * 0.9
        return shoulder_z - band <= z <= shoulder_z + band and abs(x) >= proportions.neck_width_cm * 0.55
    if target == "head":
        return z >= chin_z
    if target == "face":
        return z >= chin_z and y >= -proportions.head_depth_cm * 0.05
    if target == "jaw":
        return chin_z <= z <= bounds["jaw_top_z"] and y >= -proportions.head_depth_cm * 0.12
    if target == "cheeks":
        return bounds["cheek_low_z"] <= z <= bounds["cheek_high_z"] and y >= -proportions.head_depth_cm * 0.08
    if target == "arm.left":
        return x < -proportions.neck_width_cm * 0.6 and z >= hip_z * 0.72
    if target == "arm.right":
        return x > proportions.neck_width_cm * 0.6 and z >= hip_z * 0.72
    if target == "leg.left":
        return x < 0 and z < hip_z + proportions.thigh_thickness_cm * 0.45
    if target == "leg.right":
        return x > 0 and z < hip_z + proportions.thigh_thickness_cm * 0.45
    return False


def _transform(vertices, indices, arguments):
    if not indices:
        raise ValueError("Semantic target did not resolve to generated vertices")
    center = tuple(sum(vertices[index][axis] for index in indices) / len(indices) for axis in range(3))
    scales = tuple(_scale_value(arguments, axis) for axis in ("x", "y", "z"))
    offsets = tuple(_number(arguments, "offset_" + axis, 0.0) for axis in ("x", "y", "z"))
    result = list(vertices)
    for index in indices:
        vertex = vertices[index]
        result[index] = tuple(
            center[axis] + (vertex[axis] - center[axis]) * scales[axis] + offsets[axis]
            for axis in range(3)
        )
    return result


def _profile(vertices, indices, target, arguments, proportions, bounds):
    profile = arguments.get("profile")
    if not profile:
        return vertices
    amount = _number(arguments, "amount", 0.65)
    if not 0.0 <= amount <= 1.5:
        raise ValueError("profile amount must be between 0.0 and 1.5")

    if target == "torso" and profile == "athletic":
        return _transform(vertices, indices, {
            "x": 1.0 + amount * 0.10,
            "y": 1.0 + amount * 0.06,
            "z": 1.0,
        })
    if target == "shoulders" and profile == "broad":
        return _transform(vertices, indices, {"x": 1.0 + amount * 0.18, "y": 1.0, "z": 1.0})
    if target == "head" and profile == "oval":
        return _transform(vertices, indices, {"x": 0.96, "y": 0.96, "z": 1.0 + amount * 0.08})
    if target == "face" and profile == "narrow":
        return _transform(vertices, indices, {"x": 1.0 - amount * 0.12, "y": 1.0, "z": 1.0})
    if target == "face" and profile == "defined":
        result = list(vertices)
        chin_z = bounds["chin_z"]
        head_span = max(proportions.head_height_cm, 1e-9)
        for index in indices:
            x, y, z = result[index]
            normalized = max(0.0, min(1.0, (z - chin_z) / head_span))
            jaw_weight = max(0.0, 1.0 - normalized * 2.0)
            result[index] = (x * (1.0 - amount * 0.10 * jaw_weight), y, z)
        return result
    if target == "jaw" and profile == "tapered":
        return _transform(vertices, indices, {
            "x": 1.0 - amount * 0.18,
            "y": 1.0 - amount * 0.05,
            "z": 1.0,
        })
    if target == "jaw" and profile == "strong":
        return _transform(vertices, indices, {
            "x": 1.0 + amount * 0.12,
            "y": 1.0 + amount * 0.04,
            "z": 1.0,
        })
    if target == "cheeks" and profile == "high":
        return _transform(vertices, indices, {
            "x": 1.0 + amount * 0.08,
            "y": 1.0 + amount * 0.05,
            "z": 1.0 + amount * 0.02,
        })
    if target == "cheeks" and profile == "soft":
        return _transform(vertices, indices, {
            "x": 1.0 + amount * 0.05,
            "y": 1.0 + amount * 0.10,
            "z": 1.0,
        })
    if target in ("arm.left", "arm.right") and profile == "lean":
        return _transform(vertices, indices, {"x": 0.94, "y": 0.94, "z": 1.0})
    if target in ("leg.left", "leg.right") and profile == "athletic":
        return _transform(vertices, indices, {"x": 1.0 + amount * 0.07, "y": 1.0 + amount * 0.07, "z": 1.0})

    raise ValueError("Unsupported Human semantic profile " + str(profile) + " for " + target)


def apply_human_semantic_operations(mesh, proportions, operations, *, skeleton=None):
    """Apply topology-preserving Human semantic geometry operations."""
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("Human semantic apply expects one generated ObjectMesh part")
    part = mesh.parts[0]
    vertices = list(part.vertices)
    bounds = _bounds(proportions, skeleton)

    for operation in operations:
        if operation.operation not in ("shape", "scale"):
            raise ValueError("Human semantic geometry cannot apply " + operation.operation)
        indices = [
            index for index, vertex in enumerate(vertices)
            if _selected(operation.target, vertex, proportions, bounds)
        ]
        arguments = operation.argument_values()
        vertices = _transform(vertices, indices, arguments)
        if operation.operation == "shape":
            vertices = _profile(vertices, indices, operation.target, arguments, proportions, bounds)

    return ObjectMesh((MeshPart(part.name, tuple(vertices), part.faces, part.uvs),))
