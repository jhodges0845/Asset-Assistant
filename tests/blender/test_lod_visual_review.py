# SPDX-License-Identifier: GPL-3.0-or-later
"""Diagnostic snapshots must retain imported geometry and UVs."""
from hashlib import sha256
import pytest
bpy = pytest.importorskip("bpy")
from scripts.render_lod_review import import_snapshot


@pytest.fixture
def skinned_glb(tmp_path):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.object.armature_add()
    rig = bpy.context.object
    mesh = bpy.data.meshes.new('Review triangle')
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    uv = mesh.uv_layers.new(name='UVMap')
    for loop, value in zip(uv.data, ((.1, .2), (.8, .2), (.1, .9))):
        loop.uv = value
    obj = bpy.data.objects.new('Review body', mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = (2, 3, 4)
    obj.parent = rig
    obj.vertex_groups.new(name=rig.data.bones[0].name).add([0, 1, 2], 1, 'REPLACE')
    obj.modifiers.new('Skin', 'ARMATURE').object = rig
    obj.select_set(True)
    path = tmp_path / 'review.glb'
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB',
                              use_selection=True, export_animations=False)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    yield path
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def test_snapshot_preserves_uv_world_space_and_input(skinned_glb):
    digest = sha256(skinned_glb.read_bytes()).hexdigest()
    before = set(bpy.data.objects)
    mesh, metadata = import_snapshot(skinned_glb, None, .25)
    assert metadata['triangles'] == 1
    assert metadata['vertices'] == 3
    assert set(bpy.data.objects) == before
    points = sorted(tuple(vertex.co) for vertex in mesh.vertices)
    for actual, expected in zip(points, [(2, 3, 4), (2, 4, 4), (3, 3, 4)]):
        assert actual == pytest.approx(expected, abs=1e-6)
    values = sorted(tuple(loop.uv) for loop in mesh.uv_layers.active.data)
    for actual, expected in zip(values, [(.1, .2), (.1, .9), (.8, .2)]):
        assert actual == pytest.approx(expected, abs=1e-6)
    assert sha256(skinned_glb.read_bytes()).hexdigest() == digest
    bpy.data.meshes.remove(mesh)


def test_snapshot_rejects_missing_clip(skinned_glb):
    with pytest.raises(ValueError, match='exactly one imported clip'):
        import_snapshot(skinned_glb, 'Run', .25)
