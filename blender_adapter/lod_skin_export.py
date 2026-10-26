# SPDX-License-Identifier: GPL-3.0-or-later
"""Temporary independent hierarchy for a validated skinned LOD export scope."""
from contextlib import contextmanager
import bpy
from .lod_skin import inspect_skin_lod_source


@contextmanager
def stage_skin_lod_level(level, scene):
    """Copy skin and current pose without copying animation dependencies.

    Animation serialization must supply its own explicit policy. This staging
    helper does not export clips or alter the original hierarchy.
    """
    if not level.armatures or not level.meshes:
        raise ValueError('Choose a skinned LOD export level')
    for rig in level.armatures:
        if (rig.constraints or rig.parent or rig.data.animation_data or
                (rig.animation_data and rig.animation_data.drivers) or
                any(bone.constraints for bone in rig.pose.bones)):
            raise ValueError('LOD export staging requires rigs without external dependencies')
    for mesh in level.meshes:
        if inspect_skin_lod_source(mesh).armature not in level.armatures:
            raise ValueError('Skin binding lies outside the export level')
    objects, meshes, armatures = [], [], []
    try:
        root = bpy.data.objects.new('LOD%d' % level.index, None)
        objects.append(root)
        scene.collection.objects.link(root)
        copies = {}
        for rig in level.armatures:
            copy = rig.copy()
            objects.append(copy)
            copy.data = rig.data.copy()
            armatures.append(copy.data)
            copy.animation_data_clear()
            for key in list(copy.keys()):
                del copy[key]
            scene.collection.objects.link(copy)
            copy.parent = root
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
