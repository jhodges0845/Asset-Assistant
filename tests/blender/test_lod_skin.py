# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
import pytest
from blender_adapter.lod_skin import inspect_skin_lod_source


@pytest.fixture
def skinned():
    objects = set(bpy.data.objects)
    meshes = set(bpy.data.meshes)
    rigs = set(bpy.data.armatures)
    bpy.ops.object.armature_add()
    rig = bpy.context.object
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    mesh = bpy.context.object
    group = mesh.vertex_groups.new(name=rig.data.bones[0].name)
    group.add(list(range(len(mesh.data.vertices))), 1, 'REPLACE')
    modifier = mesh.modifiers.new('Skin', 'ARMATURE')
    modifier.object = rig
    try:
        yield mesh, rig
    finally:
        for obj in set(bpy.data.objects) - objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for data in set(bpy.data.meshes) - meshes:
            bpy.data.meshes.remove(data)
        for data in set(bpy.data.armatures) - rigs:
            bpy.data.armatures.remove(data)


def test_skin_contract_preserves_authored_weights_and_pose(skinned):
    mesh, rig = skinned
    rig.pose.bones[0].rotation_mode = 'XYZ'
    rig.pose.bones[0].rotation_euler.x = .4
    before = tuple(tuple((g.group, g.weight) for g in v.groups) for v in mesh.data.vertices)
    result = inspect_skin_lod_source(mesh)
    assert result.armature == rig
    assert len(result.weights) == len(mesh.data.vertices)
    assert all(row == ((rig.data.bones[0].name, 1.0),) for row in result.weights)
    assert tuple(tuple((g.group, g.weight) for g in v.groups) for v in mesh.data.vertices) == before
    assert rig.pose.bones[0].rotation_euler.x == pytest.approx(.4)


def test_skin_contract_rejects_unweighted_and_unnormalized(skinned):
    mesh, _ = skinned
    mesh.vertex_groups[0].remove([0])
    with pytest.raises(ValueError, match='normalized'):
        inspect_skin_lod_source(mesh)
    mesh.vertex_groups[0].add([0], .5, 'REPLACE')
    with pytest.raises(ValueError, match='normalized'):
        inspect_skin_lod_source(mesh)
    assert mesh.vertex_groups[0].weight(0) == .5


def test_skin_contract_rejects_extra_artist_groups(skinned):
    mesh, _ = skinned
    group = mesh.vertex_groups.new(name='Artist selection')
    group.add([0], 1, 'REPLACE')
    with pytest.raises(ValueError, match='preservation policy'):
        inspect_skin_lod_source(mesh)
    assert group.weight(0) == 1


def test_skin_contract_rejects_envelopes_and_extra_modifiers(skinned):
    mesh, _ = skinned
    mesh.modifiers[0].use_bone_envelopes = True
    with pytest.raises(ValueError, match='envelopes'):
        inspect_skin_lod_source(mesh)
    mesh.modifiers[0].use_bone_envelopes = False
    mesh.modifiers.new('Artist subdivision', 'SUBSURF')
    with pytest.raises(ValueError, match='exactly one'):
        inspect_skin_lod_source(mesh)


def test_skin_transfer_rest_space_preserves_source_pose(skinned):
    from blender_adapter.lod_skin import plan_skin_lod_weights
    source, rig = skinned
    target = bpy.data.objects.new('Unrigged derivative', source.data.copy())
    bpy.context.scene.collection.objects.link(target)
    target.vertex_groups.clear()
    rig.pose.bones[0].rotation_mode = 'XYZ'
    rig.pose.bones[0].rotation_euler.x = .7
    bpy.context.view_layer.update()
    before = tuple(tuple((g.group, g.weight) for g in v.groups) for v in source.data.vertices)
    result = plan_skin_lod_weights(source, target)
    assert all(row == ((rig.data.bones[0].name, 1.0),) for row in result.weights)
    assert not target.vertex_groups
    assert not target.modifiers
    assert tuple(tuple((g.group, g.weight) for g in v.groups) for v in source.data.vertices) == before
    assert rig.pose.bones[0].rotation_euler.x == pytest.approx(.7)


def test_skin_transfer_interpolates_known_triangle(skinned):
    from blender_adapter.lod_skin import plan_skin_lod_weights
    source, rig = skinned
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bone = rig.data.edit_bones.new('Second')
    bone.head = (0, 0, 1)
    bone.tail = (0, 0, 2)
    bpy.ops.object.mode_set(mode='OBJECT')
    source.data = bpy.data.meshes.new('Rest triangle')
    source.data.from_pydata([(0, 0, 0), (2, 0, 0), (0, 2, 0)], [], [(0, 1, 2)])
    source.vertex_groups.new(name=rig.data.bones[0].name).add([0], 1, 'REPLACE')
    source.vertex_groups.new(name='Second').add([1, 2], 1, 'REPLACE')
    mesh = bpy.data.meshes.new('Target triangle')
    mesh.from_pydata([(.5, .5, 0), (1.2, 0, 0), (0, 1.2, 0)], [], [(0, 1, 2)])
    target = bpy.data.objects.new('Derivative', mesh)
    bpy.context.scene.collection.objects.link(target)
    result = plan_skin_lod_weights(source, target)
    first = dict(result.weights[0])
    assert first[rig.data.bones[0].name] == pytest.approx(.5)
    assert first['Second'] == pytest.approx(.5)
    assert all(sum(weight for _, weight in row) == pytest.approx(1) for row in result.weights)


def test_bound_candidate_matches_single_bone_motion(skinned):
    from blender_adapter.lod_skin import build_skin_lod_candidate
    source, rig = skinned
    target = bpy.data.objects.new('Reduced input', source.data.copy())
    bpy.context.scene.collection.objects.link(target)
    target.vertex_groups.clear()
    source.modifiers[0].use_deform_preserve_volume = True
    before = set(bpy.data.objects)
    candidate = build_skin_lod_candidate(source, target, bpy.context.scene, max_distance=.001)
    assert set(bpy.data.objects) - before == {candidate}
    assert candidate.data != target.data
    assert not target.modifiers and not target.vertex_groups
    assert candidate.modifiers[0].use_deform_preserve_volume
    for angle in (0, .4, -.7):
        rig.pose.bones[0].rotation_mode = 'XYZ'
        rig.pose.bones[0].rotation_euler.x = angle
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        left = source.evaluated_get(graph)
        right = candidate.evaluated_get(graph)
        assert max((left.matrix_world @ a.co - right.matrix_world @ b.co).length
                   for a, b in zip(left.data.vertices, right.data.vertices)) < 1e-5


def test_transfer_distance_rejects_candidate_without_staging(skinned):
    from blender_adapter.lod_skin import build_skin_lod_candidate
    source, _ = skinned
    target = bpy.data.objects.new('Distant input', source.data.copy())
    bpy.context.scene.collection.objects.link(target)
    target.vertex_groups.clear()
    target.location.x = 10
    bpy.context.view_layer.update()
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes')}
    with pytest.raises(ValueError, match='maximum skin transfer distance'):
        build_skin_lod_candidate(source, target, bpy.context.scene, max_distance=.1)
    for kind, expected in before.items():
        assert set(getattr(bpy.data, kind)) == expected


def test_actual_skinned_reduction_preserves_source_and_cleans_proxies(skinned):
    from blender_adapter.lod_skin import build_reduced_skin_lod_candidates
    from blender_adapter.lod import _signature, _triangles
    source, rig = skinned
    before = _signature(source)
    weights = inspect_skin_lod_source(source).weights
    objects = set(bpy.data.objects)
    collections = set(bpy.data.collections)
    candidates = build_reduced_skin_lod_candidates(source, bpy.context.scene, max_distance=.3)
    assert set(bpy.data.objects) - objects == set(candidates)
    assert set(bpy.data.collections) == collections
    for candidate in candidates:
        assert _triangles(candidate.data) <= candidate['asset_assistant_lod_budget']
        assert _triangles(candidate.data) < _triangles(source.data)
        assert inspect_skin_lod_source(candidate).armature == rig
    assert _signature(source) == before
    assert inspect_skin_lod_source(source).weights == weights


def test_reduced_skin_failure_cleans_completed_candidates(skinned, monkeypatch):
    from blender_adapter import lod_skin
    source, _ = skinned
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes', 'collections')}
    original = lod_skin.build_skin_lod_candidate
    calls = []
    def fail_second(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise ValueError('Injected second skin failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(lod_skin, 'build_skin_lod_candidate', fail_second)
    with pytest.raises(ValueError, match='Injected'):
        lod_skin.build_reduced_skin_lod_candidates(source, bpy.context.scene, max_distance=.3)
    for kind, expected in before.items():
        assert set(getattr(bpy.data, kind)) == expected


def test_reduced_two_bone_candidate_matches_weighted_deformation(skinned):
    from mathutils import Vector
    from blender_adapter.lod_skin import build_reduced_skin_lod_candidates
    source, rig = skinned
    first_name = rig.data.bones[0].name
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    second = rig.data.edit_bones.new('Blend bone')
    second.head, second.tail = (0, 0, 0), (0, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    group = source.vertex_groups.new(name='Blend bone')
    for vertex in source.data.vertices:
        weight = max(.1, min(.9, (vertex.co.z + 1) / 2))
        source.vertex_groups[first_name].add([vertex.index], 1 - weight, 'REPLACE')
        group.add([vertex.index], weight, 'REPLACE')
    candidates = build_reduced_skin_lod_candidates(source, bpy.context.scene, ratios=(.5,), max_distance=.3)
    candidate, = candidates
    weights = inspect_skin_lod_source(candidate).weights
    assert any(len(row) == 2 for row in weights)
    for angle in (0, .4, -.6):
        for name, factor in ((first_name, 1), ('Blend bone', -1)):
            rig.pose.bones[name].rotation_mode = 'XYZ'
            rig.pose.bones[name].rotation_euler.x = angle * factor
        bpy.context.view_layer.update()
        transforms = {name: rig.pose.bones[name].matrix @ rig.data.bones[name].matrix_local.inverted()
                      for name in (first_name, 'Blend bone')}
        evaluated = candidate.evaluated_get(bpy.context.evaluated_depsgraph_get())
        for vertex, row, actual in zip(candidate.data.vertices, weights, evaluated.data.vertices):
            expected = sum((transforms[name] @ vertex.co * weight for name, weight in row), Vector((0, 0, 0)))
            assert (expected - actual.co).length < 1e-5


def test_skin_preview_apply_and_cancel_lifecycle(skinned):
    from blender_adapter.lod_skin_preview import preview_skin_lods, recover_skin_lod_preview
    source, rig = skinned
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'meshes', 'collections')}
    preview = preview_skin_lods(source, bpy.context.scene, max_distance=.3)
    recover_skin_lod_preview(preview.collection).cancel()
    for kind, expected in before.items():
        assert set(getattr(bpy.data, kind)) == expected
    preview = preview_skin_lods(source, bpy.context.scene, max_distance=.3)
    rig.pose.bones[0].rotation_mode = 'XYZ'
    rig.pose.bones[0].rotation_euler.x = .4
    preview.apply()
    assert preview.collection['asset_assistant_lod_state'] == 'APPLIED'


def test_skin_preview_weight_edit_blocks_apply(skinned):
    from blender_adapter.lod_skin_preview import preview_skin_lods
    source, _ = skinned
    preview = preview_skin_lods(source, bpy.context.scene, max_distance=.3)
    preview.objects[0].vertex_groups[0].add([0], .5, 'REPLACE')
    with pytest.raises(ValueError, match='normalized'):
        preview.apply()
    assert preview.collection['asset_assistant_lod_state'] == 'PREVIEW'
    preview.cancel()


def test_skin_preview_rest_bone_edit_blocks_apply(skinned):
    from blender_adapter.lod_skin_preview import preview_skin_lods
    source, rig = skinned
    preview = preview_skin_lods(source, bpy.context.scene, max_distance=.3)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    rig.data.edit_bones[0].tail.z += .1
    bpy.ops.object.mode_set(mode='OBJECT')
    with pytest.raises(ValueError, match='rest rig changed'):
        preview.apply()
    preview.cancel()


@pytest.fixture
def skin_operators():
    from blender_adapter import lod_ui
    lod_ui.register()
    try:
        yield
    finally:
        lod_ui.unregister()


def test_skin_preview_operators_preserve_selection_and_apply(skinned, skin_operators):
    from blender_adapter.lod_ui import _skin_previews
    source, _ = skinned
    selected = set(bpy.context.selected_objects)
    assert bpy.ops.asset_assistant.skin_lod_preview(max_distance=.3) == {'FINISHED'}
    preview, = _skin_previews(bpy.context.scene)
    assert set(bpy.context.selected_objects) == selected
    assert bpy.context.active_object == source
    with pytest.raises(RuntimeError, match='existing preview'):
        bpy.ops.asset_assistant.skin_lod_preview(max_distance=.3)
    assert bpy.ops.asset_assistant.lod_finish(collection_name=preview.name, action='APPLY') == {'FINISHED'}
    assert preview['asset_assistant_lod_state'] == 'APPLIED'


def test_skin_preview_operator_discard_and_wrong_selection(skinned, skin_operators):
    from blender_adapter.lod_ui import _skin_previews
    source, rig = skinned
    before = set(bpy.data.objects)
    bpy.context.view_layer.objects.active = rig
    with pytest.raises(RuntimeError, match='skinned mesh'):
        bpy.ops.asset_assistant.skin_lod_preview(max_distance=.3)
    assert set(bpy.data.objects) == before
    bpy.context.view_layer.objects.active = source
    bpy.ops.asset_assistant.skin_lod_preview(max_distance=.3)
    preview, = _skin_previews(bpy.context.scene)
    assert bpy.ops.asset_assistant.lod_finish(collection_name=preview.name, action='CANCEL') == {'FINISHED'}
    assert set(bpy.data.objects) == before


def test_posed_skin_inspection_preserves_frame_pose_and_geometry(skinned, skin_operators):
    from blender_adapter.lod_skin_preview import preview_skin_lods, _skin_signature
    from blender_adapter.lod_quality import inspect_posed_skin_lod
    source, rig = skinned
    preview = preview_skin_lods(source, bpy.context.scene, ratios=(.5,), max_distance=.3)
    rig.pose.bones[0].rotation_mode = 'XYZ'
    rig.pose.bones[0].rotation_euler.x = .6
    bpy.context.view_layer.update()
    before = _skin_signature(source)
    frame = bpy.context.scene.frame_current
    result = inspect_posed_skin_lod(source, preview.objects[0], bpy.context.evaluated_depsgraph_get())
    assert 0 < result['max_distance'] < .3
    assert bpy.ops.asset_assistant.lod_inspect(collection_name=preview.collection.name,
                                            object_name=preview.objects[0].name) == {'FINISHED'}
    assert _skin_signature(source) == before
    assert bpy.context.scene.frame_current == frame
    assert rig.pose.bones[0].rotation_euler.x == pytest.approx(.6)
    preview.cancel()


def test_skin_export_plan_keeps_rig_without_source_in_reduced_level(skinned):
    from blender_adapter.lod_skin_preview import preview_skin_lods
    from blender_adapter.lod_export import plan_lod_export
    source, rig = skinned
    preview = preview_skin_lods(source, bpy.context.scene, max_distance=.3)
    preview.apply()
    levels = plan_lod_export(preview.collection, bpy.context.scene)
    assert levels[0].meshes == (source,)
    assert all(level.armatures == (rig,) for level in levels)
    assert all(source not in level.meshes for level in levels[1:])


def test_skin_export_staging_preserves_binding_pose_and_cleanup(skinned):
    from blender_adapter.lod_export import plan_lod_export
    from blender_adapter.lod_skin_preview import preview_skin_lods, _skin_signature
    from blender_adapter.lod_skin_export import stage_skin_lod_level
    source, rig = skinned
    preview = preview_skin_lods(source, bpy.context.scene, max_distance=.3)
    preview.apply()
    rig.pose.bones[0].rotation_mode = 'XYZ'
    rig.pose.bones[0].rotation_euler.x = .4
    bpy.context.view_layer.update()
    signature = _skin_signature(source)
    before = {key: set(getattr(bpy.data, key)) for key in ('objects', 'meshes', 'armatures')}
    level = plan_lod_export(preview.collection, bpy.context.scene)[1]
    with pytest.raises(RuntimeError, match='Injected'):
        with stage_skin_lod_level(level, bpy.context.scene) as root:
            children = list(root.children)
            mesh = next(obj for obj in children if obj.type == 'MESH')
            copied_rig = next(obj for obj in children if obj.type == 'ARMATURE')
            assert mesh.data != level.meshes[0].data
            assert copied_rig.data != rig.data
            assert mesh.modifiers[0].object == copied_rig
            assert source not in children
            assert inspect_skin_lod_source(mesh).weights == inspect_skin_lod_source(level.meshes[0]).weights
            graph = bpy.context.evaluated_depsgraph_get()
            expected = level.meshes[0].evaluated_get(graph)
            actual = mesh.evaluated_get(graph)
            for a, b in zip(expected.data.vertices, actual.data.vertices):
                assert (expected.matrix_world @ a.co - actual.matrix_world @ b.co).length < 1e-6
            raise RuntimeError('Injected')
    assert _skin_signature(source) == signature
    assert rig.pose.bones[0].rotation_euler.x == pytest.approx(.4)
    for key, values in before.items():
        assert set(getattr(bpy.data, key)) == values


def test_skin_export_staging_rejects_external_dependencies(skinned):
    from blender_adapter.lod_export import plan_lod_export
    from blender_adapter.lod_skin_preview import preview_skin_lods
    from blender_adapter.lod_skin_export import stage_skin_lod_level
    source, rig = skinned
    preview = preview_skin_lods(source, bpy.context.scene, max_distance=.3)
    preview.apply()
    level = plan_lod_export(preview.collection, bpy.context.scene)[1]
    rig.pose.bones[0].constraints.new('COPY_LOCATION')
    before = set(bpy.data.objects)
    with pytest.raises(ValueError, match='external dependencies'):
        with stage_skin_lod_level(level, bpy.context.scene):
            pytest.fail('Unsupported rig was staged')
    assert set(bpy.data.objects) == before
    assert len(rig.pose.bones[0].constraints) == 1


def test_skin_level_serializes_generated_clip_without_artist_mutation(skinned, tmp_path):
    import json
    import struct
    from blender_adapter.lod_export import plan_lod_export
    from blender_adapter.lod_skin_preview import preview_skin_lods
    from blender_adapter.lod_skin_export import export_skin_lod_level
    source, rig = skinned
    source.data.materials.append(bpy.data.materials.new('LOD test material'))
    rig['asset_assistant_rig_id'] = 'lod-export-test'
    bone = rig.pose.bones[0]
    bone.rotation_mode = 'XYZ'
    for frame, angle in ((1, 0), (12, .5), (24, 0)):
        bone.rotation_euler.x = angle
        bone.keyframe_insert('rotation_euler', frame=frame)
    action = rig.animation_data.action
    action['asset_assistant_generated'] = True
    action['asset_assistant_rig_id'] = 'lod-export-test'
    action['asset_assistant_clip'] = 'TestMotion'
    second = action.copy()
    second['asset_assistant_clip'] = 'SecondMotion'
    try:
        preview = preview_skin_lods(source, bpy.context.scene, ratios=(.5,), max_distance=.3)
        preview.apply()
        level = plan_lod_export(preview.collection, bpy.context.scene)[1]
        original_slot = rig.animation_data.action_slot
        before = {key: set(getattr(bpy.data, key)) for key in ('objects', 'meshes', 'armatures', 'actions')}
        path = tmp_path / 'skin.glb'
        result = export_skin_lod_level(level, bpy.context, path)
        assert result.success, [(issue.code, issue.message) for issue in result.issues if issue.status in ('ERROR', 'WARN')]
        raw = path.read_bytes()
        length = struct.unpack_from('<I', raw, 12)[0]
        document = json.loads(raw[20:20+length])
        assert len(document['skins']) == 1
        assert len(document['meshes']) == 1
        assert {clip['name'] for clip in document['animations']} == {'TestMotion', 'SecondMotion'}
        assert any('JOINTS_0' in primitive['attributes'] and 'WEIGHTS_0' in primitive['attributes']
                   for primitive in document['meshes'][0]['primitives'])
        assert rig.animation_data.action == action
        assert rig.animation_data.action_slot == original_slot
        assert not rig.animation_data.nla_tracks
        for key, values in before.items():
            assert set(getattr(bpy.data, key)) == values
    finally:
        rig.animation_data_clear()
        bpy.data.actions.remove(action)
        bpy.data.actions.remove(second)
