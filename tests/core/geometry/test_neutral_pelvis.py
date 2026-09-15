import unittest

from object_core.geometry.neutral_pelvis import NeutralPelvisShape, generate_neutral_pelvis, semantic_controls


class NeutralPelvisTests(unittest.TestCase):
    def test_exposes_three_named_attachment_boundaries(self):
        vertices, faces, boundaries = generate_neutral_pelvis()
        self.assertGreater(len(vertices), 0)
        self.assertGreater(len(faces), 0)
        self.assertEqual(set(boundaries), {"torso", "left_thigh", "right_thigh"})
        self.assertTrue(all(len(loop) == 16 for loop in boundaries.values()))

    def test_semantic_controls_cover_modify_facing_shape_dimensions(self):
        controls = set(semantic_controls())
        self.assertTrue({"width", "depth", "hip_fullness", "glute_projection", "crotch_width", "crotch_drop", "thigh_spacing"} <= controls)

    def test_semantic_changes_move_expected_regions(self):
        base_vertices, _, base = generate_neutral_pelvis()
        wide_vertices, _, wide = generate_neutral_pelvis(NeutralPelvisShape(width=40.0, hip_fullness=1.25))
        base_outer = max(abs(base_vertices[i][0]) for i in base["torso"])
        wide_outer = max(abs(wide_vertices[i][0]) for i in wide["left_thigh"] + wide["right_thigh"])
        self.assertGreater(wide_outer, base_outer)

    def test_default_is_bilaterally_symmetric(self):
        vertices, _, _ = generate_neutral_pelvis()
        rounded = {(round(x, 6), round(y, 6), round(z, 6)) for x, y, z in vertices}
        for x, y, z in rounded:
            self.assertIn((round(-x, 6), y, z), rounded)


if __name__ == "__main__":
    unittest.main()
