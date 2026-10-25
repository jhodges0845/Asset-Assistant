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


@pytest.fixture
def lod_operators():
    from blender_adapter import lod_ui
    lod_ui.register()
    try:
        yield
    finally:
        lod_ui.unregister()


def test_lod_operators_preserve_selection_and_apply(source, lod_operators):
    from blender_adapter.lod_ui import _previews
    selected = tuple(bpy.context.selected_objects)
    assert bpy.ops.asset_assistant.lod_preview() == {'FINISHED'}
    preview, = _previews(bpy.context.scene)
    assert tuple(bpy.context.selected_objects) == selected
    assert bpy.context.active_object == source
    with pytest.raises(RuntimeError, match='existing preview'):
        bpy.ops.asset_assistant.lod_preview()
    assert bpy.ops.asset_assistant.lod_finish(collection_name=preview.name, action='APPLY') == {'FINISHED'}
    assert preview['asset_assistant_lod_state'] == 'APPLIED'
    assert source == bpy.context.active_object


def test_lod_operator_cancel_and_stale_apply(source, lod_operators):
    from blender_adapter.lod_ui import _previews
    bpy.ops.asset_assistant.lod_preview()
    preview, = _previews(bpy.context.scene)
    source.data.vertices[0].co.x += .1
    with pytest.raises(RuntimeError, match='Source changed'):
        bpy.ops.asset_assistant.lod_finish(collection_name=preview.name, action='APPLY')
    assert preview['asset_assistant_lod_state'] == 'PREVIEW'
    assert bpy.ops.asset_assistant.lod_finish(collection_name=preview.name, action='CANCEL') == {'FINISHED'}
    assert not _previews(bpy.context.scene)
    assert bpy.context.active_object == source


def test_discard_blocks_preview_in_edit_mode(source):
    preview = preview_static_lods(source, bpy.context.scene)
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    level = preview.objects[0]
    level.select_set(True)
    bpy.context.view_layer.objects.active = level
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        with pytest.raises(ValueError, match='Object Mode'):
            preview.cancel()
        assert preview.state == 'PREVIEW'
        assert level.name in bpy.data.objects
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = source
        source.select_set(True)
        preview.cancel()


def test_custom_lod_operator_budgets(source, lod_operators):
    from blender_adapter.lod_ui import _previews
    from blender_adapter.lod import recover_static_lod_preview
    original = _triangles(source.data)
    assert bpy.ops.asset_assistant.lod_preview(level_count=3, ratios=(.75, .5, .25, .125)) == {'FINISHED'}
    collection, = _previews(bpy.context.scene)
    preview = recover_static_lod_preview(collection)
    assert len(preview.objects) == 3
    assert [level.triangle_budget for level in preview.levels] == [int(original * r) for r in (.75, .5, .25)]
    for obj, level in zip(preview.objects, preview.levels):
        assert _triangles(obj.data) <= level.triangle_budget
    preview.cancel()


def test_invalid_operator_budgets_leave_scene_unchanged(source, lod_operators):
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes', 'collections')}
    with pytest.raises(RuntimeError, match='smaller triangle budget'):
        bpy.ops.asset_assistant.lod_preview(level_count=2, ratios=(.25, .5, .125, .0625))
    for kind, expected in before.items():
        assert set(getattr(bpy.data, kind)) == expected


def test_object_material_override_preserved_without_changing_shared_mesh(source):
    mesh_material = source.data.materials[0]
    override = bpy.data.materials.new('Visible object override')
    source.material_slots[0].link = 'OBJECT'
    source.material_slots[0].material = override
    sibling = bpy.data.objects.new('Shared artist mesh', source.data)
    bpy.context.scene.collection.objects.link(sibling)
    before = _signature(source)
    preview = preview_static_lods(source, bpy.context.scene)
    for obj in preview.objects:
        assert obj.material_slots[0].material == override
        assert obj.material_slots[0].link == 'DATA'
    preview.apply()
    assert _signature(source) == before
    assert source.material_slots[0].link == 'OBJECT'
    assert source.data.materials[0] == mesh_material
    assert sibling.material_slots[0].material == mesh_material


def test_changed_object_override_blocks_apply(source):
    preview = preview_static_lods(source, bpy.context.scene)
    source.material_slots[0].link = 'OBJECT'
    source.material_slots[0].material = bpy.data.materials.new('Edited override')
    with pytest.raises(ValueError, match='Source changed'):
        preview.apply()
    preview.cancel()


def test_multiple_uv_layers_and_material_assignments(source):
    from math import isfinite
    source.data.uv_layers.new(name='Lightmap')
    source.data.materials.append(bpy.data.materials.new('Upper material'))
    for face in source.data.polygons:
        face.material_index = int(face.center.z > 0)
    preview = preview_static_lods(source, bpy.context.scene)
    for obj in preview.objects:
        assert [layer.name for layer in obj.data.uv_layers] == ['UVMap', 'Lightmap']
        assert {face.material_index for face in obj.data.polygons} == {0, 1}
        assert all(isfinite(value) for layer in obj.data.uv_layers for item in layer.data for value in item.uv)
    preview.cancel()


def test_surface_diagnostics_are_read_only_and_detect_translation(source):
    from blender_adapter.lod_quality import inspect_static_lod
    copy = bpy.data.objects.new('Quality copy', source.data.copy())
    bpy.context.scene.collection.objects.link(copy)
    bpy.context.view_layer.update()
    source_before, copy_before = _signature(source), _signature(copy)
    report = inspect_static_lod(source, copy)
    assert report['max_distance'] < 1e-6
    assert report['sample_count'] > len(source.data.vertices) * 2
    assert (_signature(source), _signature(copy)) == (source_before, copy_before)
    copy.location.x = 3
    bpy.context.view_layer.update()
    moved = inspect_static_lod(source, copy)
    assert moved['max_distance'] > 2.9
    assert moved['rms_distance'] > 0


def test_reduced_surface_diagnostics(source):
    from blender_adapter.lod_quality import inspect_static_lod
    preview = preview_static_lods(source, bpy.context.scene)
    for obj, level in zip(preview.objects, preview.levels):
        before = _signature(obj)
        report = inspect_static_lod(source, obj)
        assert 0 < report['max_distance'] < .2
        assert report['level_triangles'] <= level.triangle_budget
        assert _signature(obj) == before
    preview.cancel()


def test_inspect_operator_preserves_preview(source, lod_operators):
    preview = preview_static_lods(source, bpy.context.scene)
    before = tuple(_signature(obj) for obj in (source,) + preview.objects)
    assert bpy.ops.asset_assistant.lod_inspect(collection_name=preview.collection.name,
                                             object_name=preview.objects[0].name) == {'FINISHED'}
    assert tuple(_signature(obj) for obj in (source,) + preview.objects) == before
    assert preview.collection['asset_assistant_lod_state'] == 'PREVIEW'
    preview.cancel()


@pytest.fixture
def second_source(source):
    obj = bpy.data.objects.new('Second static source', source.data.copy())
    bpy.context.scene.collection.objects.link(obj)
    return obj


def test_static_set_apply_preflights_every_member(source, second_source):
    from blender_adapter.lod_sets import preview_static_lod_set
    group = preview_static_lod_set([source, second_source], bpy.context.scene)
    second_source.data.vertices[0].co.x += .2
    with pytest.raises(ValueError, match='Source changed'):
        group.apply()
    assert all(p.collection['asset_assistant_lod_state'] == 'PREVIEW' for p in group.previews)
    assert group.state == 'PREVIEW'
    group.cancel()


def test_static_set_failure_rolls_back_completed_members(source, second_source, monkeypatch):
    from blender_adapter import lod_sets
    original = lod_sets.preview_static_lods
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes', 'collections')}
    def fail_second(obj, *args):
        if obj == second_source:
            raise ValueError('Injected second member failure')
        return original(obj, *args)
    monkeypatch.setattr(lod_sets, 'preview_static_lods', fail_second)
    with pytest.raises(ValueError, match='Injected'):
        lod_sets.preview_static_lod_set([source, second_source], bpy.context.scene)
    for kind, expected in before.items():
        assert set(getattr(bpy.data, kind)) == expected


def test_static_set_apply_preserves_both_sources(source, second_source):
    from blender_adapter.lod_sets import preview_static_lod_set
    sources = (source, second_source)
    before = tuple(_signature(obj) for obj in sources)
    group = preview_static_lod_set(sources, bpy.context.scene)
    assert [len(levels) for levels in group.apply()] == [2, 2]
    assert tuple(_signature(obj) for obj in sources) == before
    with pytest.raises(ValueError, match='active LOD set'):
        group.cancel()


def test_static_set_cancel_preflights_every_member(source, second_source):
    from blender_adapter.lod_sets import preview_static_lod_set
    group = preview_static_lod_set([source, second_source], bpy.context.scene)
    group.previews[1].collection.objects.link(source)
    before = set(bpy.data.objects)
    with pytest.raises(ValueError, match='collection changed'):
        group.cancel()
    assert set(bpy.data.objects) == before
    assert all(p.state == 'PREVIEW' for p in group.previews)
    group.previews[1].collection.objects.unlink(source)
    group.cancel()


def test_static_set_recovery_uses_member_references(source, second_source):
    from blender_adapter.lod_sets import preview_static_lod_set, recover_static_lod_set
    group = preview_static_lod_set([source, second_source], bpy.context.scene)
    group.previews[0].collection.name = 'Renamed member'
    recovered = recover_static_lod_set(group.record)
    assert tuple(p.source for p in recovered.previews) == (source, second_source)
    recovered.apply()
    with pytest.raises(ValueError, match='active LOD set'):
        group.cancel()


def test_static_set_recovery_rejects_missing_member(source, second_source):
    from blender_adapter.lod_sets import preview_static_lod_set, recover_static_lod_set
    group = preview_static_lod_set([source, second_source], bpy.context.scene)
    del group.record['member_1']
    before = set(bpy.data.objects)
    with pytest.raises(ValueError, match='missing or duplicated'):
        recover_static_lod_set(group.record)
    assert set(bpy.data.objects) == before
    group.record['member_1'] = group.previews[1].collection
    group.cancel()


def test_selected_mesh_group_operators(source, second_source, lod_operators):
    from blender_adapter.lod_ui import _groups
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    source.select_set(True)
    second_source.select_set(True)
    selected = set(bpy.context.selected_objects)
    assert bpy.ops.asset_assistant.lod_preview(use_selection=True) == {'FINISHED'}
    group, = _groups(bpy.context.scene)
    assert group['lod_set_count'] == 2
    assert set(bpy.context.selected_objects) == selected
    member = group['member_0']
    with pytest.raises(RuntimeError, match='complete LOD group'):
        bpy.ops.asset_assistant.lod_finish(collection_name=member.name, action='APPLY')
    assert bpy.ops.asset_assistant.lod_finish(collection_name=group.name, action='APPLY') == {'FINISHED'}
    assert group['lod_set_state'] == 'APPLIED'


def test_selected_mesh_group_discard(source, second_source, lod_operators):
    from blender_adapter.lod_ui import _groups
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    source.select_set(True)
    second_source.select_set(True)
    before = set(bpy.data.objects)
    bpy.ops.asset_assistant.lod_preview(use_selection=True)
    group, = _groups(bpy.context.scene)
    assert bpy.ops.asset_assistant.lod_finish(collection_name=group.name, action='CANCEL') == {'FINISHED'}
    assert set(bpy.data.objects) == before
    assert not _groups(bpy.context.scene)


def test_selected_group_rejects_non_mesh_without_staging(source, lod_operators):
    empty = bpy.data.objects.new('Artist helper', None)
    bpy.context.scene.collection.objects.link(empty)
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    source.select_set(True)
    empty.select_set(True)
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes', 'collections')}
    with pytest.raises(RuntimeError, match='static mesh'):
        bpy.ops.asset_assistant.lod_preview(use_selection=True)
    for kind, expected in before.items():
        assert set(getattr(bpy.data, kind)) == expected


def test_selected_group_rejects_existing_member_preview(source, second_source, lod_operators):
    preview = preview_static_lods(second_source, bpy.context.scene)
    source.select_set(True)
    second_source.select_set(True)
    before = set(bpy.data.objects)
    with pytest.raises(RuntimeError, match='existing preview'):
        bpy.ops.asset_assistant.lod_preview(use_selection=True)
    assert set(bpy.data.objects) == before
    preview.cancel()


def test_export_plan_separates_source_and_reduced_levels(source, second_source):
    from blender_adapter.lod_sets import preview_static_lod_set
    from blender_adapter.lod_export import plan_lod_export
    group = preview_static_lod_set([source, second_source], bpy.context.scene)
    with pytest.raises(ValueError, match='Apply'):
        plan_lod_export(group.record, bpy.context.scene)
    group.apply()
    before = set(bpy.data.objects)
    levels = plan_lod_export(group.record, bpy.context.scene)
    assert levels[0].meshes == (source, second_source)
    assert len(levels) == 3
    assert all(len(level.meshes) == 2 for level in levels)
    assert not any(obj in (source, second_source) for level in levels[1:] for obj in level.meshes)
    assert set(bpy.data.objects) == before


def test_export_plan_rejects_edited_applied_mesh(source):
    from blender_adapter.lod_export import plan_lod_export
    preview = preview_static_lods(source, bpy.context.scene)
    preview.apply()
    preview.objects[0].data.vertices[0].co.x += .2
    with pytest.raises(ValueError, match='data changed'):
        plan_lod_export(preview.collection, bpy.context.scene)


def test_static_lod_glb_bundle(source, tmp_path):
    import json
    from blender_adapter.lod_export import export_static_lod_bundle
    preview = preview_static_lods(source, bpy.context.scene)
    preview.apply()
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes')}
    selected = set(bpy.context.selected_objects)
    directory = tmp_path / 'lod-bundle'
    manifest = export_static_lod_bundle(preview.collection, bpy.context, directory)
    assert len(manifest['levels']) == 3
    assert not manifest['engine_lod_configured']
    assert json.loads((directory / 'lod-manifest.json').read_text()) == manifest
    for level in manifest['levels']:
        import struct
        data = (directory / level['file']).read_bytes()
        assert data[:4] == b'glTF'
        length, kind = struct.unpack_from('<II', data, 12)
        assert kind == 0x4E4F534A
        document = json.loads(data[20:20+length])
        assert len(document['meshes']) == level['mesh_count']
        triangles = sum(document['accessors'][primitive['indices']]['count'] // 3
                        for mesh in document['meshes'] for primitive in mesh['primitives'])
        assert triangles == level['triangles']
    assert set(bpy.context.selected_objects) == selected
    assert bpy.context.active_object == source
    for kind, expected in before.items():
        assert set(getattr(bpy.data, kind)) == expected
    with pytest.raises(ValueError, match='new bundle directory'):
        export_static_lod_bundle(preview.collection, bpy.context, directory)


def test_static_lod_bundle_failure_preserves_scene_and_destination(source, tmp_path, monkeypatch):
    from blender_adapter.lod_export import export_static_lod_bundle
    from blender_adapter import targets
    preview = preview_static_lods(source, bpy.context.scene)
    preview.apply()
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes')}
    def fail(*args, **kwargs):
        raise ValueError('Injected export failure')
    monkeypatch.setattr(targets, 'get_adapter', fail)
    destination = tmp_path / 'failed-bundle'
    with pytest.raises(ValueError, match='Injected'):
        export_static_lod_bundle(preview.collection, bpy.context, destination)
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []
    for kind, expected in before.items():
        assert set(getattr(bpy.data, kind)) == expected
