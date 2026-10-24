# SPDX-License-Identifier: GPL-3.0-or-later
"""Edited Human shape and skin binding survive the advertised exchange layouts."""
import bpy
from tests.blender import test_glb_import_roundtrip as exchange
from blender_adapter.modification import inspect_generated_asset, apply_semantic_modification
from object_core.modification import SemanticOperation, ModificationRequest, plan_modification
from blender_adapter.asset_structure import asset_meshes


class EditedHumanExchangeTests(exchange.GLBImportRoundTripTests):
    def prepare_asset(self):
        body = next(obj for obj in self.root.children if obj.type == "MESH")
        original = tuple(tuple(vertex.co) for vertex in body.data.vertices)
        operation = SemanticOperation("shape", "shoulders", (("profile", "broad"), ("amount", .6)))
        plan = plan_modification(inspect_generated_asset(self.root),
                                ModificationRequest(semantic_operations=(operation,)))
        self.assertTrue(plan.safe_to_apply)
        apply_semantic_modification(self.root, plan)
        self.assertNotEqual(original, tuple(tuple(vertex.co) for vertex in body.data.vertices))

    def _prove_exchange(self, target, extension):
        before = set(bpy.data.objects)
        before_actions = set(bpy.data.actions)
        imported_clips = super()._prove_exchange(target, extension)
        from blender_adapter.targets import base_asset_rig
        labels = {base_asset_rig(root): label for root, label in imported_clips}
        imported_actions = set(bpy.data.actions) - before_actions
        imported_rigs = [obj for obj in set(bpy.data.objects) - before if obj.type == "ARMATURE"]
        source_rig = next(obj for obj in self.root.children if obj.type == "ARMATURE")
        source_mode = source_rig.data.pose_position
        try:
            source_rig.data.pose_position = "REST"
            for rig in imported_rigs:
                rig.data.pose_position = "REST"
            bpy.context.view_layer.update()
            source_points = self._points(asset_meshes(self.root))
            source_extent = self._extent(source_points)
            for rig in imported_rigs:
                bodies = [obj for obj in set(bpy.data.objects) - before if obj.type == "MESH"
                          and any(mod.type == "ARMATURE" and mod.object == rig for mod in obj.modifiers)]
                self.assertTrue(bodies)
                actual_extent = self._extent(self._points(bodies))
                for expected, actual in zip(source_extent, actual_extent):
                    self.assertAlmostEqual(expected, actual, delta=.0001)
                bone_names = set(rig.data.bones.keys())
                for body in bodies:
                    groups = {group.index for group in body.vertex_groups if group.name in bone_names}
                    self.assertTrue(groups)
                    for vertex in body.data.vertices:
                        weight = sum(group.weight for group in vertex.groups if group.group in groups)
                        self.assertAlmostEqual(weight, 1., delta=.001)
                if extension == ".fbx" and (target != "UNREAL" or labels[rig]):
                    self._verify_fbx_motion(rig, bodies, source_rig, source_points, imported_actions, labels[rig])
                    source_rig.data.pose_position = "REST"
                    rig.data.pose_position = "REST"
                    bpy.context.view_layer.update()
        finally:
            source_rig.data.pose_position = source_mode
            bpy.context.view_layer.update()

    def _verify_fbx_motion(self, rig, bodies, source_rig, source_points, imported_actions, clip_label):
        from mathutils.kdtree import KDTree
        from blender_adapter.animation import activate_generated_action
        import math
        data = rig.animation_data
        self.assertIsNotNone(data)
        actions = [(action, slot) for action in imported_actions for slot in action.slots
                   if slot.identifier == "OB" + rig.name]
        self.assertEqual(len(actions), 1 if clip_label else 2)
        tree = KDTree(len(source_points))
        for index, point in enumerate(source_points):
            tree.insert(point, index)
        tree.balance()
        mapping = [tree.find(point)[1] for point in self._points(bodies)]
        for track in data.nla_tracks:
            track.mute = True
        rig.data.pose_position = "POSE"
        for action, slot in actions:
            label = clip_label or next((name for name in ("Idle", "Walk") if name in action.name), None)
            self.assertIsNotNone(label, action.name)
            source = activate_generated_action(self.root, label)
            data.action = action
            data.action_slot = slot
            duration = source.frame_range[1] - source.frame_range[0]
            self.assertAlmostEqual(action.frame_range[1] - action.frame_range[0], duration, delta=1.)
            offsets = sorted({int(duration * fraction) for fraction in (0., .25, .5, .75, .95)})
            maximum = 0.
            for offset in offsets:
                frame = action.frame_range[0] + offset
                self.scene.frame_set(math.floor(frame), subframe=frame % 1)
                bpy.context.view_layer.update()
                depsgraph = bpy.context.evaluated_depsgraph_get()
                imported = [obj.evaluated_get(depsgraph) for obj in bodies]
                points = self._points(imported)
                frame = source.frame_range[0] + offset
                self.scene.frame_set(math.floor(frame), subframe=frame % 1)
                bpy.context.view_layer.update()
                original = self._points([obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
                                         for obj in asset_meshes(self.root)])
                maximum = max(maximum, max((point-original[index]).length * 100
                                          for point, index in zip(points, mapping)))
            self.assertLess(maximum, .002, (action.name, maximum))

    @staticmethod
    def _points(objects):
        return [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]

    @staticmethod
    def _extent(points):
        return tuple(max(point[axis] for point in points) - min(point[axis] for point in points)
                     for axis in range(3))
