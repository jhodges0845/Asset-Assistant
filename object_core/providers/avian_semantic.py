# SPDX-License-Identifier: GPL-3.0-or-later
"""Provider-owned semantic mesh edits for Avian assets."""

from .semantic_geometry import _number, _scale_value, _transform

from ..models import MeshPart, ObjectMesh


def _selected(target, vertex, dimensions):
    x, y, z = vertex
    length = dimensions["body_length_cm"]
    width = dimensions["body_width_cm"]
    height = dimensions["body_height_cm"]
    body_z = height * 0.52

    if target == "body":
        return -length * 0.44 <= y <= length * 0.46 and z >= height * 0.20
    if target == "chest":
        return length * 0.02 <= y <= length * 0.46 and z >= body_z - height * 0.30
    if target == "head":
        return y >= length * 0.47 and z >= body_z
    if target == "beak":
        return y >= length * 0.66
    if target == "wing.left":
        return x < -width * 0.42 and z >= body_z - height * 0.22
    if target == "wing.right":
        return x > width * 0.42 and z >= body_z - height * 0.22
    if target == "tail":
        return y <= -length * 0.43
    if target == "leg.left":
        return x < 0 and z < body_z - height * 0.12 and y > -length * 0.35
    if target == "leg.right":
        return x > 0 and z < body_z - height * 0.12 and y > -length * 0.35
    if target == "foot.left":
        return x < 0 and z <= height * 0.14
    if target == "foot.right":
        return x > 0 and z <= height * 0.14
    return False


def _profile(vertices, indices, target, arguments, dimensions):
    profile = arguments.get("profile")
    if not profile:
        return vertices
    amount = _number(arguments, "amount", 0.65)
    if not 0.0 <= amount <= 1.5:
        raise ValueError("profile amount must be between 0.0 and 1.5")
    result = list(vertices)

    if target == "beak" and profile == "hooked":
        ys = [vertices[index][1] for index in indices]
        low, high = min(ys), max(ys)
        span = max(high - low, 1e-9)
        drop = dimensions["body_height_cm"] * 0.18 * amount
        for index in indices:
            x, y, z = result[index]
            forward = (y - low) / span
            result[index] = (x, y, z - drop * forward * forward)
        return result

    if target == "chest" and profile == "powerful":
        return _transform(result, indices, {"x": 1.0 + amount * 0.25, "y": 1.0 + amount * 0.12, "z": 1.0 + amount * 0.18})

    if target in ("wing.left", "wing.right") and profile == "broad":
        return _transform(result, indices, {"x": 1.0 + amount * 0.12, "y": 1.0 + amount * 0.30, "z": 1.0 + amount * 0.08})

    if target == "tail" and profile == "fan":
        ys = [vertices[index][1] for index in indices]
        front, rear = max(ys), min(ys)
        span = max(front - rear, 1e-9)
        for index in indices:
            x, y, z = result[index]
            rearward = (front - y) / span
            result[index] = (x * (1.0 + amount * 0.85 * rearward), y, z)
        return result

    raise ValueError("Unsupported Avian semantic profile " + str(profile) + " for " + target)


def apply_avian_semantic_operations(mesh, dimensions, operations):
    """Apply semantic operations without changing topology or the procedural base."""
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("Avian semantic apply expects one generated ObjectMesh part")
    part = mesh.parts[0]
    vertices = list(part.vertices)

    for operation in operations:
        if operation.operation not in ("shape", "scale"):
            raise ValueError("Avian semantic geometry cannot apply " + operation.operation)
        indices = [index for index, vertex in enumerate(vertices) if _selected(operation.target, vertex, dimensions)]
        arguments = operation.argument_values()
        vertices = _transform(vertices, indices, arguments)
        if operation.operation == "shape":
            vertices = _profile(vertices, indices, operation.target, arguments, dimensions)

    return ObjectMesh((MeshPart(part.name, tuple(vertices), part.faces, part.uvs),))
