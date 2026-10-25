# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
import pytest
from blender_adapter.lod import preview_static_lods, _signature, _triangles


@pytest.fixture
def source():
    before_objects = set(bpy.data.objects)
    before_meshes = set(bpy.data.meshes)
    before_collections = set(bpy.data.collections)
    before_materials = set(bpy.data.materials)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
    obj = bpy.context.object
    obj.data.materials.append(bpy.data.materials.new("Artist LOD material"))
    try:
        yield obj
    finally:
        for item in set(bpy.data.objects)-before_objects:
            bpy.data.objects.remove(item, do_unlink=True)
        for item in set(bpy.data.meshes)-before_meshes:
            bpy.data.meshes.remove(item, do_unlink=True)
        for item in set(bpy.data.collections)-before_collections:
            bpy.data.collections.remove(item)
        for item in set(bpy.data.materials)-before_materials:
            bpy.data.materials.remove(item)


def test_preview_cancel_preserves_source_and_removes_copies(source):
    signature = _signature(source)
    objects = set(bpy.data.objects)
    meshes = set(bpy.data.meshes)
    preview = preview_static_lods(source, bpy.context.scene)
    assert _signature(source) == signature
    assert all(obj.parent is None for obj in preview.objects)
    for obj, level in zip(preview.objects, preview.levels):
        assert _triangles(obj.data) <= level.triangle_budget
        assert tuple(obj.data.materials) == tuple(source.data.materials)
        assert len(obj.data.uv_layers) == len(source.data.uv_layers)
    preview.cancel()
    assert set(bpy.data.objects) == objects
    assert set(bpy.data.meshes) == meshes
    assert _signature(source) == signature


def test_apply_keeps_source_and_blocks_second_apply(source):
    signature = _signature(source)
    preview = preview_static_lods(source, bpy.context.scene)
    result = preview.apply()
    assert len(result) == 2
    assert preview.collection['asset_assistant_lod_state'] == 'APPLIED'
    assert _signature(source) == signature
    with pytest.raises(ValueError):
        preview.apply()


def test_source_edit_blocks_apply(source):
    preview = preview_static_lods(source, bpy.context.scene)
    source.data.vertices[0].co.x += .1
    with pytest.raises(ValueError, match='Source changed'):
        preview.apply()
    preview.cancel()


def test_unsupported_state_is_rejected_without_copies(source):
    before = set(bpy.data.objects)
    source.vertex_groups.new(name='Artist skin')
    with pytest.raises(ValueError, match='static meshes'):
        preview_static_lods(source, bpy.context.scene)
    assert set(bpy.data.objects) == before


def test_preview_edit_is_preserved_and_blocks_apply(source):
    preview = preview_static_lods(source, bpy.context.scene)
    preview.objects[0].data.vertices[0].co.x += .2
    edited = _signature(preview.objects[0])
    with pytest.raises(ValueError, match='Preview changed'):
        preview.apply()
    assert _signature(preview.objects[0]) == edited
    preview.cancel()


def test_failed_reduction_cleans_only_staging_data(source, monkeypatch):
    from blender_adapter import validation
    original = validation.inspect_objects
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes', 'collections')}
    signature = _signature(source)

    def reject_copy(objects, **kwargs):
        if objects[0] != source:
            raise ValueError('Injected reduced-mesh failure')
        return original(objects, **kwargs)

    monkeypatch.setattr(validation, 'inspect_objects', reject_copy)
    with pytest.raises(ValueError, match='Injected'):
        preview_static_lods(source, bpy.context.scene)
    for kind, expected in before.items():
        assert set(getattr(bpy.data, kind)) == expected
    assert _signature(source) == signature


def test_mesh_animation_is_rejected_without_copies(source):
    source.data.animation_data_create()
    before = set(bpy.data.objects)
    with pytest.raises(ValueError, match='static meshes'):
        preview_static_lods(source, bpy.context.scene)
    assert set(bpy.data.objects) == before


def test_edit_mode_blocks_preview_and_apply(source):
    preview = preview_static_lods(source, bpy.context.scene)
    bpy.context.view_layer.objects.active = source
    source.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    before = set(bpy.data.objects)
    try:
        with pytest.raises(ValueError, match='Object Mode'):
            preview_static_lods(source, bpy.context.scene)
        with pytest.raises(ValueError, match='Object Mode'):
            preview.apply()
        assert set(bpy.data.objects) == before
        assert preview.state == 'PREVIEW'
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        preview.cancel()


def test_recovery_uses_references_and_rejects_stale_handles(source):
    from blender_adapter.lod import recover_static_lod_preview
    preview = preview_static_lods(source, bpy.context.scene)
    source.name = 'Renamed artist source'
    preview.objects[0].name = 'Renamed level'
    recovered = recover_static_lod_preview(preview.collection)
    assert recovered.source == source
    assert recovered.objects == preview.objects
    recovered.apply()
    with pytest.raises(ValueError, match='active preview'):
        preview.cancel()


def test_recovery_preserves_foreign_collection_contents(source):
    from blender_adapter.lod import recover_static_lod_preview
    preview = preview_static_lods(source, bpy.context.scene)
    preview.collection.objects.link(source)
    with pytest.raises(ValueError, match='collection changed'):
        recover_static_lod_preview(preview.collection)
    with pytest.raises(ValueError, match='collection changed'):
        preview.cancel()
    assert source.name in bpy.data.objects
    preview.collection.objects.unlink(source)
    preview.cancel()


def test_replaced_preview_mesh_is_preserved(source):
    preview = preview_static_lods(source, bpy.context.scene)
    original = preview.objects[0].data
    replacement = original.copy()
    preview.objects[0].data = replacement
    with pytest.raises(ValueError, match='ownership changed'):
        preview.cancel()
    assert preview.objects[0].data == replacement
    preview.objects[0].data = original
    preview.cancel()
