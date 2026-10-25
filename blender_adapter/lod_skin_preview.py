# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved explicit lifecycle for experimental skinned LOD previews."""
from dataclasses import asdict
from hashlib import sha256
import json
import bpy
from .core_gateway import plan_lods
from .lod import StaticLODPreview, _signature, _triangles, recover_static_lod_preview
from .lod_skin import inspect_skin_lod_source, build_reduced_skin_lod_candidates


def _skin_signature(obj):
    contract = inspect_skin_lod_source(obj)
    rig = contract.armature
    rest = tuple((bone.name, bone.parent.name if bone.parent else None,
                  tuple(tuple(row) for row in bone.matrix_local), bone.length, bone.use_deform)
                 for bone in rig.data.bones)
    payload = (_signature(obj), contract.weights, rest,
               tuple(tuple(row) for row in rig.matrix_world),
               obj.modifiers[0].use_deform_preserve_volume)
    return sha256(repr(payload).encode()).hexdigest()


class SkinLODPreview(StaticLODPreview):
    def validate_apply(self):
        if self.state != 'PREVIEW':
            raise ValueError('Only an active skin preview can be applied')
        self._check_structure()
        rig = self.collection.get('lod_skin_rig')
        for obj in (self.source,) + self.objects:
            if inspect_skin_lod_source(obj).armature != rig:
                raise ValueError('Skin binding changed; preserve edits and rebuild')
        if _skin_signature(self.source) != self.source_signature:
            raise ValueError('Skin source or rest rig changed; cancel and rebuild')
        if tuple(_skin_signature(obj) for obj in self.objects) != self.preview_signatures:
            raise ValueError('Skin preview changed; preserve edits before rebuilding')


def preview_skin_lods(source, scene, ratios=(.5, .25), *, max_distance):
    ratios = tuple(ratios)
    signature = _skin_signature(source)
    levels = plan_lods(_triangles(source.data), ratios)
    objects = build_reduced_skin_lod_candidates(source, scene, ratios, max_distance=max_distance)
    collection = None
    try:
        collection = bpy.data.collections.new(source.name + ' Skin LOD Preview')
        scene.collection.children.link(collection)
        collection['asset_assistant_lod_state'] = 'PREVIEW'
        collection['lod_skin_preview'] = True
        collection['lod_skin_rig'] = source.modifiers[0].object
        collection['lod_source'] = source
        for index, obj in enumerate(objects):
            collection.objects.link(obj)
            scene.collection.objects.unlink(obj)
            collection['lod_object_' + str(index)] = obj
            collection['lod_mesh_' + str(index)] = obj.data
        signatures = tuple(_skin_signature(obj) for obj in objects)
        collection['lod_manifest'] = json.dumps({
            'version': 1, 'source_signature': signature,
            'levels': [asdict(level) for level in levels], 'preview_signatures': signatures})
        return SkinLODPreview(source, signature, collection, objects, levels, signatures)
    except Exception:
        if collection is not None:
            bpy.data.collections.remove(collection)
        for obj in objects:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        raise


def recover_skin_lod_preview(collection):
    if not collection.get('lod_skin_preview'):
        raise ValueError('Choose a skinned LOD preview')
    saved = recover_static_lod_preview(collection)
    return SkinLODPreview(saved.source, saved.source_signature, saved.collection,
                          saved.objects, saved.levels, saved.preview_signatures)
