from object_core.geometry.anatomical_pelvis import pelvis_landmarks, pelvis_surface_ring


def test_pelvis_landmarks_are_bilateral_and_anatomically_ordered():
    lm=pelvis_landmarks(90.0,34.0,22.0,18.0)
    assert lm["iliac.left"][0] == -lm["iliac.right"][0]
    assert lm["trochanter.left"][0] == -lm["trochanter.right"][0]
    assert lm["glute.left"][0] == -lm["glute.right"][0]
    assert lm["iliac.left"][2] > lm["trochanter.left"][2] > lm["crotch.center"][2]
    assert lm["glute.left"][1] < 0.0
    assert lm["pubic.front"][1] > 0.0


def test_landmark_driven_surface_keeps_exact_left_right_symmetry():
    ring=pelvis_surface_ring(88.0,34.0,22.0,18.0,.72)
    for i in range(1,8):
        mirror=16-i
        assert abs(ring[i][0] + ring[mirror][0]) < 1e-9
        assert abs(ring[i][1] - ring[mirror][1]) < 1e-9
        assert abs(ring[i][2] - ring[mirror][2]) < 1e-9


def test_landmark_driven_surface_has_iliac_to_crotch_relief():
    ring=pelvis_surface_ring(88.0,34.0,22.0,18.0,.72)
    zs=[p[2] for p in ring]
    assert max(zs)-min(zs) > 3.0
