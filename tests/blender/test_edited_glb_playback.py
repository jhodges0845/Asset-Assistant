# SPDX-License-Identifier: GPL-3.0-or-later
"""Semantically edited skin retains source motion through actual GLB exchange."""
from tests.blender import test_canine_glb_playback as playback
from blender_adapter.modification import inspect_generated_asset, apply_semantic_modification
from object_core.modification import SemanticOperation, ModificationRequest, plan_modification


class EditedCanineGLBPlaybackTests(playback.CanineGLBPlaybackTests):
    semantic_target = "chest"

    def prepare_asset(self, root):
        body = next(obj for obj in root.children if obj.type == "MESH")
        before = tuple(tuple(vertex.co) for vertex in body.data.vertices)
        weights = tuple(tuple((group.group, group.weight) for group in vertex.groups)
                        for vertex in body.data.vertices)
        operation = SemanticOperation("shape", self.semantic_target,
                                      (("profile", "broad"), ("amount", .6)))
        plan = plan_modification(inspect_generated_asset(root),
                                ModificationRequest(semantic_operations=(operation,)))
        self.assertTrue(plan.safe_to_apply)
        snapshot = apply_semantic_modification(root, plan)
        self.assertTrue(snapshot.owns_geometry)
        self.assertNotEqual(before, tuple(tuple(vertex.co) for vertex in body.data.vertices))
        self.assertEqual(weights, tuple(tuple((group.group, group.weight) for group in vertex.groups)
                                       for vertex in body.data.vertices))
        return root


class EditedHumanGLBPlaybackTests(EditedCanineGLBPlaybackTests):
    provider_key = "human"
    run_duration = .72
    semantic_target = "shoulders"
