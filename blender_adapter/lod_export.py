# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit read-only level boundaries for future destination export."""
from dataclasses import dataclass
import json
import bpy
from .lod import _signature, _validate_source, _triangles


@dataclass(frozen=True)
class LODExportLevel:
    index: int
    meshes: tuple
    armatures: tuple
    triangle_count: int


def _member_levels(collection, scene):
    if collection.get('asset_assistant_lod_state') != 'APPLIED':
        raise ValueError('Apply every LOD preview before planning export')
    try:
        manifest = json.loads(collection['lod_manifest'])
        if manifest['version'] != 1:
            raise ValueError('Unsupported LOD manifest version')
        levels = manifest['levels']
        if not 1 <= len(levels) <= 4:
            raise ValueError('Invalid LOD level count')
        source = collection['lod_source']
        objects = tuple(collection['lod_object_' + str(i)] for i in range(len(levels)))
        if set(collection.objects) != set(objects) or collection.children or source in objects:
            raise ValueError('LOD export collection membership changed')
        skin = bool(collection.get('lod_skin_preview'))
        if skin:
            from .lod_skin_preview import _skin_signature
            from .lod_skin import inspect_skin_lod_source
            signature = _skin_signature
            rig = collection['lod_skin_rig']
            rigs = (rig,)
        else:
            signature = _signature
            rigs = ()
        for obj in (source,) + objects + rigs:
            if not isinstance(obj, bpy.types.Object) or scene.objects.get(obj.name) != obj:
                raise ValueError('LOD export members must exist in the active scene')
        for index, obj in enumerate(objects):
            if obj.data != collection.get('lod_mesh_' + str(index)):
                raise ValueError('LOD export mesh ownership changed')
        for obj in (source,) + objects:
            if skin:
                if inspect_skin_lod_source(obj).armature != rig:
                    raise ValueError('LOD export skin binding changed')
            else:
                _validate_source(obj)
        if signature(source) != manifest['source_signature'] or tuple(signature(obj) for obj in objects) != tuple(manifest['preview_signatures']):
            raise ValueError('Applied LOD data changed; review and rebuild before export')
        result = [LODExportLevel(0, (source,), rigs, _triangles(source.data))]
        for index, (obj, level) in enumerate(zip(objects, levels), 1):
            count = _triangles(obj.data)
            if level['index'] != index or count > level['triangle_budget']:
                raise ValueError('LOD level ordering or triangle budget changed')
            result.append(LODExportLevel(index, (obj,), rigs, count))
        return tuple(result)
    except (KeyError, TypeError, AttributeError, ReferenceError, json.JSONDecodeError) as exc:
        raise ValueError('LOD export metadata is missing or invalid') from exc


def plan_lod_export(collection, scene):
    """Return explicit LOD0/source and reduced scopes; never reparent or write.

    Changed applied meshes conservatively require a rebuilt/reviewed set. Engine
    names, thresholds and serialized LOD configuration are not implied here.
    """
    if scene != bpy.context.scene or collection not in scene.collection.children_recursive:
        raise ValueError('Choose an LOD collection in the active scene')
    if 'lod_set_state' not in collection:
        return _member_levels(collection, scene)
    if collection.get('lod_set_state') != 'APPLIED' or collection.get('lod_set_version') != 1:
        raise ValueError('Apply a supported LOD group before planning export')
    count = collection.get('lod_set_count')
    if not isinstance(count, int) or count < 1 or collection.objects or collection.children:
        raise ValueError('Invalid LOD group record')
    members = tuple(collection.get('member_' + str(i)) for i in range(count))
    if len(set(members)) != count or any(member not in scene.collection.children_recursive for member in members):
        raise ValueError('LOD group members are missing or duplicated')
    plans = [_member_levels(member, scene) for member in members]
    if len({len(plan) for plan in plans}) != 1:
        raise ValueError('LOD group members have incompatible level counts')
    result = []
    for index in range(len(plans[0])):
        meshes = tuple(obj for plan in plans for obj in plan[index].meshes)
        if len(set(meshes)) != len(meshes):
            raise ValueError('LOD export scope contains duplicate meshes')
        rigs = tuple(dict.fromkeys(obj for plan in plans for obj in plan[index].armatures))
        result.append(LODExportLevel(index, meshes, rigs, sum(plan[index].triangle_count for plan in plans)))
    return tuple(result)
