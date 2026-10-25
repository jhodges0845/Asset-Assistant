# SPDX-License-Identifier: GPL-3.0-or-later
"""Preserve Blender linear quaternion motion in temporary glTF export Actions."""
from math import acos, ceil
from mathutils import Quaternion


def densify_linear_quaternions(curves):
    """Bound spherical interpolation differences without editing source Actions.

    Call only on temporary export copies. Blender interpolates quaternion
    components; glTF interpolates rotations. Subdivide large linear rotations
    into at most .005-radian arcs, evaluating the original component curves.
    Other interpolation and modifier types are left untouched.
    """
    groups = {}
    for curve in curves:
        if curve.data_path.endswith('rotation_quaternion'):
            groups.setdefault(curve.data_path, {})[curve.array_index] = curve
    for group in groups.values():
        if set(group) != {0, 1, 2, 3}:
            continue
        ordered = [group[index] for index in range(4)]
        if any(key.interpolation != 'LINEAR' for curve in ordered for key in curve.keyframe_points):
            continue
        if any(modifier.type != 'CYCLES' for curve in ordered for modifier in curve.modifiers):
            continue
        times = sorted({float(key.co.x) for curve in ordered for key in curve.keyframe_points})
        samples = []
        for start, end in zip(times, times[1:]):
            left = Quaternion(tuple(curve.evaluate(start) for curve in ordered)).normalized()
            right = Quaternion(tuple(curve.evaluate(end) for curve in ordered)).normalized()
            # Use the signed dot: opposite quaternion signs traverse a different
            # component path and must not be treated as an identical rotation.
            angle = 2 * acos(max(-1., min(1., left.dot(right))))
            steps = max(1, ceil(angle / .005))
            for step in range(1, steps):
                frame = start + (end-start) * step / steps
                samples.append((frame, tuple(curve.evaluate(frame) for curve in ordered)))
        for frame, values in samples:
            for index, curve in enumerate(ordered):
                key = curve.keyframe_points.insert(frame, values[index], options={'FAST'})
                key.interpolation = 'LINEAR'
        for curve in ordered:
            curve.update()
