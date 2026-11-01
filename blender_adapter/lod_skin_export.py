# SPDX-License-Identifier: GPL-3.0-or-later
"""Temporary independent hierarchy for a validated skinned LOD export scope."""
from contextlib import contextmanager
import bpy
from .lod_skin import inspect_skin_lod_source


@contextmanager
def stage_skin_lod_level(level, scene, *, generated_clips=False):
    """Copy skin and current pose without copying animation dependencies.

    With generated_clips enabled, stable owned generated actions are associated
    with the copy for the shared exporter. Artist actions/NLA remain blocked.
    The original hierarchy is never altered.
    """
    if not level.armatures or not level.meshes:
        raise ValueError('Choose a skinned LOD export level')
    for rig in level.armatures:
        if (rig.constraints or rig.data.animation_data or
                (rig.animation_data and rig.animation_data.drivers) or
                any(bone.constraints for bone in rig.pose.bones)):
            raise ValueError('LOD export staging requires rigs without external dependencies')
    if any(rig.parent for rig in level.armatures) and len(level.armatures) != 1:
        raise ValueError('Parented LOD export requires exactly one rig')
    for rig in level.armatures:
        child = rig
        while child.parent:
            parent = child.parent
            if (child.parent_type != 'OBJECT' or parent.type != 'EMPTY' or
                    parent.animation_data or parent.constraints):
                raise ValueError('LOD export requires static empty object parents')
            child = parent
    for mesh in level.meshes:
        if inspect_skin_lod_source(mesh).armature not in level.armatures:
            raise ValueError('Skin binding lies outside the export level')
    if generated_clips:
        from types import SimpleNamespace
        from .animation import generated_actions, action_curves, _RIG_ID
        if len(level.armatures) != 1:
            raise ValueError('Generated clip export requires exactly one rig')
        rig = level.armatures[0]
        actions = generated_actions(SimpleNamespace(children=(rig,)))
        data = rig.animation_data
        if not rig.get(_RIG_ID) or not actions:
            raise ValueError('Generated clip export requires stable rig ownership and generated clips')
        for action in actions:
            slots = tuple(action.slots) if hasattr(action, 'slots') else (None,)
            if any(not curve.data_path.startswith('pose.bones[')
                   for slot in slots for curve in action_curves(action, slot)):
                raise ValueError('Skinned LOD clips require bone channels; object motion needs playback preparation')
        for action in actions:
            slots = tuple(action.slots) if hasattr(action, 'slots') else (None,)
            for slot in slots:
                for curve in action_curves(action, slot):
                    if (any(key.interpolation not in ('LINEAR', 'CONSTANT')
                            for key in curve.keyframe_points) or
                            any(mod.type != 'CYCLES' for mod in curve.modifiers)):
                        raise ValueError('Skinned LOD clips require linear or constant keys without unsupported modifiers')
        if data and (data.nla_tracks or (data.action and data.action not in actions)):
            raise ValueError('Artist actions and NLA require explicit manual export preparation')
    objects, meshes, armatures = [], [], []
    try:
        root = bpy.data.objects.new('LOD%d' % level.index, None)
        objects.append(root)
        scene.collection.objects.link(root)
        if len(level.armatures) == 1 and level.armatures[0].parent:
            rig = level.armatures[0]
            root.matrix_world = rig.parent.matrix_world @ rig.matrix_parent_inverse
        copies = {}
        for rig in level.armatures:
            copy = rig.copy()
            objects.append(copy)
            copy.data = rig.data.copy()
            armatures.append(copy.data)
            copy.animation_data_clear()
            for key in list(copy.keys()):
                del copy[key]
            if generated_clips:
                copy[_RIG_ID] = rig[_RIG_ID]
                animation = copy.animation_data_create()
                animation.action = actions[0]
                if hasattr(actions[0], 'slots') and len(actions[0].slots):
                    animation.action_slot = actions[0].slots[0]
            scene.collection.objects.link(copy)
            copy.parent = root
            copy.matrix_parent_inverse.identity()
            if rig.parent:
                # Preserve the local space used by authored object animation.
                copy.matrix_basis = rig.matrix_basis.copy()
            else:
                copy.matrix_world = rig.matrix_world.copy()
            copies[rig] = copy
        for source in level.meshes:
            copy = source.copy()
            objects.append(copy)
            copy.data = source.data.copy()
            meshes.append(copy.data)
            for key in list(copy.keys()):
                del copy[key]
            scene.collection.objects.link(copy)
            copy.parent = root
            copy.matrix_world = source.matrix_world.copy()
            copy.modifiers[0].object = copies[source.modifiers[0].object]
        bpy.context.view_layer.update()
        yield root
    finally:
        for obj in reversed(objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for rig in armatures:
            if rig.users == 0:
                bpy.data.armatures.remove(rig)


def export_skin_lod_level(level, context, filepath):
    """Export one generated-clip skin scope through the normal Godot adapter.

    Caller owns bundle staging/publication. No automatic LOD switching is implied.
    """
    from .targets import get_adapter
    with stage_skin_lod_level(level, context.scene, generated_clips=True) as root:
        return get_adapter('GODOT', asset_use='ANIMATED').export(root, context, filepath)
