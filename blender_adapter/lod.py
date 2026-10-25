# SPDX-License-Identifier: GPL-3.0-or-later
"""Static LOD preview backend; source geometry is never replaced."""
from dataclasses import dataclass
from hashlib import sha256
import bpy
from object_core.lod import plan_lods


def _signature(obj):
    mesh = obj.data
    payload = (
        tuple(tuple(row) for row in obj.matrix_world),
        tuple(tuple(v.co) for v in mesh.vertices),
        tuple(tuple(e.vertices) for e in mesh.edges),
        tuple((tuple(p.vertices), p.material_index, p.use_smooth) for p in mesh.polygons),
        tuple((layer.name, tuple(tuple(item.uv) for item in layer.data)) for layer in mesh.uv_layers),
        tuple(material.as_pointer() if material else None for material in mesh.materials),
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

    def cancel(self):
        if self.state != 'PREVIEW':
            raise ValueError("Only an active preview can be cancelled")
        for obj in self.objects:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(self.collection)
        self.state = 'CANCELLED'

    def apply(self):
        if self.state != 'PREVIEW':
            raise ValueError("Only an active preview can be applied")
        _validate_source(self.source)
        if _signature(self.source) != self.source_signature:
            raise ValueError("Source changed; cancel and build a new LOD preview")
        for obj in self.objects:
            _validate_source(obj)
        if tuple(_signature(obj) for obj in self.objects) != self.preview_signatures:
            raise ValueError("Preview changed; preserve the edits separately and rebuild before applying")
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
            if len(reduced.uv_layers) != len(source.data.uv_layers) or tuple(reduced.materials) != tuple(source.data.materials):
                raise ValueError("LOD reduction did not preserve UV layers and material slots")
            obj['asset_assistant_lod_level'] = level.index
            obj['asset_assistant_lod_triangles'] = _triangles(reduced)
        return StaticLODPreview(source, signature, collection, tuple(objects), levels,
                                tuple(_signature(obj) for obj in objects))
    except Exception:
        for obj in objects:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(collection)
        raise
