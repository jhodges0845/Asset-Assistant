from object_core.providers.semantic_geometry import _transform


def test_transform_scales_named_region_around_its_center():
    vertices = ((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (5.0, 0.0, 0.0))

    result = _transform(vertices, (0, 1), {"x": 2.0})

    assert result[0] == (-2.0, 0.0, 0.0)
    assert result[1] == (2.0, 0.0, 0.0)
    assert result[2] == vertices[2]


def test_transform_combines_axis_scale_and_offset():
    vertices = ((0.0, 0.0, 0.0), (2.0, 2.0, 2.0))

    result = _transform(vertices, (0, 1), {
        "x": 0.5,
        "y": 2.0,
        "z": 1.0,
        "offset_x": 3.0,
        "offset_z": -1.0,
    })

    assert result == [(3.5, -1.0, -1.0), (4.5, 3.0, 1.0)]


def test_transform_rejects_empty_semantic_region():
    try:
        _transform(((0.0, 0.0, 0.0),), (), {"factor": 1.1})
    except ValueError as error:
        assert str(error) == "Semantic target did not resolve to generated vertices"
    else:
        raise AssertionError("empty semantic regions must be rejected")
