import unittest

from object_core.geometry.neutral_pelvis import generate_neutral_pelvis
from object_core.geometry.neutral_pelvis_landmark_baseline import (
    generate_neutral_pelvis as generate_landmark_baseline,
)


class CurvedLandmarkPelvisTests(unittest.TestCase):
    def test_curvature_changes_surface_without_changing_topology_or_attachments(self):
        baseline_vertices, baseline_faces, baseline_boundaries = generate_landmark_baseline()
        curved_vertices, curved_faces, curved_boundaries = generate_neutral_pelvis()

        self.assertEqual(curved_faces, baseline_faces)
        self.assertEqual(curved_boundaries, baseline_boundaries)
        self.assertEqual(len(curved_vertices), len(baseline_vertices))

        # Torso and thigh interface points are intentionally frozen so this test
        # changes only internal surface flow between the existing landmarks.
        for name, loop in baseline_boundaries.items():
            for index in loop:
                self.assertEqual(curved_vertices[index], baseline_vertices[index], (name, index))

        displacement = max(
            sum((a - b) ** 2 for a, b in zip(curved, baseline)) ** 0.5
            for curved, baseline in zip(curved_vertices, baseline_vertices)
        )
        self.assertGreater(displacement, 1e-3)

    def test_curved_experiment_remains_bilaterally_symmetric(self):
        vertices, _, _ = generate_neutral_pelvis()
        rounded = {(round(x, 6), round(y, 6), round(z, 6)) for x, y, z in vertices}
        for x, y, z in rounded:
            self.assertIn((round(-x, 6), y, z), rounded)


if __name__ == "__main__":
    unittest.main()
