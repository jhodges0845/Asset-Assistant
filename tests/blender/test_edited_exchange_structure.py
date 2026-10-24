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
        super()._prove_exchange(target, extension)
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
        finally:
            source_rig.data.pose_position = source_mode
            bpy.context.view_layer.update()

    @staticmethod
    def _points(objects):
        return [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]

    @staticmethod
    def _extent(points):
        return tuple(max(point[axis] for point in points) - min(point[axis] for point in points)
                     for axis in range(3))
