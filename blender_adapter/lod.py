# SPDX-License-Identifier: GPL-3.0-or-later
"""Static LOD preview backend; source geometry is never replaced."""
from dataclasses import dataclass, asdict
import json
from hashlib import sha256
import bpy
from .core_gateway import plan_lods, LODLevel


def _signature(obj):
    mesh = obj.data
    payload = (
        tuple(tuple(row) for row in obj.matrix_world),
        tuple(tuple(v.co) for v in mesh.vertices),
        tuple(tuple(e.vertices) for e in mesh.edges),
        tuple((tuple(p.vertices), p.material_index, p.use_smooth) for p in mesh.polygons),
        tuple((layer.name, tuple(tuple(item.uv) for item in layer.data)) for layer in mesh.uv_layers),
        tuple((material.name_full, material.library.filepath if material.library else None) if material else None for material in (slot.material for slot in obj.material_slots)),
    )
    return sha256(repr(payload).encode()).hexdigest()


def _validate_source(obj):
    if obj is None or obj.type != 'MESH':
        raise ValueError("Choose one static mesh for LOD preview")
    if obj.mode != 'OBJECT':
        raise ValueError("Return to Object Mode before building or applying LODs")
    if obj.modifiers or obj.constraints or obj.animation_data or obj.data.animation_data or obj.data.shape_keys or obj.vertex_groups:
        raise ValueError("This LOD preview supports static meshes without modifiers, constraints, animation, shape keys or skin groups")
    parent = obj.parent
    while parent:
        if parent.type == 'ARMATURE' or parent.animation_data or parent.constraints:
            raise ValueError("Animated or constrained asset hierarchies are not supported for LOD preview")
        parent = parent.parent
    from .validation import inspect_objects
    if inspect_objects([obj], require_manifold_geometry=False).invalid_meshes:
        raise ValueError("Resolve invalid source geometry before LOD preview")


def _triangles(mesh):
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


@dataclass
class StaticLODPreview:
    source: object
    source_signature: str
    collection: object
    objects: tuple
    levels: tuple
    preview_signatures: tuple
    state: str = 'PREVIEW'

    def _check_structure(self):
        try:
            if self.collection.get('asset_assistant_lod_state') != 'PREVIEW':
                raise ValueError("Only an active preview can be changed")
            if set(self.collection.objects) != set(self.objects) or self.collection.children:
                raise ValueError("Preview collection changed; preserve its contents before rebuilding")
            for index, obj in enumerate(self.objects):
                if obj.mode != 'OBJECT':
                    raise ValueError("Return to Object Mode before changing a LOD preview")
                if obj.data != self.collection.get('lod_mesh_' + str(index)) or tuple(obj.users_collection) != (self.collection,):
                    raise ValueError("Preview ownership changed; preserve the edits before rebuilding")
        except ReferenceError as exc:
            raise ValueError("Preview data was removed; preserve remaining objects before rebuilding") from exc

    def cancel(self):
        if self.state != 'PREVIEW':
            raise ValueError("Only an active preview can be cancelled")
        self._check_structure()
        bpy.data.collections.remove(self.collection)
        for obj in self.objects:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        self.state = 'CANCELLED'

    def validate_apply(self):
        if self.state != 'PREVIEW':
            raise ValueError("Only an active preview can be applied")
        self._check_structure()
        _validate_source(self.source)
        if _signature(self.source) != self.source_signature:
            raise ValueError("Source changed; cancel and build a new LOD preview")
        for obj in self.objects:
            _validate_source(obj)
        if tuple(_signature(obj) for obj in self.objects) != self.preview_signatures:
            raise ValueError("Preview changed; preserve the edits separately and rebuild before applying")

    def apply(self):
        self.validate_apply()
        self.collection.name = self.source.name + ' LODs'
        self.collection['asset_assistant_lod_state'] = 'APPLIED'
        self.state = 'APPLIED'
        return self.objects


def preview_static_lods(source, scene, ratios=(.5, .25)):
    if scene != bpy.context.scene:
        raise ValueError("LOD preview requires the active scene")
    _validate_source(source)
    signature = _signature(source)
    levels = plan_lods(_triangles(source.data), ratios)
    collection = bpy.data.collections.new(source.name + ' LOD Preview')
    collection['asset_assistant_lod_state'] = 'PREVIEW'
    scene.collection.children.link(collection)
    objects = []
    try:
        for level in levels:
            mesh = source.data.copy()
            obj = bpy.data.objects.new(source.name + '_LOD' + str(level.index), mesh)
            objects.append(obj)
            collection.objects.link(obj)
            obj.matrix_world = source.matrix_world.copy()
            # Bake effective object overrides into the independent LOD mesh only.
            for index, slot in enumerate(source.material_slots):
                mesh.materials[index] = slot.material
            modifier = obj.modifiers.new('LOD reduction', 'DECIMATE')
            modifier.ratio = level.triangle_budget / _triangles(source.data)
            modifier.use_collapse_triangulate = True
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            reduced = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),
                preserve_all_data_layers=True, depsgraph=depsgraph)
            obj.modifiers.clear()
            obj.data = reduced
            bpy.data.meshes.remove(mesh)
            from .validation import inspect_objects
            if inspect_objects([obj], require_manifold_geometry=False).invalid_meshes:
                raise ValueError("LOD reduction produced invalid geometry")
            if _triangles(reduced) > level.triangle_budget:
                raise ValueError("LOD reduction could not meet the requested triangle budget")
            if len(reduced.uv_layers) != len(source.data.uv_layers) or tuple(reduced.materials) != tuple(slot.material for slot in source.material_slots):
                raise ValueError("LOD reduction did not preserve UV layers and material slots")
            obj['asset_assistant_lod_level'] = level.index
            obj['asset_assistant_lod_triangles'] = _triangles(reduced)
        signatures = tuple(_signature(obj) for obj in objects)
        collection['lod_source'] = source
        for index, obj in enumerate(objects):
            collection['lod_object_' + str(index)] = obj
            collection['lod_mesh_' + str(index)] = obj.data
        collection['lod_manifest'] = json.dumps({
            'version': 1, 'source_signature': signature,
            'levels': [asdict(level) for level in levels],
            'preview_signatures': signatures,
        })
        return StaticLODPreview(source, signature, collection, tuple(objects), levels, signatures)
    except Exception:
        bpy.data.collections.remove(collection)
        for obj in objects:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        raise


def recover_static_lod_preview(collection):
    """Recover a saved preview through Blender ID references, never object names."""
    if collection.get('asset_assistant_lod_state') != 'PREVIEW':
        raise ValueError("Choose an active LOD preview collection")
    try:
        manifest = json.loads(collection['lod_manifest'])
        if manifest['version'] != 1:
            raise ValueError("Unsupported LOD preview version")
        levels = tuple(LODLevel(**item) for item in manifest['levels'])
        if not 1 <= len(levels) <= 4:
            raise ValueError("Invalid LOD preview level count")
        source = collection['lod_source']
        if not isinstance(source, bpy.types.Object):
            raise ValueError("LOD preview source is missing")
        objects = tuple(collection['lod_object_' + str(index)] for index in range(len(levels)))
        if any(not isinstance(obj, bpy.types.Object) for obj in objects) or source in objects:
            raise ValueError("LOD preview objects are missing or invalid")
        signatures = tuple(manifest['preview_signatures'])
        if len(signatures) != len(objects):
            raise ValueError("Invalid LOD preview signatures")
        preview = StaticLODPreview(source, manifest['source_signature'], collection,
                                   objects, levels, signatures)
        preview._check_structure()
        return preview
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError("LOD preview metadata is missing or damaged; preserve its objects") from exc
