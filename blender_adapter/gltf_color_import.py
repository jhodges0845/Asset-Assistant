# SPDX-License-Identifier: GPL-3.0-or-later
"""Preserve glTF colors through Blender's native vertex mapping in scoped imports."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import copy
from uuid import uuid4
import sys
import bpy

_scope = ContextVar('asset_assistant_import_colors', default=None)


def extension_available():
    module = sys.modules.get(__package__)
    return (__package__ in bpy.context.preferences.addons and
            callable(getattr(module, 'glTF2ImportUserExtension', None)))


@contextmanager
def preserve_import_colors():
    if not extension_available() or _scope.get() is not None:
        raise ValueError('Color-preserving import extension unavailable or already active')
    state = {'started': False, 'pending': {}}
    token = _scope.set(state)
    try:
        yield
        if not state['started'] or state['pending']:
            raise ValueError('Color-preserving import hooks did not complete')
    finally:
        _scope.reset(token)


class ColorImportExtension:
    is_critical = True

    def __init__(self):
        self.state = _scope.get()
        self.synthetic = {}
        if self.state is not None:
            self.state['started'] = True

    def decode_accessor_before_hook(self, accessor, array, gltf):
        if self.state is not None and id(accessor) in self.synthetic:
            array.value = self.synthetic[id(accessor)]

    def gather_import_mesh_before_hook(self, pymesh, gltf):
        if self.state is None:
            return
        import numpy as np
        from io_scene_gltf2.io.imp.gltf2_io_binary import BinaryData
        colors = sorted({key for prim in pymesh.primitives for key in prim.attributes
                         if key.startswith('COLOR_')})
        if not colors:
            return
        if colors != ['COLOR_' + str(i) for i in range(len(colors))] or len(colors) > 8:
            raise ValueError('Unsupported color set numbering')
        if any('KHR_draco_mesh_compression' in (p.extensions or {}) for p in pymesh.primitives):
            raise ValueError('Decode compressed colored meshes before precision-preserving import')
        marker = '_AA_COLOR_' + uuid4().hex + '_'
        aliases = []
        for color in colors:
            alias = marker + color
            if any(alias in p.attributes for p in pymesh.primitives):
                raise ValueError('Import color attribute collision')
            template = next(gltf.data.accessors[p.attributes[color]] for p in pymesh.primitives
                            if color in p.attributes)
            for prim in pymesh.primitives:
                count = gltf.data.accessors[prim.attributes['POSITION']].count
                values = np.ones((count, 4), dtype=np.float32)
                if color in prim.attributes:
                    decoded = BinaryData.decode_accessor(gltf, prim.attributes[color])
                    if decoded.shape not in ((count, 3), (count, 4)) or not np.isfinite(decoded).all():
                        raise ValueError('Invalid imported color values')
                    values[:, :decoded.shape[1]] = decoded
                accessor = copy(template)
                accessor.count, accessor.type, accessor.component_type = count, 'VEC4', 5126
                accessor.buffer_view = accessor.byte_offset = accessor.sparse = None
                accessor.min = accessor.max = None
                accessor.normalized = False
                self.synthetic[id(accessor)] = values
                prim.attributes[alias] = len(gltf.data.accessors)
                gltf.data.accessors.append(accessor)
            aliases.append((alias, int(color[6:])))
        self.state['pending'][id(pymesh)] = aliases

    def gather_import_mesh_after_hook(self, pymesh, mesh, gltf):
        if self.state is None:
            return
        aliases = self.state['pending'].get(id(pymesh), ())
        for alias, index in aliases:
            attribute = mesh.attributes.get(alias)
            name = 'Color' if index == 0 else 'Color.%03d' % index
            old = mesh.color_attributes.get(name)
            if attribute is None or old is None or attribute.data_type != 'FLOAT_COLOR':
                raise ValueError('Imported color mapping unavailable')
            values = [tuple(item.color) for item in attribute.data]
            domain = old.domain
            mesh.color_attributes.remove(old)
            layer = mesh.color_attributes.new(name=name, type='FLOAT_COLOR', domain=domain)
            if layer.name != name:
                raise ValueError('Imported color layer name collision')
            for i, item in enumerate(layer.data):
                vertex = mesh.loops[i].vertex_index if domain == 'CORNER' else i
                item.color = values[vertex]
            mesh.attributes.remove(attribute)
            for prim in pymesh.primitives:
                del prim.attributes[alias]
        if aliases:
            mesh.color_attributes.render_color_index = 0
            del self.state['pending'][id(pymesh)]
