import unittest
from collections import defaultdict
from dataclasses import replace

from object_core.geometry.neutral_pelvis import NeutralPelvisShape, generate_neutral_pelvis, semantic_controls


class NeutralPelvisTests(unittest.TestCase):
    def test_exposes_three_named_attachment_boundaries(self):
        vertices, faces, boundaries = generate_neutral_pelvis()
        self.assertGreater(len(vertices), 0)
        self.assertGreater(len(faces), 0)
        self.assertEqual(set(boundaries), {"torso", "left_thigh", "right_thigh"})
        # Patch recipes own their native edge density.  Attachment adapters may
        # resample later; the generator must expose the actual mesh boundaries.
        self.assertGreaterEqual(len(boundaries["torso"]), 16)
        self.assertEqual(len(boundaries["left_thigh"]), len(boundaries["right_thigh"]))
        self.assertGreaterEqual(len(boundaries["left_thigh"]), 12)

    def test_surface_has_only_declared_boundaries_and_consistent_winding(self):
        shapes = [NeutralPelvisShape()]
        for control, values in {
            "width": (20, 40), "depth": (12, 32), "height": (12, 30),
            "crotch_width": (3, 12), "thigh_spacing": (1.5, 10),
            "glute_projection": (.55, 1.65), "crotch_drop": (.55, 1.55),
        }.items():
            shapes.extend(replace(shapes[0], **{control: value}) for value in values)
        for shape in shapes:
            with self.subTest(shape=shape):
                vertices, faces, boundaries = generate_neutral_pelvis(shape)
                edges = defaultdict(list)
                for face in faces:
                    self.assertEqual(len(face), len(set(face)))
                    for a, b in zip(face, face[1:] + face[:1]):
                        edges[tuple(sorted((a, b)))].append((a, b))
                expected = {tuple(sorted((a, b)))
                            for loop in boundaries.values()
                            for a, b in zip(loop, loop[1:] + loop[:1])}
                actual = {edge for edge, uses in edges.items() if len(uses) == 1}
                self.assertEqual(actual, expected)
                for edge, uses in edges.items():
                    self.assertLessEqual(len(uses), 2, edge)
                    if len(uses) == 2:
                        self.assertEqual(uses[0], tuple(reversed(uses[1])), edge)
                # Connected genus-zero surface with three attachment holes.
                self.assertEqual(len(vertices) - len(edges) + len(faces), -1)
                adjacency = defaultdict(set)
                for a, b in edges:
                    adjacency[a].add(b)
                    adjacency[b].add(a)
                visited, pending = set(), [0]
                while pending:
                    vertex = pending.pop()
                    if vertex not in visited:
                        visited.add(vertex)
                        pending.extend(adjacency[vertex] - visited)
                self.assertEqual(len(visited), len(vertices))

    def test_shell_normals_point_outward(self):
        vertices, faces, boundaries = generate_neutral_pelvis()
        torso = set(boundaries["torso"])
        for face in faces:
            if len(torso.intersection(face)) != 2:
                continue
            a, b, c = (vertices[i] for i in face[:3])
            u = tuple(y-x for x, y in zip(a, b))
            v = tuple(y-x for x, y in zip(a, c))
            normal = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2])
            center = tuple(sum(vertices[i][axis] for i in face)/len(face) for axis in (0, 1))
            self.assertGreater(sum(x*y for x, y in zip(normal, center)), 0)

    def test_default_surface_has_no_collapsed_or_folded_faces(self):
        vertices, faces, _ = generate_neutral_pelvis()
        for face in faces:
            normals = []
            for i in range(len(face)):
                a, b, c = (vertices[face[j % len(face)]] for j in (i, i+1, i+2))
                u = tuple(y-x for x, y in zip(a, b))
                v = tuple(y-x for x, y in zip(b, c))
                normals.append((u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]))
            average = tuple(sum(n[axis] for n in normals) for axis in range(3))
            for normal in normals:
                self.assertGreater(sum(x*y for x, y in zip(normal, average)), 1e-8, face)

    def test_lower_side_turn_has_multiple_longitudinal_rows(self):
        vertices, _, _ = generate_neutral_pelvis()
        shape = NeutralPelvisShape()
        # The shared-edge recipe must contain a real descending side surface,
        # rather than one horizontal shelf followed immediately by an outlet.
        lateral = [
            vertex for vertex in vertices
            if vertex[0] > shape.width * .34 and abs(vertex[1]) < shape.depth * .28
        ]
        levels = sorted({round(vertex[2], 3) for vertex in lateral}, reverse=True)
        self.assertGreaterEqual(len(levels), 8)
        self.assertGreater(levels[0] - levels[-1], shape.height * .45)

    def test_semantic_controls_cover_modify_facing_shape_dimensions(self):
        controls = set(semantic_controls())
        self.assertTrue({"width", "depth", "hip_fullness", "glute_projection", "crotch_width", "crotch_drop", "thigh_spacing"} <= controls)

    def test_semantic_changes_move_expected_regions(self):
        base_vertices, _, _ = generate_neutral_pelvis()
        wide_vertices, _, _ = generate_neutral_pelvis(NeutralPelvisShape(width=40.0, hip_fullness=1.25))
        base_outer = max(abs(vertex[0]) for vertex in base_vertices)
        wide_outer = max(abs(vertex[0]) for vertex in wide_vertices)
        self.assertGreater(wide_outer, base_outer)

    def test_default_is_bilaterally_symmetric(self):
        vertices, _, _ = generate_neutral_pelvis()
        rounded = {(round(x, 6), round(y, 6), round(z, 6)) for x, y, z in vertices}
        for x, y, z in rounded:
            self.assertIn((round(-x, 6), y, z), rounded)


if __name__ == "__main__":
    unittest.main()
