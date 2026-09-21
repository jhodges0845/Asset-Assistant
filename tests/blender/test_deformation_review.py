# SPDX-License-Identifier: GPL-3.0-or-later
"""Camera-space regressions independent of expensive surface generation."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
try:
    import bpy
except ModuleNotFoundError:
    bpy = None


@unittest.skipIf(bpy is None, "requires Blender")
class DeformationReviewTests(unittest.TestCase):
    def test_review_cards_fit_and_depth_stacking_is_rejected(self):
        from scripts import inspect_human_deformation as review
        def human(name):
            root = bpy.data.objects.new(name, None)
            bpy.context.collection.objects.link(root)
            bpy.ops.mesh.primitive_cube_add(size=1)
            obj = bpy.context.object
            obj.parent = root
            obj.location.z = .9
            obj.scale = (.7, .25, 1.8)
            return root, obj, None
        try:
            with TemporaryDirectory() as directory:
                output = Path(directory) / "human_v2_deformation_review.png"
                output.write_bytes(b"existing artist review")
                with patch.object(review, "_human", side_effect=human), \
                     patch.object(review, "_apply_and_verify_pose"), \
                     patch.object(review, "_find_repo_root", return_value=Path(directory)):
                    review.main(render=False)
                self.assertEqual(output.read_bytes(), b"existing artist review")
            meshes = sorted((o for o in bpy.context.scene.objects if o.type == "MESH"), key=lambda o: o.parent.name)
            labels = sorted((o for o in bpy.context.scene.objects if o.type == "FONT"), key=lambda o: o.data.body)
            review._verify_projection(meshes, labels)
            # Reproduce the original bug: rows separated only in camera depth.
            for i, (mesh, label) in enumerate(zip(meshes, labels)):
                mesh.parent.location = (0, i * 2.7, 0)
                label.location = (0, i * 2.7 - .1, 2.15)
            bpy.context.view_layer.update()
            with self.assertRaisesRegex(RuntimeError, "overlaps"):
                review._verify_projection(meshes, labels)
        finally:
            review._clear_scene()

    def test_wrist_keeps_body_stationary_and_knee_flexes_backward(self):
        from scripts import inspect_human_deformation as review
        from object_core.providers.human import _neutral_surface_data
        try:
            review._clear_scene()
            root, obj, rig = review._human("WeightIsolation")
            bpy.context.view_layer.update()
            before = review._evaluated_local_points(obj)
            review._apply_and_verify_pose("Wrist", obj, rig, "hand.left", "Z", 1.05)
            after = review._evaluated_local_points(obj)
            _, arms = _neutral_surface_data()
            arm_indices = {i for _, indices in arms for i in indices}
            body_displacement = max((a - b).length for i, (a, b) in enumerate(zip(after, before)) if i not in arm_indices)
            self.assertLess(body_displacement, 1e-6)
            bone = rig.pose.bones["lower_leg.left"]
            before_tail = bone.tail.copy()
            _, name, axis, angle = next(p for p in review.POSES if p[0] == "Knee")
            review._apply_and_verify_pose("Knee", obj, rig, name, axis, angle)
            self.assertLess(bone.tail.y, before_tail.y - .1)
        finally:
            review._clear_scene()
