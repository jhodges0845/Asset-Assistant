# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped glTF extension preserving validated LOD weights below Blender's cutoff."""
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4
import sys
import bpy
from .lod_skin import inspect_skin_lod_source

_scope = ContextVar('asset_assistant_lod_weights', default=None)


def extension_available():
    package = __package__
    module = sys.modules.get(package)
    return (package in bpy.context.preferences.addons and
            callable(getattr(module, 'glTF2ExportUserExtension', None)))


@contextmanager
def preserve_weights(root, options):
    """Only staged copies receive provenance; missing hooks abort publication."""
    contracts = {obj: inspect_skin_lod_source(obj) for obj in root.children
                 if obj.type == 'MESH'}
    if not any(0 < weight <= .0001 for contract in contracts.values()
               for row in contract.weights for _, weight in row):
        yield options
        return
    if not extension_available() or _scope.get() is not None:
        raise ValueError('Weight-preserving LOD export extension is unavailable or already active')
    marker = '_aa_lod_' + uuid4().hex
    state = {'marker': marker, 'contracts': contracts, 'seen': set(),
             'custom_attributes': options.get('export_attributes', False)}
    attributes = []
    token = _scope.set(state)
    try:
        for obj in contracts:
            if len(obj.data.vertices) > 2 ** 24:
                raise ValueError('LOD provenance exceeds exact float vertex indexing')
            attr = obj.data.attributes.new(marker, 'FLOAT', 'POINT')
            attributes.append((obj.data, attr))
            if attr.name != marker:
                raise ValueError('LOD provenance attribute collision')
            attr.data.foreach_set('value', range(len(obj.data.vertices)))
        scoped = dict(options, export_attributes=True, gltf_export_id=marker)
        yield scoped
        if state['seen'] != set(contracts):
            raise ValueError('Weight-preserving LOD export hook did not process every mesh')
    finally:
        _scope.reset(token)
        for data, attr in attributes:
            data.attributes.remove(attr)


class WeightExportExtension:
    is_critical = True

    def gather_attribute_keep(self, attribute, settings):
        state = _scope.get()
        if (state is not None and settings.get('gltf_export_id') == state['marker']
                and not state['custom_attributes']):
            attribute.keep = attribute.attr_name == state['marker']

    def gather_mesh_hook(self, mesh, data, obj, groups, modifiers, materials, settings):
        state = _scope.get()
        if state is None or settings.get('gltf_export_id') != state['marker']:
            return
        if obj not in state['contracts']:
            raise ValueError('Unexpected mesh in weight-preserving LOD export')
        import numpy as np
        from io_scene_gltf2.blender.exp.accessors import array_to_accessor
        from io_scene_gltf2.blender.exp.skins import gather_skin
        contract = state['contracts'][obj]
        node = next(node for node in settings['vtree'].nodes.values()
                    if node.blender_object == obj)
        skin = gather_skin(node.armature, settings)
        joints = {joint.name: index for index, joint in enumerate(skin.joints)}
        if len(joints) != len(skin.joints) or len(joints) > 65536:
            raise ValueError('Ambiguous or oversized LOD joint mapping')
        rows = contract.weights
        bones = np.zeros((len(rows), 8), dtype=np.uint16)
        weights = np.zeros((len(rows), 8), dtype=np.float32)
        for index, row in enumerate(rows):
            total = sum(weight for _, weight in row)
            if not row or len(row) > 8 or not np.isfinite(total) or total <= 0:
                raise ValueError('Invalid LOD skin weight row')
            for slot, (name, weight) in enumerate(row):
                bones[index, slot] = joints[name]
                weights[index, slot] = weight / total
                if not np.isfinite(weights[index, slot]) or weights[index, slot] <= 0:
                    raise ValueError('LOD skin weight cannot be represented in glTF')
        chunks = 2 if any(len(row) > 4 for row in rows) else 1
        covered = set()
        for primitive in mesh.primitives:
            ids = primitive.attributes.pop(state['marker'].upper())
            if (ids.component_type != 5126 or ids.type != 'SCALAR' or
                    ids.byte_offset not in (None, 0) or ids.sparse is not None):
                raise ValueError('Unsupported LOD provenance accessor')
            values = np.frombuffer(ids.buffer_view.data, dtype='<f4')
            if (len(values) != ids.count or not np.all(np.isfinite(values)) or
                    not np.all(values == np.floor(values)) or
                    np.any(values < 0) or np.any(values >= len(rows))):
                raise ValueError('Invalid LOD vertex provenance')
            indices = values.astype(np.int64)
            if primitive.attributes['POSITION'].count != len(indices):
                raise ValueError('LOD provenance count differs from geometry')
            covered.update(indices.tolist())
            for key in list(primitive.attributes):
                if key.startswith(('JOINTS_', 'WEIGHTS_')):
                    del primitive.attributes[key]
            for chunk in range(chunks):
                columns = slice(chunk * 4, (chunk + 1) * 4)
                primitive.attributes['JOINTS_' + str(chunk)] = array_to_accessor(
                    'JOINTS', bones[indices, columns].copy(), settings, 5123, 'VEC4')
                primitive.attributes['WEIGHTS_' + str(chunk)] = array_to_accessor(
                    'WEIGHTS', weights[indices, columns].copy(), settings, 5126, 'VEC4')
        used = {vertex for polygon in data.polygons for vertex in polygon.vertices}
        if covered != used:
            raise ValueError('LOD provenance does not cover the exported surface')
        state['seen'].add(obj)
