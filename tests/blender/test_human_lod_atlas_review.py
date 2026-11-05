# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
bpy = pytest.importorskip('bpy')
from scripts.review_human_lod_atlas import atlas_report, source_atlas_columns


@pytest.fixture
def mesh():
    data = bpy.data.meshes.new('Atlas diagnostic')
    data.from_pydata([(0,0,0), (1,0,0), (0,1,0)], [], [(0,1,2)])
    uv = data.uv_layers.new()
    for loop, value in zip(uv.data, ((.1,.1), (.4,.1), (.1,.4))):
        loop.uv = value
    yield data
    bpy.data.meshes.remove(data)


def test_single_cell_is_read_only(mesh):
    before = [tuple(loop.uv) for loop in mesh.uv_layers.active.data]
    assert atlas_report(mesh, 2) == dict(triangles=1, cross_cell_triangles=0,
        outside_atlas_triangles=0, zero_uv_area_triangles=0, smooth_polygons=0)
    assert [tuple(loop.uv) for loop in mesh.uv_layers.active.data] == before


def test_crossing_and_outside_are_distinct(mesh):
    mesh.uv_layers.active.data[1].uv = (.6,.1)
    result = atlas_report(mesh, 2)
    assert result['cross_cell_triangles'] == 1
    assert result['outside_atlas_triangles'] == 0
    mesh.uv_layers.active.data[1].uv = (1.1,.1)
    assert atlas_report(mesh, 2)['outside_atlas_triangles'] == 1


def test_collapsed_uv_triangle(mesh):
    for loop in mesh.uv_layers.active.data:
        loop.uv = (.1,.1)
    assert atlas_report(mesh, 2)['zero_uv_area_triangles'] == 1


@pytest.mark.parametrize('columns', [0, -1, 1.5, True])
def test_rejects_invalid_grid(mesh, columns):
    with pytest.raises(ValueError):
        atlas_report(mesh, columns)


def test_rejects_missing_or_nonfinite_uv(mesh):
    mesh.uv_layers.active.data[0].uv = (float('nan'),.1)
    with pytest.raises(ValueError, match='finite'):
        atlas_report(mesh, 2)
    mesh.uv_layers.remove(mesh.uv_layers.active)
    with pytest.raises(ValueError, match='active UV'):
        atlas_report(mesh, 2)


def test_source_grid_rejects_repacked_faces():
    data = bpy.data.meshes.new('Two atlas cells')
    data.from_pydata([(0,0,0),(1,0,0),(0,1,0),(1,1,0)], [], [(0,1,2),(1,3,2)])
    uv = data.uv_layers.new()
    try:
        for loop, value in zip(uv.data, ((.1,.1),(.4,.1),(.1,.4),(.6,.1),(.9,.1),(.6,.4))):
            loop.uv = value
        assert source_atlas_columns(data) == 2
        # A valid UV island in the wrong cell is not the expected generated atlas.
        for loop in list(uv.data)[3:]:
            loop.uv.x -= .5
        with pytest.raises(ValueError, match='atlas assumption'):
            source_atlas_columns(data)
    finally:
        bpy.data.meshes.remove(data)
