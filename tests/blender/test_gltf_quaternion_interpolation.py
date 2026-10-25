# SPDX-License-Identifier: GPL-3.0-or-later
"""A staged quaternion curve retains component-interpolated source motion."""
import bpy
from mathutils import Quaternion
from blender_adapter.animation import action_curves
from blender_adapter.gltf_animation import densify_linear_quaternions


def test_dense_export_copy_matches_component_motion():
    obj = bpy.data.objects.new('Quaternion parity', None)
    source = copied = None
    try:
        obj.rotation_mode = 'QUATERNION'
        for frame, angle in ((0, 0.), (24, 1.2)):
            obj.rotation_quaternion = Quaternion((1., 0., 0.), angle)
            obj.keyframe_insert('rotation_quaternion', frame=frame)
        source = obj.animation_data.action
        curves = action_curves(source, source.slots[0])
        for curve in curves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        original = tuple(tuple(tuple(key.co) for key in curve.keyframe_points) for curve in curves)
        # The sparse glTF spherical path must actually differ from Blender's
        # normalized component interpolation in this regression fixture.
        from mathutils import Vector
        reference_curves = sorted(curves, key=lambda c: c.array_index)
        start = Quaternion(tuple(c.evaluate(0) for c in reference_curves)).normalized()
        end = Quaternion(tuple(c.evaluate(24) for c in reference_curves)).normalized()
        midpoint = Quaternion(tuple(c.evaluate(6) for c in reference_curves)).normalized()
        assert ((start.slerp(end, .25) @ Vector((0, 1, 0))) -
                (midpoint @ Vector((0, 1, 0)))).length > .0001
        copied = source.copy()
        exported = sorted(action_curves(copied, copied.slots[0]), key=lambda c: c.array_index)
        densify_linear_quaternions(exported)
        times = [key.co.x for key in exported[0].keyframe_points]
        assert len(times) > 2
        assert times[0] == 0 and times[-1] == 24
        # Rotation difference via vector displacement avoids acos precision loss.
        from mathutils import Vector
        axis = Vector((0., 1., 0.))
        for frame in (24 * i / 127 for i in range(128)):
            index = next((i for i in range(len(times)-1) if times[i] <= frame <= times[i+1]), len(times)-2)
            left, right = times[index:index+2]
            q0 = Quaternion(tuple(curve.evaluate(left) for curve in exported)).normalized()
            q1 = Quaternion(tuple(curve.evaluate(right) for curve in exported)).normalized()
            actual = q0.slerp(q1, (frame-left)/(right-left))
            expected = Quaternion(tuple(curve.evaluate(frame) for curve in sorted(curves,key=lambda c:c.array_index))).normalized()
            assert ((actual @ axis) - (expected @ axis)).length < .000003
        assert original == tuple(tuple(tuple(key.co) for key in curve.keyframe_points) for curve in curves)
    finally:
        bpy.data.objects.remove(obj, do_unlink=True)
        for action in (source, copied):
            if action is not None:
                bpy.data.actions.remove(action)
