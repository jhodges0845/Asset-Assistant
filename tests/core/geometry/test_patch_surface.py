import unittest
from math import sqrt

from object_core.geometry.patch_surface import (
    PatchNetwork,
    curve_points,
    fair_boundaries,
    vertex_neighbors,
)


class PatchSurfaceTests(unittest.TestCase):
    def test_tangent_fairing_moves_interior_rows_not_shared_boundary(self):
        net = PatchNetwork()
        net.boundary("top.left", curve_points((-2, 1, 0), (0, 1, 0), 2))
        shared = net.boundary("shared", curve_points((0, 1, 0), (0, -1, 0), 2))
        net.boundary("bottom.left", curve_points((-2, -1, 0), (0, -1, 0), 2))
        net.boundary("outer.left", curve_points((-2, 1, 0), (-2, -1, 0), 2))
        net.boundary("top.right", curve_points((0, 1, 0), (2, 1, 0), 2))
        net.boundary("outer.right", curve_points((2, 1, 0), (2, -1, 0), 2))
        net.boundary("bottom.right", curve_points((0, -1, 0), (2, -1, 0), 2))

        # Both patches bow toward +Z, so their first interior rows meet the
        # shared edge with a visible crease instead of opposite tangents.
        net.patch(
            "left", "top.left", "shared", "bottom.left", "outer.left",
            control=(0, 0, 1),
        )
        net.patch(
            "right", "top.right", "outer.right", "bottom.right", "shared",
            control=(0, 0, 1),
        )

        midpoint = shared[1]
        boundary_before = tuple(net.vertices[index] for index in shared)
        neighbors = vertex_neighbors(net.faces, len(net.vertices))
        cross = tuple(neighbors[midpoint] - set(shared))
        self.assertEqual(len(cross), 2)

        def tangent_cosine():
            center = net.vertices[midpoint]
            vectors = [
                tuple(net.vertices[index][axis] - center[axis] for axis in range(3))
                for index in cross
            ]
            lengths = [sqrt(sum(value * value for value in vector)) for vector in vectors]
            return sum(vectors[0][axis] * vectors[1][axis] for axis in range(3)) / (lengths[0] * lengths[1])

        before = tangent_cosine()
        fair_boundaries(
            net.vertices,
            net.faces,
            (shared,),
            strength=0.5,
            iterations=2,
        )
        after = tangent_cosine()

        self.assertEqual(boundary_before, tuple(net.vertices[index] for index in shared))
        self.assertLess(after, before)
        self.assertLess(after, -0.7)


if __name__ == "__main__":
    unittest.main()
