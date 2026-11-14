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
