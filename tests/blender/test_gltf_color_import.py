# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
import pytest
from blender_adapter import gltf_color_import as colors
from blender_adapter.asset_file_import_ui import _IMPORT_DATA_KINDS, _import_external


@pytest.fixture
def painted_file(tmp_path):
    before = {k: set(getattr(bpy.data, k)) for k in _IMPORT_DATA_KINDS}
    enabled = 'blender_adapter' in bpy.context.preferences.addons
    if not enabled:
        bpy.context.preferences.addons.new().module = 'blender_adapter'
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8)
    source = bpy.context.object
    layer = source.data.color_attributes.new(name='Paint', type='FLOAT_COLOR', domain='CORNER')
    for item in layer.data:
        item.color = (.2, .4, .6, .7)
    material = bpy.data.materials.new('Color precision'); material.use_nodes = True
    node = material.node_tree.nodes.new('ShaderNodeVertexColor'); node.layer_name = 'Paint'
    material.node_tree.links.new(node.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    source.data.materials.append(material)
    path = tmp_path / 'paint.glb'
    assert bpy.ops.export_scene.gltf(filepath=str(path), use_selection=True) == {'FINISHED'}
    try:
        yield source, path
    finally:
        created = [x for k in _IMPORT_DATA_KINDS for x in getattr(bpy.data, k) if x not in before[k]]
        bpy.data.batch_remove(ids=created)
        if not enabled:
            bpy.context.preferences.addons.remove(bpy.context.preferences.addons['blender_adapter'])


def test_scoped_import_preserves_float_color(painted_file):
    source, path = painted_file
    before = set(bpy.data.objects)
    with colors.preserve_import_colors():
        assert bpy.ops.import_scene.gltf(filepath=str(path)) == {'FINISHED'}
    mesh, = [o.data for o in set(bpy.data.objects) - before if o.type == 'MESH']
    layer = mesh.color_attributes['Color']
    assert layer.data_type == 'FLOAT_COLOR'
    for item in layer.data:
        assert tuple(item.color)[:3] == pytest.approx((.2, .4, .6), abs=1e-7)
    assert not any(a.name.startswith('_AA_COLOR_') for a in mesh.attributes)
    # Native imports outside the scope retain Blender's ordinary behavior.
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    mesh, = [o.data for o in set(bpy.data.objects) - before if o.type == 'MESH']
    assert mesh.color_attributes['Color'].data_type == 'BYTE_COLOR'


def test_critical_color_failure_rolls_back(painted_file, monkeypatch):
    source, path = painted_file
    original = colors.ColorImportExtension.gather_import_mesh_after_hook
    def fail(self, *args):
        original(self, *args)
        raise ValueError('Injected precision failure')
    monkeypatch.setattr(colors.ColorImportExtension, 'gather_import_mesh_after_hook', fail)
    before = {k: set(getattr(bpy.data, k)) for k in _IMPORT_DATA_KINDS}
    selected = set(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    with pytest.raises(RuntimeError):
        _import_external(str(path), '.glb', bpy.context)
    assert all(set(getattr(bpy.data, k)) == v for k, v in before.items())
    assert set(bpy.context.selected_objects) == selected
    assert bpy.context.view_layer.objects.active == active
    assert colors._scope.get() is None

def _rewrite_glb(path, change):
    import json
    import struct
    raw = path.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + size])
    change(document)
    encoded = json.dumps(document).encode()
    encoded += b' ' * (-len(encoded) % 4)
    tail = raw[20 + size:]
    path.write_bytes(struct.pack('<III', 0x46546c67, 2, 20 + len(encoded) + len(tail)) +
                     struct.pack('<II', len(encoded), 0x4e4f534a) + encoded + tail)


def test_missing_primitive_color_stays_white(painted_file):
    from copy import deepcopy
    source, path = painted_file
    def change(document):
        primitives = document['meshes'][0]['primitives']
        second = deepcopy(primitives[0])
        del second['attributes']['COLOR_0']
        primitives.append(second)
    _rewrite_glb(path, change)
    before = set(bpy.data.objects)
    with colors.preserve_import_colors():
        bpy.ops.import_scene.gltf(filepath=str(path))
    mesh, = [o.data for o in set(bpy.data.objects) - before if o.type == 'MESH']
    values = [tuple(item.color) for item in mesh.color_attributes['Color'].data]
    assert any(v == (1, 1, 1, 1) for v in values)
    assert any(abs(v[0] - .2) < 1e-7 for v in values)
    assert all(v[:3] == (1, 1, 1) or abs(v[0] - .2) < 1e-7 for v in values)


def test_temporary_name_collision_rejects_without_overwriting(painted_file, monkeypatch):
    from types import SimpleNamespace
    source, path = painted_file
    monkeypatch.setattr(colors, 'uuid4', lambda: SimpleNamespace(hex='fixed'))
    def change(document):
        attrs = document['meshes'][0]['primitives'][0]['attributes']
        attrs['_AA_COLOR_fixed_COLOR_0'] = attrs['POSITION']
    _rewrite_glb(path, change)
    original = path.read_bytes()
    before = set(bpy.data.objects)
    with pytest.raises(RuntimeError):
        _import_external(str(path), '.glb', bpy.context)
    assert set(bpy.data.objects) == before
    assert path.read_bytes() == original
    assert colors._scope.get() is None

def test_asset_import_uses_precision_scope(painted_file):
    source, path = painted_file
    before = set(bpy.data.objects)
    _import_external(str(path), '.glb', bpy.context)
    meshes = [o.data for o in set(bpy.data.objects) - before if o.type == 'MESH']
    assert meshes
    assert all(mesh.color_attributes['Color'].data_type == 'FLOAT_COLOR' for mesh in meshes)
    assert colors._scope.get() is None
