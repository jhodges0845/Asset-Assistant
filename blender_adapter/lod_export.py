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


def export_static_lod_bundle(collection, context, directory):
    """Write separate validated GLBs and a manifest into a new directory.

    This exchange bundle does not configure automatic engine LOD switching.
    """
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from .targets import get_adapter
    levels = plan_lod_export(collection, context.scene)
    if any(level.armatures for level in levels):
        raise ValueError('Skinned LOD bundle export is not implemented')
    destination = Path(directory).resolve()
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('Choose a new bundle directory inside an existing directory')
    selected = tuple(context.selected_objects)
    active = context.view_layer.objects.active
    manifest = {'version': 1, 'format': 'GLB', 'engine_lod_configured': False, 'levels': []}
    with TemporaryDirectory(prefix='asset-assistant-lod-', dir=destination.parent) as staging:
        for level in levels:
            objects, meshes = [], []
            try:
                root = bpy.data.objects.new('LOD' + str(level.index), None)
                objects.append(root)
                context.scene.collection.objects.link(root)
                for source in level.meshes:
                    mesh = source.data.copy()
                    meshes.append(mesh)
                    obj = bpy.data.objects.new(source.name + ' Export', mesh)
                    objects.append(obj)
                    context.scene.collection.objects.link(obj)
                    obj.parent = root
                    obj.matrix_world = source.matrix_world.copy()
                    for index, slot in enumerate(source.material_slots):
                        mesh.materials[index] = slot.material
                filename = 'LOD%d.glb' % level.index
                result = get_adapter('GODOT', asset_use='STATIC').export(root, context, Path(staging) / filename)
                if not result.success:
                    raise ValueError('LOD export failed: ' + '; '.join(issue.message for issue in result.issues if issue.status in ('ERROR', 'WARN')))
                manifest['levels'].append({'index': level.index, 'file': filename,
                                           'triangles': level.triangle_count, 'mesh_count': len(level.meshes)})
            finally:
                for obj in reversed(objects):
                    bpy.data.objects.remove(obj, do_unlink=True)
                for mesh in meshes:
                    if mesh.users == 0:
                        bpy.data.meshes.remove(mesh)
                for obj in context.selected_objects:
                    obj.select_set(False)
                for obj in selected:
                    obj.select_set(True)
                context.view_layer.objects.active = active
        (Path(staging) / 'lod-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        destination.mkdir()  # Fails if another writer created the path meanwhile.
        created = []
        try:
            for source_path in Path(staging).iterdir():
                target = destination / source_path.name
                with target.open('xb') as stream:
                    created.append(target)
                    stream.write(source_path.read_bytes())
        except Exception:
            for path in created:
                path.unlink()
            if not any(destination.iterdir()):
                destination.rmdir()
            raise
    return manifest
