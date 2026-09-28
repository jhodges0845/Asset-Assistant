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

    def test_canine_lights_stay_in_front_of_all_review_surfaces(self):
        from object_core.objects import get_provider
        provider = get_provider('quadruped')
        defaults = {p.key: p.default for p in provider.parameters}
        for overrides in ({}, dict(body_length_cm=95, shoulder_height_cm=40,
                                   body_width_cm=28, head_length_cm=30, tail_length_cm=50)):
            with self.subTest(overrides=overrides):
                self.review._clear_scene()
                values = dict(defaults, **overrides)
                args = SimpleNamespace(resolution_x=1200, resolution_y=500, samples=1)
                self.review._configure_scene(args, provider.mesh(values).parts[0])
                scene = bpy.context.scene
                nearest_y = min((obj.matrix_world @ vertex.co).y
                                for obj in scene.objects if obj.type == 'MESH'
                                for vertex in obj.data.vertices)
                for name in ('Key', 'Fill'):
                    self.assertLess(scene.objects[name].location.y, nearest_y,
                                    'Review lights must not cut through long body views')

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
