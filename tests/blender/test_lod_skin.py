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


@pytest.fixture
def enabled_weight_extension():
    import addon_utils
    addon_utils.enable('blender_adapter', default_set=True, persistent=False)
    try:
        from blender_adapter.lod_weight_export import extension_available
        assert extension_available()
        yield
    finally:
        addon_utils.disable('blender_adapter', default_set=True)


@pytest.mark.parametrize("influences, small_weight", ((1, None), (8, None), (2, 1.000001e-4),
                                                     (2, 1e-8), (2, .00005), (2, .0001)))
def test_skin_level_serializes_generated_clip_without_artist_mutation(skinned, tmp_path, influences, small_weight, request):
    if small_weight is not None and small_weight <= .0001:
        request.getfixturevalue("enabled_weight_extension")
    import json
    import struct
    from blender_adapter.lod_export import plan_lod_export
    from blender_adapter.lod_skin_preview import preview_skin_lods
    from blender_adapter.lod_export import export_skin_lod_bundle
    source, rig = skinned
    if influences > 1:
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        for index in range(influences - 1):
            extra = rig.data.edit_bones.new('Influence%d' % index)
            extra.head = (index + 1, 0, 0)
            extra.tail = (index + 1, 0, 1)
        bpy.ops.object.mode_set(mode='OBJECT')
        for joint in rig.data.bones:
            group = source.vertex_groups.get(joint.name) or source.vertex_groups.new(name=joint.name)
            group.add(list(range(len(source.data.vertices))), 1 / influences, 'REPLACE')
    if small_weight is not None:
        indices = list(range(len(source.data.vertices)))
        source.vertex_groups[0].add(indices, 1 - small_weight, 'REPLACE')
        source.vertex_groups[1].add(indices, small_weight, 'REPLACE')
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
    from blender_adapter.animation import action_curves
    for curve in action_curves(action, rig.animation_data.action_slot):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    second = action.copy()
    second['asset_assistant_clip'] = 'SecondMotion'
    try:
        preview = preview_skin_lods(source, bpy.context.scene, ratios=(.5,), max_distance=.3)
        preview.apply()
        level = plan_lod_export(preview.collection, bpy.context.scene)[1]
        original_slot = rig.animation_data.action_slot
        before = {key: set(getattr(bpy.data, key)) for key in ('objects', 'meshes', 'armatures', 'actions')}
        destination = tmp_path / 'skin-bundle'
        manifest = export_skin_lod_bundle(preview.collection, bpy.context, destination)
        assert len(manifest['levels']) == 2
        assert not manifest['engine_lod_configured']
        for entry in manifest['levels']:
            raw = (destination / entry['file']).read_bytes()
            length = struct.unpack_from('<I', raw, 12)[0]
            document = json.loads(raw[20:20+length])
            assert len(document['skins']) == 1
            assert len(document['skins'][0]['joints']) == influences
            if influences == 8:
                assert all('JOINTS_1' in primitive['attributes'] and 'WEIGHTS_1' in primitive['attributes']
                           for primitive in document['meshes'][0]['primitives'])
            if small_weight is not None:
                for primitive in document['meshes'][0]['primitives']:
                    accessor = document['accessors'][primitive['attributes']['WEIGHTS_0']]
                    assert accessor['componentType'] == 5126
                    view = document['bufferViews'][accessor['bufferView']]
                    offset = 20 + length + 8 + view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
                    weights = struct.unpack_from('<4f', raw, offset)
                    assert sorted(w for w in weights if w > 0) == pytest.approx(
                        struct.unpack('<2f', struct.pack('<2f', small_weight, 1 - small_weight)), abs=1e-10)
            assert len(document['meshes']) == 1
            assert {clip['name'] for clip in document['animations']} == {'TestMotion', 'SecondMotion'}
            triangles = sum(document['accessors'][primitive['indices']]['count'] // 3
                            for primitive in document['meshes'][0]['primitives'])
            assert triangles == entry['triangles']
            assert all('JOINTS_0' in primitive['attributes'] and 'WEIGHTS_0' in primitive['attributes']
                       for primitive in document['meshes'][0]['primitives'])
        with pytest.raises(ValueError, match='new bundle directory'):
            export_skin_lod_bundle(preview.collection, bpy.context, destination)
        assert rig.animation_data.action == action
        assert rig.animation_data.action_slot == original_slot
        assert not rig.animation_data.nla_tracks
        for key, values in before.items():
            assert set(getattr(bpy.data, key)) == values
    finally:
        rig.animation_data_clear()
        bpy.data.actions.remove(action)
        bpy.data.actions.remove(second)


def test_skin_bundle_failure_does_not_publish(skinned, tmp_path, monkeypatch):
    from blender_adapter.lod_export import export_skin_lod_bundle
    from blender_adapter.lod_skin_preview import preview_skin_lods
    from blender_adapter import lod_skin_export
    source, rig = skinned
    preview = preview_skin_lods(source, bpy.context.scene, max_distance=.3)
    preview.apply()
    before = set(bpy.data.objects)
    def fail(level, context, path):
        path.write_bytes(b'partial')
        raise ValueError('Injected serializer failure')
    monkeypatch.setattr(lod_skin_export, 'export_skin_lod_level', fail)
    with pytest.raises(ValueError, match='Injected'):
        export_skin_lod_bundle(preview.collection, bpy.context, tmp_path / 'failed')
    assert not list(tmp_path.iterdir())
    assert set(bpy.data.objects) == before


def test_parented_skin_staging_preserves_animated_world_space(skinned, tmp_path):
    from blender_adapter.lod_export import plan_lod_export
    from blender_adapter.lod_skin_preview import preview_skin_lods
    from blender_adapter.lod_skin_export import stage_skin_lod_level
    from mathutils import Matrix, Quaternion
    source, rig = skinned
    parent = bpy.data.objects.new('Static artist root', None)
    bpy.context.scene.collection.objects.link(parent)
    parent.location = (3, -2, .7)
    parent.rotation_euler.z = .6
    rig.parent = parent
    rig.matrix_parent_inverse = Matrix.Translation((-.3, .2, 0))
    rig['asset_assistant_rig_id'] = 'parent-lod-test'
    for frame, offset in ((1, 0), (12, .4), (24, 0)):
        rig.pose.bones[0].location.x = offset
        rig.pose.bones[0].keyframe_insert('location', frame=frame)
        rig.pose.bones[0].rotation_mode = 'QUATERNION'
        rig.pose.bones[0].rotation_quaternion = Quaternion((0, 0, 1), offset * 2)
        rig.pose.bones[0].keyframe_insert('rotation_quaternion', frame=frame)
    action = rig.animation_data.action
    action['asset_assistant_generated'] = True
    action['asset_assistant_rig_id'] = 'parent-lod-test'
    action['asset_assistant_clip'] = 'RootMotion'
    from blender_adapter.animation import action_curves
    for curve in action_curves(action, rig.animation_data.action_slot):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    scene = bpy.context.scene
    frame, subframe = scene.frame_current, scene.frame_subframe
    try:
        scene.frame_set(1)
        preview = preview_skin_lods(source, scene, ratios=(.5,), max_distance=.3)
        preview.apply()
        level = plan_lod_export(preview.collection, scene)[1]
        with stage_skin_lod_level(level, scene, generated_clips=True) as root:
            copied_rig = next(obj for obj in root.children if obj.type == 'ARMATURE')
            mesh = next(obj for obj in root.children if obj.type == 'MESH')
            for sample in (1, 6, 12, 18, 24):
                scene.frame_set(sample)
                for a, b in zip(rig.matrix_world, copied_rig.matrix_world):
                    assert tuple(a) == pytest.approx(tuple(b), abs=1e-6)
                graph = bpy.context.evaluated_depsgraph_get()
                expected = level.meshes[0].evaluated_get(graph)
                actual = mesh.evaluated_get(graph)
                for a, b in zip(expected.data.vertices, actual.data.vertices):
                    assert (expected.matrix_world @ a.co - actual.matrix_world @ b.co).length < 1e-5
        assert rig.parent == parent
        assert rig.animation_data.action == action
        # Exercise the real writer with the same nontrivial parent transform.
        scene.frame_set(1)
        source.data.materials.append(bpy.data.materials.new('Parent export material'))
        # This material edit requires an explicitly rebuilt preview.
        rebuilt = preview_skin_lods(source, scene, ratios=(.5,), max_distance=.3)
        rebuilt.apply()
        from blender_adapter.lod_export import export_skin_lod_bundle
        result = export_skin_lod_bundle(rebuilt.collection, bpy.context, tmp_path / 'parented')
        assert len(result['levels']) == 2
        samples = tuple(1 + step * 23 / 48 for step in range(49))
        def world_points(obj):
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            return [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
        expected = {}
        for sample in samples:
            scene.frame_set(int(sample), subframe=sample - int(sample))
            expected[sample] = world_points(rebuilt.objects[0])
        before_objects = set(bpy.data.objects)
        before_actions = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=str(tmp_path / 'parented' / 'LOD1.glb'))
        imported = set(bpy.data.objects) - before_objects
        try:
            imported_mesh = next(obj for obj in imported if obj.type == 'MESH'
                                 and any(mod.type == 'ARMATURE' for mod in obj.modifiers))
            imported_rig = next(obj for obj in imported if obj.type == 'ARMATURE')
            data = imported_rig.animation_data
            assert data is not None
            if data.action is None:
                strips = [strip for track in data.nla_tracks for strip in track.strips]
                assert len(strips) == 1
                data.action = strips[0].action
                if hasattr(strips[0], 'action_slot'):
                    data.action_slot = strips[0].action_slot
            for track in data.nla_tracks:
                track.mute = True
            start = data.action.frame_range[0]
            from mathutils.kdtree import KDTree
            for sample in samples:
                # Export clips start at zero; align the imported action start.
                aligned = start + sample - 1
                scene.frame_set(int(aligned), subframe=aligned - int(aligned))
                actual = world_points(imported_mesh)
                # GLB may split vertices at UV/normal seams; compare both ways.
                for left, right in ((actual, expected[sample]), (expected[sample], actual)):
                    tree = KDTree(len(right))
                    for index, point in enumerate(right):
                        tree.insert(point, index)
                    tree.balance()
                    assert max(tree.find(point)[2] for point in left) < 1e-5, (sample, start, tuple(imported_rig.location), data.action.name)
        finally:
            for obj in imported:
                bpy.data.objects.remove(obj, do_unlink=True)
            for imported_action in set(bpy.data.actions) - before_actions:
                bpy.data.actions.remove(imported_action)
        curve = action_curves(action, rig.animation_data.action_slot)[0]
        key = curve.keyframe_points[0]
        key.interpolation = 'BEZIER'
        with pytest.raises(ValueError, match='linear or constant'):
            with stage_skin_lod_level(level, scene, generated_clips=True):
                pytest.fail('Unverified Bezier animation accepted')
        assert key.interpolation == 'BEZIER'
        key.interpolation = 'LINEAR'
        rig.keyframe_insert('location', frame=1)
        with pytest.raises(ValueError, match='bone channels'):
            with stage_skin_lod_level(level, scene, generated_clips=True):
                pytest.fail('Object animation accepted')
        parent.keyframe_insert('location', frame=1)
        with pytest.raises(ValueError, match='static empty'):
            with stage_skin_lod_level(level, scene):
                pytest.fail('Animated parent accepted')
    finally:
        parent_action = parent.animation_data.action if parent.animation_data else None
        parent.animation_data_clear()
        if parent_action:
            bpy.data.actions.remove(parent_action)
        rig.animation_data_clear()
        bpy.data.actions.remove(action)
        scene.frame_set(frame, subframe=subframe)


def test_skin_export_rejects_silent_influence_truncation(skinned):
    from blender_adapter.lod_skin_export import stage_skin_lod_level
    from blender_adapter.lod_export import LODExportLevel
    source, rig = skinned
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for index in range(8):
        bone = rig.data.edit_bones.new('Extra%d' % index)
        bone.head = (index + 1, 0, 0)
        bone.tail = (index + 1, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    for bone in rig.data.bones:
        group = source.vertex_groups.get(bone.name) or source.vertex_groups.new(name=bone.name)
        group.add(list(range(len(source.data.vertices))), 1 / 9, 'REPLACE')
    before = inspect_skin_lod_source(source).weights
    objects = set(bpy.data.objects)
    level = LODExportLevel(0, (source,), (rig,), 0)
    with pytest.raises(ValueError, match='eight influences'):
        with stage_skin_lod_level(level, bpy.context.scene, generated_clips=True):
            pytest.fail('Exporter would truncate weights')
    assert inspect_skin_lod_source(source).weights == before
    assert set(bpy.data.objects) == objects


@pytest.mark.parametrize('small_weight', (1e-8, 0.00005, 0.0001))
def test_skin_export_blocks_small_weight_loss_without_mutation(skinned, small_weight, tmp_path):
    from blender_adapter.lod_skin_export import stage_skin_lod_level
    from blender_adapter.lod_export import LODExportLevel
    source, rig = skinned
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    extra = rig.data.edit_bones.new('SmallInfluence')
    extra.head, extra.tail = (1, 0, 0), (1, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    group = source.vertex_groups.new(name='SmallInfluence')
    group.add([0], small_weight, 'REPLACE')
    source.vertex_groups[0].add([0], 1 - small_weight, 'REPLACE')
    before = inspect_skin_lod_source(source).weights
    datablocks = {key: set(getattr(bpy.data, key)) for key in ('objects', 'meshes', 'armatures', 'actions')}
    level = LODExportLevel(0, (source,), (rig,), 0)
    with pytest.raises(ValueError, match='would discard SmallInfluence weight'):
        with stage_skin_lod_level(level, bpy.context.scene, generated_clips=True):
            pytest.fail('Small skin weight would be silently discarded')
    assert inspect_skin_lod_source(source).weights == before
    for key, values in datablocks.items():
        assert set(getattr(bpy.data, key)) == values
    # Preview/pose staging does not serialize and must retain small weights.
    with stage_skin_lod_level(level, bpy.context.scene) as root:
        mesh = next(obj for obj in root.children if obj.type == 'MESH')
        assert inspect_skin_lod_source(mesh).weights == before

    from blender_adapter.lod_skin_preview import preview_skin_lods
    from blender_adapter.lod_export import export_skin_lod_bundle
    preview = preview_skin_lods(source, bpy.context.scene, ratios=(.5,), max_distance=.3)
    preview.apply()
    objects = set(bpy.data.objects)
    selected = set(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    with pytest.raises(ValueError, match='would discard'):
        export_skin_lod_bundle(preview.collection, bpy.context, tmp_path / 'rejected')
    assert not list(tmp_path.iterdir())
    assert inspect_skin_lod_source(source).weights == before
    assert set(bpy.data.objects) == objects
    assert set(bpy.context.selected_objects) == selected
    assert bpy.context.view_layer.objects.active == active


@pytest.mark.parametrize('failure', ('missing', 'critical', 'provenance'))
def test_weight_hook_failure_cleans_bundle(skinned, enabled_weight_extension, monkeypatch, tmp_path, failure):
    from blender_adapter.lod_weight_export import WeightExportExtension, _scope
    from blender_adapter.lod_skin_preview import preview_skin_lods
    from blender_adapter.lod_export import export_skin_lod_bundle
    source, rig = skinned
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bone = rig.data.edit_bones.new('Tiny')
    bone.head, bone.tail = (1, 0, 0), (1, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    source.vertex_groups.new(name='Tiny').add([0], .00001, 'REPLACE')
    source.vertex_groups[0].add([0], .99999, 'REPLACE')
    source.data.materials.append(bpy.data.materials.new('Hook failure material'))
    rig['asset_assistant_rig_id'] = 'hook-failure'
    rig.pose.bones[0].keyframe_insert('rotation_euler', frame=1)
    rig.pose.bones[0].rotation_euler.x = .5
    rig.pose.bones[0].keyframe_insert('rotation_euler', frame=12)
    action = rig.animation_data.action
    action['asset_assistant_generated'] = True
    action['asset_assistant_clip'] = 'HookTest'
    action['asset_assistant_rig_id'] = rig['asset_assistant_rig_id']
    from blender_adapter.animation import action_curves
    for curve in action_curves(action, rig.animation_data.action_slot):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    preview = preview_skin_lods(source, bpy.context.scene, ratios=(.5,), max_distance=.3)
    preview.apply()
    before = inspect_skin_lod_source(source).weights
    objects = set(bpy.data.objects)
    attrs = tuple(source.data.attributes.keys())
    original = WeightExportExtension.gather_mesh_hook
    calls = []
    def broken(self, mesh, data, obj, groups, modifiers, materials, settings):
        calls.append(obj)
        if failure == 'missing':
            return
        if failure == 'critical':
            raise RuntimeError('Injected critical hook failure')
        mesh.primitives[0].attributes.pop(_scope.get()['marker'].upper())
        return original(self, mesh, data, obj, groups, modifiers, materials, settings)
    monkeypatch.setattr(WeightExportExtension, 'gather_mesh_hook', broken)
    try:
        with pytest.raises(ValueError, match='LOD export failed') as error:
            export_skin_lod_bundle(preview.collection, bpy.context, tmp_path / 'rejected')
        assert calls, str(error.value)
        assert not list(tmp_path.iterdir())
        assert _scope.get() is None
        assert set(bpy.data.objects) == objects
        assert tuple(source.data.attributes.keys()) == attrs
        assert inspect_skin_lod_source(source).weights == before
    finally:
        rig.animation_data_clear()
        bpy.data.actions.remove(action)


def test_weight_hook_maps_eight_distinct_influences_across_materials(skinned, enabled_weight_extension, tmp_path):
    import json
    import struct
    from blender_adapter.lod_export import LODExportLevel
    from blender_adapter.lod_skin_export import stage_skin_lod_level
    from blender_adapter.lod_weight_export import preserve_weights
    source, rig = skinned
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for i in range(7):
        bone = rig.data.edit_bones.new('Tiny' + str(i))
        bone.head, bone.tail = (i + 1, 0, 0), (i + 1, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    for bone in list(rig.data.bones)[1:]:
        source.vertex_groups.new(name=bone.name)
    for vertex in source.data.vertices:
        tiny = [(vertex.index + 1) * (i + 1) * 1e-8 for i in range(7)]
        for group, weight in zip(source.vertex_groups, [1 - sum(tiny)] + tiny):
            group.add([vertex.index], weight, 'REPLACE')
    materials = [bpy.data.materials.new(name) for name in ('HookFirst', 'HookSecond')]
    for material in materials:
        source.data.materials.append(material)
    for polygon in source.data.polygons:
        polygon.material_index = polygon.index % 2
    source.data.attributes.new('_artist_private', 'FLOAT', 'POINT')
    expected = inspect_skin_lod_source(source).weights
    attributes = tuple(source.data.attributes.keys())
    path = tmp_path / 'eight.glb'
    try:
        with stage_skin_lod_level(LODExportLevel(0, (source,), (rig,), 0), bpy.context.scene) as root:
            for obj in bpy.context.selected_objects:
                obj.select_set(False)
            for obj in root.children:
                obj.select_set(True)
            with preserve_weights(root, dict(filepath=str(path), use_selection=True,
                                            export_all_influences=True)) as options:
                assert bpy.ops.export_scene.gltf(**options) == {'FINISHED'}
        raw = path.read_bytes()
        length = struct.unpack_from('<I', raw, 12)[0]
        doc = json.loads(raw[20:20 + length])
        def accessor(index, fmt):
            acc = doc['accessors'][index]
            view = doc['bufferViews'][acc['bufferView']]
            offset = 28 + length + view.get('byteOffset', 0) + acc.get('byteOffset', 0)
            stride = view.get('byteStride', struct.calcsize(fmt))
            return [struct.unpack_from(fmt, raw, offset + i * stride) for i in range(acc['count'])]
        names = [doc['nodes'][index]['name'] for index in doc['skins'][0]['joints']]
        covered = set()
        primitives = doc['meshes'][0]['primitives']
        assert len(primitives) == 2
        for primitive in primitives:
            attrs = primitive['attributes']
            assert not any(key.startswith('_AA_LOD_') for key in attrs)
            assert '_ARTIST_PRIVATE' not in attrs
            joints = [a + b for a, b in zip(accessor(attrs['JOINTS_0'], '<4H'), accessor(attrs['JOINTS_1'], '<4H'))]
            weights = [a + b for a, b in zip(accessor(attrs['WEIGHTS_0'], '<4f'), accessor(attrs['WEIGHTS_1'], '<4f'))]
            for js, ws in zip(joints, weights):
                actual = dict(zip((names[j] for j in js), ws))
                index = round(actual['Tiny0'] / 1e-8) - 1
                assert 0 <= index < len(expected)
                total = sum(weight for _, weight in expected[index])
                for name, weight in expected[index]:
                    assert actual[name] == pytest.approx(weight / total, rel=1e-6, abs=1e-12)
                covered.add(index)
        assert covered == set(range(len(expected)))
        assert inspect_skin_lod_source(source).weights == expected
        assert tuple(source.data.attributes.keys()) == attributes
    finally:
        source.data.materials.clear()
        for material in materials:
            bpy.data.materials.remove(material)
