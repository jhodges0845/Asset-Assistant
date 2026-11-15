# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
bpy = pytest.importorskip('bpy')
from blender_adapter.animation_file_compatibility import validate_clip_compatibility


@pytest.fixture
def clip_pair():
    from blender_adapter.asset_file_import_ui import _IMPORT_DATA_KINDS
    before = {kind: set(getattr(bpy.data, kind)) for kind in _IMPORT_DATA_KINDS}
    bpy.ops.object.armature_add()
    source = bpy.context.object
    bone = source.pose.bones[0]
    bone.rotation_mode = 'XYZ'
    bone.rotation_euler.x = .2
    bone.keyframe_insert('rotation_euler', frame=1)
    bone.rotation_euler.x = .5
    bone.keyframe_insert('rotation_euler', frame=12)
    action, slot = source.animation_data.action, source.animation_data.action_slot
    target = source.copy()
    target.data = source.data.copy()
    target.animation_data_clear()
    bpy.context.collection.objects.link(target)
    yield source, target, action, slot
    created = [item for kind, original in before.items()
               for item in set(getattr(bpy.data, kind)) - original]
    if created:
        bpy.data.batch_remove(ids=created)


def test_matching_clip_is_read_only(clip_pair):
    source, target, action, slot = clip_pair
    assert len(validate_clip_compatibility(*clip_pair)) == 3
    assert source.animation_data.action == action
    assert target.animation_data is None


@pytest.mark.parametrize('change', ['rest', 'name', 'rotation', 'constraint', 'root_motion', 'modifier'])
def test_incompatible_clip_rejected(clip_pair, change):
    source, target, action, slot = clip_pair
    if change == 'rest':
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.mode_set(mode='EDIT')
        target.data.edit_bones[0].tail.x += .1
        bpy.ops.object.mode_set(mode='OBJECT')
    elif change == 'name':
        target.data.bones[0].name = 'Different'
    elif change == 'rotation':
        target.pose.bones[0].rotation_mode = 'QUATERNION'
    elif change == 'constraint':
        target.pose.bones[0].constraints.new('COPY_ROTATION')
    elif change == 'root_motion':
        source.keyframe_insert('location', frame=1)
    else:
        validate_clip_compatibility(*clip_pair)[0].modifiers.new('NOISE')
    with pytest.raises(ValueError):
        validate_clip_compatibility(*clip_pair)
    assert source.animation_data.action == action
    assert target.animation_data is None


@pytest.mark.parametrize('extension', ['.glb', '.fbx'])
def test_real_file_inspection_preserves_scene_and_cleans_failure(clip_pair, tmp_path, extension, monkeypatch):
    from blender_adapter.asset_file_import_ui import _import_external, _IMPORT_DATA_KINDS
    from blender_adapter.animation_file_compatibility import inspect_animation_file
    source, _, _, _ = clip_pair
    bpy.ops.object.select_all(action='DESELECT')
    source.select_set(True)
    bpy.context.view_layer.objects.active = source
    path = tmp_path / ('clip' + extension)
    if extension == '.glb':
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_animations=True)
    else:
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, add_leaf_bones=False,
                                 bake_anim=True, bake_anim_use_all_actions=False,
                                 bake_anim_use_nla_strips=False)
    original = set(bpy.data.objects)
    _import_external(str(path), extension, bpy.context)
    target = next(obj for obj in set(bpy.data.objects) - original if obj.type == 'ARMATURE')
    before = {kind: set(getattr(bpy.data, kind)) for kind in _IMPORT_DATA_KINDS}
    active = bpy.context.view_layer.objects.active
    selection = set(bpy.context.selected_objects)
    reports = inspect_animation_file(path, target, bpy.context)
    assert reports and reports[0]['channels'] > 0
    assert all(set(getattr(bpy.data, kind)) == ids for kind, ids in before.items())
    assert bpy.context.view_layer.objects.active == active
    assert set(bpy.context.selected_objects) == selection
    from hashlib import sha256
    from blender_adapter.animation_file_compatibility import transfer_animation_file
    from blender_adapter.animation_lifecycle import managed_actions
    from blender_adapter import animation_lifecycle
    root = bpy.data.objects.new('Transfer target', None)
    bpy.context.collection.objects.link(root)
    target.parent = root
    target['asset_assistant_rig_id'] = 'transfer-test-rig'
    from blender_adapter import animation_file_ui
    with monkeypatch.context() as patch:
        patch.setattr(animation_file_ui, '_root', lambda context: root)
        animation_file_ui.register()
        try:
            original_actions = set(bpy.data.actions)
            assert bpy.ops.asset_assistant.inspect_clip_file(filepath=str(path)) == {'FINISHED'}
            assert set(bpy.data.actions) == original_actions
            assert bpy.ops.asset_assistant.discard_clip_file() == {'FINISHED'}
            assert animation_file_ui._PENDING not in bpy.context.scene
            assert bpy.ops.asset_assistant.inspect_clip_file(filepath=str(path)) == {'FINISHED'}
            with monkeypatch.context() as changed_target:
                changed_target.setattr(animation_file_ui, '_root', lambda context: None)
                with pytest.raises(RuntimeError, match='Target changed'):
                    bpy.ops.asset_assistant.apply_clip_file(clip_index=0, export_name='UI imported clip', fps=24)
            assert set(bpy.data.actions) == original_actions
            assert bpy.ops.asset_assistant.apply_clip_file(clip_index=0, export_name='UI imported clip', fps=24) == {'FINISHED'}
            assert animation_file_ui._PENDING not in bpy.context.scene
        finally:
            animation_file_ui.clear_preview(bpy.context.scene)
            animation_file_ui.unregister()
    original_action = target.animation_data.action
    original_tracks = tuple((track, tuple(strip.action for strip in track.strips))
                            for track in target.animation_data.nla_tracks)
    digest = sha256(path.read_bytes()).hexdigest()
    baseline = {kind: set(getattr(bpy.data, kind)) for kind in _IMPORT_DATA_KINDS}
    copied = transfer_animation_file(path, root, bpy.context, expected_sha256=digest,
                                     clips={0: 'Approved clip'})
    assert len(copied) == 1 and copied[0] in managed_actions(root)
    assert copied[0].use_fake_user
    assert target.animation_data.action == original_action
    assert tuple((track, tuple(strip.action for strip in track.strips))
                 for track in target.animation_data.nla_tracks) == original_tracks
    assert all(set(getattr(bpy.data, kind)) == ids for kind, ids in baseline.items() if kind != 'actions')
    assert set(bpy.data.actions) - baseline['actions'] == set(copied)
    baseline = {kind: set(getattr(bpy.data, kind)) for kind in _IMPORT_DATA_KINDS}
    with pytest.raises(ValueError, match='changed'):
        transfer_animation_file(path, root, bpy.context, expected_sha256='stale', clips={0: 'Other'})
    register = animation_lifecycle.register_animation_action
    def fail_after_registration(*args, **kwargs):
        register(*args, **kwargs)
        raise RuntimeError('Injected registration failure')
    with monkeypatch.context() as patch:
        patch.setattr(animation_lifecycle, 'register_animation_action', fail_after_registration)
        with pytest.raises(RuntimeError, match='Injected'):
            transfer_animation_file(path, root, bpy.context, expected_sha256=digest, clips={0: 'Other'})
    assert all(set(getattr(bpy.data, kind)) == ids for kind, ids in baseline.items())
    before = baseline
    target.data.bones[0].name = 'Incompatible'
    with pytest.raises(ValueError, match='retargeting'):
        inspect_animation_file(path, target, bpy.context)
    assert all(set(getattr(bpy.data, kind)) == ids for kind, ids in before.items())


def test_transfer_rejects_external_glb_animation_buffers(tmp_path):
    import json
    import struct
    from hashlib import sha256
    from blender_adapter.animation_file_compatibility import transfer_animation_file
    document = json.dumps({'buffers': [{'uri': 'external.bin', 'byteLength': 12}]}).encode()
    document += b' ' * (-len(document) % 4)
    payload = struct.pack('<4sIII4s', b'glTF', 2, 20 + len(document), len(document), b'JSON') + document
    path = tmp_path / 'external.glb'
    path.write_bytes(payload)
    with pytest.raises(ValueError, match='External animation buffers'):
        transfer_animation_file(path, None, bpy.context, expected_sha256=sha256(payload).hexdigest(), clips={0: 'Clip'})


@pytest.mark.parametrize('extension', ['.glb', '.fbx'])
def test_multiclip_file_selection_and_unsupported_fbx_rejection(clip_pair, tmp_path, extension):
    from hashlib import sha256
    from blender_adapter.animation import action_curves
    from blender_adapter.animation_file_compatibility import inspect_animation_file, transfer_animation_file
    from blender_adapter.asset_file_import_ui import _import_external
    from blender_adapter.animation_lifecycle import managed_actions
    source, _, first, slot = clip_pair
    first.name = 'Small motion'
    second = first.copy()
    second.name = 'Large motion'
    for curve in action_curves(second, second.slots[0]):
        for key in curve.keyframe_points:
            key.co.y *= 2
            key.handle_left.y *= 2
            key.handle_right.y *= 2
    source.animation_data.action = None
    for action in (first, second):
        track = source.animation_data.nla_tracks.new()
        track.name = action.name
        strip = track.strips.new(action.name, 1, action)
        strip.action_slot = action.slots[0]
    bpy.ops.object.select_all(action='DESELECT')
    source.select_set(True)
    bpy.context.view_layer.objects.active = source
    path = tmp_path / ('two_clips' + extension)
    if extension == '.glb':
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_animations=True, export_animation_mode='NLA_TRACKS')
    else:
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, add_leaf_bones=False,
                                 bake_anim=True, bake_anim_use_all_actions=False,
                                 bake_anim_use_nla_strips=True)
    original = set(bpy.data.objects)
    _import_external(str(path), extension, bpy.context)
    target = next(obj for obj in set(bpy.data.objects) - original if obj.type == 'ARMATURE')
    root = bpy.data.objects.new('Multiclip target', None)
    bpy.context.collection.objects.link(root)
    target.parent = root
    target['asset_assistant_rig_id'] = 'multiclip-test-rig'
    if extension == '.fbx':
        # NLA FBX export bakes object transforms as well as bone channels.
        # Unsupported object channels must fail without retaining imported data.
        from blender_adapter.asset_file_import_ui import _IMPORT_DATA_KINDS
        before = {kind: set(getattr(bpy.data, kind)) for kind in _IMPORT_DATA_KINDS}
        original_action = target.animation_data.action
        with pytest.raises(ValueError, match='Only supported bone transform channels'):
            inspect_animation_file(path, target, bpy.context)
        assert all(set(getattr(bpy.data, kind)) == ids for kind, ids in before.items())
        assert target.animation_data.action == original_action
        return
    reports = inspect_animation_file(path, target, bpy.context)
    assert len(reports) == 2
    index = next(i for i, report in enumerate(reports) if 'Large motion' in report['name'])
    original_action = target.animation_data.action
    original_tracks = tuple((track.name, tuple(strip.action for strip in track.strips))
                            for track in target.animation_data.nla_tracks)
    before = set(bpy.data.actions)
    copied = transfer_animation_file(path, root, bpy.context,
                                    expected_sha256=sha256(path.read_bytes()).hexdigest(),
                                    clips={index: 'Selected large motion'})
    assert set(bpy.data.actions) - before == set(copied)
    assert tuple(managed_actions(root)) == copied
    assert target.animation_data.action == original_action
    assert tuple((track.name, tuple(strip.action for strip in track.strips))
                 for track in target.animation_data.nla_tracks) == original_tracks
    # A late name collision must roll back the already-registered first copy.
    from blender_adapter.asset_file_import_ui import _IMPORT_DATA_KINDS
    baseline = {kind: set(getattr(bpy.data, kind)) for kind in _IMPORT_DATA_KINDS}
    other_index = 1 - index
    with pytest.raises(ValueError, match='unique'):
        transfer_animation_file(path, root, bpy.context,
                                expected_sha256=sha256(path.read_bytes()).hexdigest(),
                                clips={other_index: 'Must roll back', index: 'Selected large motion'})
    assert all(set(getattr(bpy.data, kind)) == ids for kind, ids in baseline.items())
    assert tuple(managed_actions(root)) == copied
    assert target.animation_data.action == original_action
    assert tuple((track.name, tuple(strip.action for strip in track.strips))
                 for track in target.animation_data.nla_tracks) == original_tracks
    # Evaluate the transferred clip in isolation, against the authored rotation.
    target.animation_data.action = copied[0]
    target.animation_data.action_slot = copied[0].slots[0]
    for track in target.animation_data.nla_tracks:
        track.mute = True
    bpy.context.scene.frame_set(round(copied[0].frame_range[1]))
    bpy.context.view_layer.update()
    assert target.pose.bones[0].matrix_basis.to_quaternion().angle == pytest.approx(1.0, abs=1e-4)
    # A separate Blender process verifies persistence without in-memory state.
    import subprocess
    from pathlib import Path
    saved = tmp_path / 'transferred.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(saved))
    check = tmp_path / 'check_transfer.py'
    check.write_text(
        'import bpy, sys\n'
        + 'sys.path.insert(0, ' + repr(str(Path(__file__).resolve().parents[2])) + ')\n'
        + 'from blender_adapter.animation_lifecycle import managed_actions\n'
        + "root = bpy.data.objects['Multiclip target']\n"
        + 'clips = tuple(managed_actions(root))\n'
        + "assert len(clips) == 1 and clips[0].name == 'Selected large motion'\n"
        + "rig = next(obj for obj in root.children if obj.type == 'ARMATURE')\n"
        + 'assert rig.animation_data.action == clips[0]\n'
        + 'bpy.context.scene.frame_set(round(clips[0].frame_range[1]))\n'
        + 'bpy.context.view_layer.update()\n'
        + 'assert abs(rig.pose.bones[0].matrix_basis.to_quaternion().angle - 1.0) < 1e-4\n'
        + "print('TRANSFER_REOPEN_OK')\n", encoding='utf-8')
    result = subprocess.run([bpy.app.binary_path, '-b', '--factory-startup', str(saved),
                             '--python-exit-code', '1', '--python', str(check)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'TRANSFER_REOPEN_OK' in result.stdout
