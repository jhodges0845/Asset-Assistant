# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
import numpy as np
import pytest
from mathutils import Matrix, Vector
from tests.blender.playback_metrics import world_points, maximum_distance


@pytest.mark.parametrize('matrix', (
    Matrix.Identity(4), Matrix.Translation((1.7, -.3, 2.1)),
    Matrix.Translation((-.7, 1.2, -.1)) @ Matrix.Rotation(.73, 4, 'Z') @
    Matrix.Diagonal((.7, -1.4, 2.3, 1)),
))
def test_bulk_world_points_match_blender_affine_coordinates(matrix):
    mesh = bpy.data.meshes.new('Bulk metric test')
    obj = bpy.data.objects.new('Bulk metric test', mesh)
    try:
        rng = np.random.default_rng(814)
        mesh.from_pydata(rng.uniform(-2, 2, (257, 3)).tolist(), [], [])
        obj.matrix_world = matrix
        expected = np.asarray([obj.matrix_world @ vertex.co for vertex in mesh.vertices], dtype=np.float32)
        actual = world_points(obj)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=5e-7)
        assert actual.shape == (257, 3)
        assert actual.dtype == np.float32
    finally:
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(mesh)


@pytest.mark.parametrize('amount', (0, .000009, .000011, .000019, .000021, .0011))
def test_bulk_distance_retains_decisions_and_detects_single_vertex_motion(amount):
    rng = np.random.default_rng(915)
    left = rng.uniform(-1, 1, (257, 3)).astype(np.float32)
    right = left.copy()
    right[173, 2] += amount
    expected = max((Vector(a) - Vector(b)).length for a, b in zip(left, right))
    actual = maximum_distance(left, right)
    assert actual == pytest.approx(expected, rel=2e-7, abs=1e-12)
    for threshold in (.00001, .00002, .001):
        assert (actual < threshold) == (expected < threshold)
    # A fixed, wrong correspondence cannot be concealed by rematching.
    assert maximum_distance(left, right[::-1]) > 1


@pytest.mark.parametrize('bad', (np.zeros((0, 3)), np.zeros((2, 2)),
                               np.array([[float('nan'), 0, 0]])))
def test_bulk_distance_rejects_invalid_comparisons(bad):
    with pytest.raises(ValueError):
        maximum_distance(bad, bad)


def test_bulk_distance_matches_three_axis_reference():
    rng = np.random.default_rng(916)
    left = rng.uniform(-2, 2, (1024, 3)).astype(np.float32)
    right = left + rng.uniform(-.003, .003, left.shape).astype(np.float32)
    expected = max((Vector(a) - Vector(b)).length for a, b in zip(left, right))
    assert maximum_distance(left, right) == pytest.approx(expected, rel=2e-7)
