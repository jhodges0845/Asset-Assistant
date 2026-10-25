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
