import unittest
from math import sqrt

from object_core.geometry.landmark_curves import bezier_curve_points, fit_landmark_arc


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


class LandmarkCurveTests(unittest.TestCase):
    def test_bezier_keeps_landmarks_exact_and_respects_handle_directions(self):
        start = (0.0, 0.0, 0.0)
        end = (10.0, 0.0, 0.0)
        start_handle = (3.0, 2.0, 0.0)
        end_handle = (3.0, -2.0, 0.0)
        points = bezier_curve_points(start, end, 8, start_handle, end_handle)

        self.assertEqual(points[0], start)
        self.assertEqual(points[-1], end)
        self.assertEqual(len(points), 9)

        first_step = _sub(points[1], start)
        last_step = _sub(end, points[-2])
        self.assertGreater(_dot(first_step, start_handle), 0.0)
        self.assertGreater(_dot(last_step, end_handle), 0.0)

    def test_handles_are_clamped_to_prevent_large_overshoot(self):
        points = bezier_curve_points(
            (0.0, 0.0, 0.0),
            (10.0, 0.0, 0.0),
            12,
            (100.0, 100.0, 0.0),
            (100.0, -100.0, 0.0),
            max_handle_ratio=0.4,
        )
        self.assertLess(max(abs(point[1]) for point in points), 4.0)

    def test_landmark_arc_replaces_piecewise_span_with_smooth_single_curve(self):
        authored = (
            (0.0, 0.0, 0.0),
            (2.0, 1.8, 0.0),
            (4.0, 2.1, 0.0),
            (6.0, 1.5, 0.0),
            (8.0, 0.0, 0.0),
        )
        curved = fit_landmark_arc(authored)
        self.assertEqual(curved[0], authored[0])
        self.assertEqual(curved[-1], authored[-1])
        self.assertEqual(len(curved), len(authored))
        self.assertNotEqual(curved[2], authored[2])

        steps = [_sub(b, a) for a, b in zip(curved, curved[1:])]
        for first, second in zip(steps, steps[1:]):
            self.assertGreater(_dot(first, second), 0.0)


if __name__ == "__main__":
    unittest.main()
