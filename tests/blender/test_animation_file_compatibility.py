# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
bpy = pytest.importorskip('bpy')
from blender_adapter.animation_file_compatibility import validate_clip_compatibility


@pytest.fixture
def clip_pair():
    before = {kind: set(getattr(bpy.data, kind)) for kind in ('objects', 'armatures', 'actions')}
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
    for kind, original in before.items():
        for item in set(getattr(bpy.data, kind)) - original:
            getattr(bpy.data, kind).remove(item, do_unlink=True)


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
def test_real_file_inspection_preserves_scene_and_cleans_failure(clip_pair, tmp_path, extension):
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
    target.data.bones[0].name = 'Incompatible'
    with pytest.raises(ValueError, match='retargeting'):
        inspect_animation_file(path, target, bpy.context)
    assert all(set(getattr(bpy.data, kind)) == ids for kind, ids in before.items())
