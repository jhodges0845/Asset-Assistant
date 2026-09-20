# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from collections import Counter

from object_core.geometry.anatomical_pelvis import pelvis_ring
from object_core.geometry.anatomical_pelvis_patch import append_anatomical_pelvis_patch


class AnatomicalPelvisPatchTests(unittest.TestCase):
    def setUp(self):
        self.vertices = list(pelvis_ring(90.0, 34.0, 24.0, 18.0))
        self.faces = []
        self.boundary = tuple(range(16))
        self.left = ((15.0, 0.0, 88.5), (15.0, 0.0, 87.0), (15.0, 0.0, 85.5))
        self.right = tuple((-x, y, z) for x, y, z in self.left)
        self.left_root, self.right_root = append_anatomical_pelvis_patch(
            self.vertices, self.faces, self.boundary, self.left, self.right, 18.0, 17.0
        )

    def test_builds_three_longitudinal_rows_per_thigh(self):
        # 16 shared-boundary vertices + 3 x 16 vertices for each thigh.
        self.assertEqual(len(self.vertices), 16 + 3 * 16 * 2)
        self.assertEqual(len(self.left_root), 16)
        self.assertEqual(len(self.right_root), 16)

    def test_only_two_faces_are_triangular_split_poles(self):
        triangles = [face for face in self.faces if len(face) == 3]
        quads = [face for face in self.faces if len(face) == 4]
        self.assertEqual(len(triangles), 2)
        self.assertEqual(len(quads), 24 + 32 * 2)

    def test_patch_has_exactly_three_boundary_loops(self):
        counts = Counter()
        for face in self.faces:
            for i, a in enumerate(face):
                counts[tuple(sorted((a, face[(i + 1) % len(face)])))] += 1
        boundary_edges = {edge for edge, count in counts.items() if count == 1}
        expected = set()
        for ring in (self.boundary, self.left_root, self.right_root):
            for i, a in enumerate(ring):
                expected.add(tuple(sorted((a, ring[(i + 1) % 16]))))
        self.assertEqual(boundary_edges, expected)
        self.assertTrue(all(count in (1, 2) for count in counts.values()))

    def test_rows_remain_bilaterally_symmetric(self):
        rounded = {(round(x, 6), round(y, 6), round(z, 6)) for x, y, z in self.vertices}
        for x, y, z in tuple(rounded):
            self.assertIn((round(-x, 6), y, z), rounded)

    def test_outer_bands_never_cross_the_body_midline(self):
        # The old split was manifold but joined front/back halves to left/right
        # thighs, so some outer edges traversed the body diagonally.
        for face in self.faces:
            upper = [i for i in face if i < 16]
            lower = [i for i in face if 16 <= i < 48]
            if len(upper) == 2:
                for a in upper:
                    for b in lower:
                        self.assertGreaterEqual(
                            self.vertices[a][0] * self.vertices[b][0], -1e-8)

    def test_rejects_missing_longitudinal_rows(self):
        with self.assertRaises(ValueError):
            append_anatomical_pelvis_patch(
                [], [], tuple(range(16)), self.left[:2], self.right[:2], 18.0, 17.0
            )


if __name__ == "__main__":
    unittest.main()
