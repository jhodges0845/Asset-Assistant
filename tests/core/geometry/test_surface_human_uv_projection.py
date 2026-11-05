# SPDX-License-Identifier: GPL-3.0-or-later
from itertools import combinations
import unittest
from object_core.geometry.deformable import _generate_face_atlas_uvs
from object_core.geometry.surface_human_builder import HumanSurfaceBuilder
from object_core.geometry.surface_human import SurfaceHumanSpec
from object_core.providers.human import _neutral_surface_anatomy_data


def minimum_area(uvs):
    return min(abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
               for a,b,c in combinations(uvs,3))


class SurfaceHumanUVProjectionTests(unittest.TestCase):
    def test_nonplanar_quad_uses_noncollapsed_projection_at_any_scale(self):
        for scale in (1e-4, 1, 1e4):
            points = tuple(tuple(v*scale for v in p) for p in
                           ((0,1,0),(0,0,1),(.3,0,2),(.2,0,-2)))
            old = _generate_face_atlas_uvs(points, ((0,1,2,3),))[0]
            new = _generate_face_atlas_uvs(points, ((0,1,2,3),), avoid_collapsed_triangles=True)[0]
            self.assertEqual(minimum_area(old), 0)
            self.assertGreater(minimum_area(new), .01)
            self.assertTrue(all(.08 <= v <= .92 for p in new for v in p))

    def test_usable_and_unrepairable_projections_stay_exact(self):
        for points in (((0,0,0),(1,0,0),(1,1,0),(0,1,0)),
                       ((0,0,0),(1,1,1),(2,2,2),(3,3,3)),
                       ((0,0,0),(1,0,0),(2,0,0),(3,0,0))):
            face = ((0,1,2,3),)
            self.assertEqual(_generate_face_atlas_uvs(points,face),
                _generate_face_atlas_uvs(points,face,avoid_collapsed_triangles=True))
        self.assertEqual(_generate_face_atlas_uvs((),(),avoid_collapsed_triangles=True), ())

    def test_current_human_changes_only_two_uv_islands(self):
        original, _ = HumanSurfaceBuilder().build(SurfaceHumanSpec())
        part = original.parts[0]
        old = _generate_face_atlas_uvs(part.vertices,part.faces)
        actual = _neutral_surface_anatomy_data()[0].parts[0]
        self.assertEqual(actual.vertices, part.vertices)
        self.assertEqual(actual.faces, part.faces)
        changed = [i for i,(a,b) in enumerate(zip(old,actual.uvs)) if a != b]
        self.assertEqual(changed, [35564,42481])
        for index in changed:
            self.assertLess(minimum_area(old[index]), 1e-15)
            self.assertGreater(minimum_area(actual.uvs[index]), 1e-7)
