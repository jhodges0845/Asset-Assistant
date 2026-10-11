# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from types import SimpleNamespace

try:
    import bpy
except ModuleNotFoundError:
    bpy = None


@unittest.skipIf(bpy is None, 'requires Blender')
class CanineReviewCropTests(unittest.TestCase):
    def setUp(self):
        from scripts import render_canine_review
        self.review = render_canine_review
        self.provider = self.review.get_provider('quadruped')
        self.defaults = {p.key: p.default for p in self.provider.parameters}

    def tearDown(self):
        self.review.sheets._clear_scene()

    def test_paw_crops_are_local_and_frame_correctly_across_samples(self):
        for overrides in ({}, dict(body_length_cm=95, shoulder_height_cm=40, body_width_cm=28,
                                   head_length_cm=30, tail_length_cm=50),
                          dict(body_length_cm=25, shoulder_height_cm=15, body_width_cm=55,
                               head_length_cm=8, tail_length_cm=5)):
            mesh, anatomy = self.review._construction(self.provider.dimensions(dict(self.defaults, **overrides)))
            source = mesh.parts[0]
            for name in ('front-paw', 'hind-paw'):
                with self.subTest(overrides=overrides, region=name):
                    part, metadata = self.review.crop_review_part(source, source, anatomy, name)
                    indices = metadata['review_source_vertex_indices']
                    owned = set(next(r.vertex_indices for r in anatomy.regions
                                     if r.name == metadata['review_limb']))
                    self.assertTrue(set(indices) < owned)
                    self.assertEqual(part.vertices, tuple(source.vertices[i] for i in indices))
                    self.assertAlmostEqual(min(v[2] for v in part.vertices), 0)
                    restored_faces = tuple(tuple(indices[i] for i in face) for face in part.faces)
                    self.assertTrue(set(restored_faces) <= set(source.faces))
                    self.review.sheets._clear_scene()
                    self.review.sheets._configure_scene(
                        SimpleNamespace(resolution_x=1200, resolution_y=500, samples=1), part)
                    self.assertEqual(4, len([o for o in bpy.context.scene.objects if o.type == 'MESH']))

    def test_pose_retains_neutral_selection_and_evaluated_coordinates(self):
        mesh, anatomy = self.review._construction(self.provider.dimensions(self.defaults))
        source = mesh.parts[0]
        for name, pose in (('front-paw', 'elbow'), ('hind-paw', 'hock')):
            neutral, selection = self.review.crop_review_part(source, source, anatomy, name)
            posed, _ = self.review.review_part(self.defaults, pose)
            cropped, posed_selection = self.review.crop_review_part(posed, source, anatomy, name)
            self.assertEqual(selection, posed_selection)
            self.assertEqual(neutral.faces, cropped.faces)
            self.assertNotEqual(neutral.vertices, cropped.vertices)
            self.assertEqual(cropped.vertices, tuple(posed.vertices[i]
                             for i in selection['review_source_vertex_indices']))

    def test_body_and_head_paths_preserve_existing_selection(self):
        from dataclasses import replace
        mesh, anatomy = self.review._construction(self.provider.dimensions(self.defaults))
        source = mesh.parts[0]
        self.assertEqual((source, {}), self.review.crop_review_part(source, source, anatomy, 'body'))
        head, metadata = self.review.crop_review_part(source, source, anatomy, 'head')
        owned = set(next(r.vertex_indices for r in anatomy.regions if r.name == 'head'))
        expected = tuple(face for face in source.faces if set(face) <= owned)
        indices = metadata['review_source_vertex_indices']
        self.assertEqual(expected, tuple(tuple(indices[i] for i in face) for face in head.faces))
        with self.assertRaises(ValueError):
            self.review.crop_review_part(source, source, anatomy, 'unknown')
        with self.assertRaisesRegex(ValueError, 'matching neutral topology'):
            self.review.crop_review_part(replace(source, faces=source.faces[:-1], uvs=source.uvs[:-1]), source, anatomy, 'front-paw')
