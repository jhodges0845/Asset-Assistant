# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from types import SimpleNamespace

try:
    import bpy
except ModuleNotFoundError:
    bpy = None


@unittest.skipIf(bpy is None, "requires Blender")
class HumanReviewCameraTests(unittest.TestCase):
    def setUp(self):
        from scripts import render_human_review
        self.review = render_human_review

    def tearDown(self):
        self.review._clear_scene()

    def configure(self, width=1800, height=900):
        self.review._clear_scene()
        args = SimpleNamespace(height_cm=180.0, weight_kg=95.0, body_type="average",
                               resolution_x=width, resolution_y=height)
        self.review._configure_scene(args, self.review._human_part(args))
        return bpy.context.scene

    def test_complete_models_and_labels_fit_wide_and_portrait_frames(self):
        for width, height in ((1800, 900), (900, 1800)):
            with self.subTest(width=width, height=height):
                scene = self.configure(width, height)
                self.assertEqual(len([obj for obj in scene.objects if obj.type == "MESH"]), 4)
                self.assertEqual(len([obj for obj in scene.objects if obj.type == "FONT"]), 4)

    def test_rejects_old_half_width_camera_frame(self):
        scene = self.configure()
        scene.camera.data.ortho_scale *= 0.5
        with self.assertRaisesRegex(RuntimeError, "outside the camera"):
            self.review._validate_camera_frame(
                scene.camera, [obj for obj in scene.objects if obj.type == "MESH"], scene)

    def test_rejects_far_plane_clipping(self):
        scene = self.configure()
        scene.camera.data.clip_end = 1.0
        with self.assertRaisesRegex(RuntimeError, "outside the camera"):
            self.review._validate_camera_frame(
                scene.camera, [obj for obj in scene.objects if obj.type == "MESH"], scene)
