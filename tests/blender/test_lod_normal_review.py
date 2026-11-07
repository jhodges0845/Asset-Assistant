# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
bpy = pytest.importorskip('bpy')
from scripts.review_lod_normals import normal_report


@pytest.mark.parametrize('normal,opposed,angle', [((0, 0, 1), 0, 0), ((0, 0, -1), 3, 180), ((1, 0, 1), 0, 45)])
def test_normal_report_measures_authored_normals_without_mutation(normal, opposed, angle):
    mesh = bpy.data.meshes.new('Normal diagnostic')
    try:
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        mesh.polygons[0].use_smooth = True
        mesh.normals_split_custom_set([normal] * 3)
        uv = mesh.uv_layers.new()
        uv.data[0].uv = (.2, .3)
        def state():
            return (tuple(tuple(v.co) for v in mesh.vertices),
                    tuple(tuple(x.uv) for x in uv.data),
                    tuple(tuple(n.vector) for n in mesh.corner_normals),
                    tuple(p.use_smooth for p in mesh.polygons))
        before = state()
        report = normal_report(mesh)
        assert report['opposed_corners'] == opposed
        assert report['measured_corners'] == 3
        assert report['median_degrees'] == pytest.approx(angle, abs=.01)
        assert state() == before
    finally:
        bpy.data.meshes.remove(mesh)


def test_degenerate_triangles_are_reported_not_counted_as_normal_agreement():
    mesh = bpy.data.meshes.new('Degenerate diagnostic')
    try:
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (2, 0, 0)], [], [(0, 1, 2)])
        report = normal_report(mesh)
        assert report['triangles'] == report['degenerate_triangles'] == 1
        assert report['measured_corners'] == 0
        assert report['median_degrees'] is None
        assert report['p95_degrees'] is None
    finally:
        bpy.data.meshes.remove(mesh)
