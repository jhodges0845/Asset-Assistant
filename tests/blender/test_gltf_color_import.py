# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
import pytest
from blender_adapter import gltf_color_import as colors
from blender_adapter.asset_file_import_ui import _IMPORT_DATA_KINDS, _import_external


@pytest.fixture
def import_session():
    before = {k: set(getattr(bpy.data, k)) for k in _IMPORT_DATA_KINDS}
    enabled = 'blender_adapter' in bpy.context.preferences.addons
    if not enabled:
        bpy.context.preferences.addons.new().module = 'blender_adapter'
    try:
        yield
    finally:
        created = [x for k in _IMPORT_DATA_KINDS for x in getattr(bpy.data, k) if x not in before[k]]
        bpy.data.batch_remove(ids=created)
        if not enabled:
            bpy.context.preferences.addons.remove(bpy.context.preferences.addons['blender_adapter'])


@pytest.fixture
def painted_file(tmp_path, import_session):
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
    return source, path


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

def test_painted_lod_bundle_roundtrip(painted_file, tmp_path):
    from blender_adapter.lod import preview_static_lods, _signature
    from blender_adapter.lod_export import export_static_lod_bundle
    from blender_adapter.materials import material_issues
    source, _ = painted_file
    assert material_issues((source,))  # Other file exporters remain conservative.
    assert not material_issues((source,), allow_vertex_colors=True)
    original = _signature(source)
    preview = preview_static_lods(source, bpy.context.scene, ratios=(.5,))
    preview.apply()
    destination = tmp_path / 'painted-bundle'
    manifest = export_static_lod_bundle(preview.collection, bpy.context, destination)
    for level in manifest['levels']:
        before = set(bpy.data.objects)
        _import_external(str(destination / level['file']), '.glb', bpy.context)
        mesh, = [o.data for o in set(bpy.data.objects) - before if o.type == 'MESH']
        assert mesh.color_attributes['Color'].data_type == 'FLOAT_COLOR'
        material = mesh.materials[0]
        shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pending = [link.from_node for link in shader.inputs['Base Color'].links]
        reached = set()
        while pending:
            node = pending.pop()
            if node in reached:
                continue
            reached.add(node)
            pending.extend(link.from_node for socket in node.inputs for link in socket.links)
        assert any(n.type == 'VERTEX_COLOR' and
                   (n.layer_name == 'Color' or (not n.layer_name and mesh.color_attributes.render_color_index == 0))
                   for n in reached)
        for item in mesh.color_attributes['Color'].data:
            assert tuple(item.color)[:3] == pytest.approx((.2, .4, .6), abs=1e-7)
    assert _signature(source) == original


def test_color_material_validation_checks_each_mesh(painted_file):
    from blender_adapter.materials import material_issues
    source, _ = painted_file
    other = source.copy(); other.data = source.data.copy()
    bpy.context.scene.collection.objects.link(other)
    other.data.color_attributes.remove(other.data.color_attributes['Paint'])
    assert material_issues((source, other), allow_vertex_colors=True)
    node = next(n for n in source.data.materials[0].node_tree.nodes if n.type == 'VERTEX_COLOR')
    node.layer_name = ''
    assert not material_issues((source,), allow_vertex_colors=True)
    source.data.color_attributes.remove(source.data.color_attributes['Paint'])
    assert material_issues((source,), allow_vertex_colors=True)

def test_imported_painted_mesh_can_build_lods(painted_file):
    from blender_adapter.lod import preview_static_lods, _signature
    from blender_adapter.validation import inspect_objects
    source, path = painted_file
    before = set(bpy.data.objects)
    _import_external(str(path), '.glb', bpy.context)
    imported, = [o for o in set(bpy.data.objects) - before if o.type == 'MESH']
    original = _signature(imported)
    preview = preview_static_lods(imported, bpy.context.scene, ratios=(.5,))
    assert not inspect_objects(preview.objects, require_manifold_geometry=False).invalid_meshes
    assert _signature(imported) == original
    preview.apply()


@pytest.mark.parametrize('component,code,maximum', [(5121, 'B', 255), (5123, 'H', 65535)])
@pytest.mark.parametrize('width', [3, 4])
def test_normalized_external_paint_vertex_mapping(tmp_path, import_session, component, code, maximum, width):
    """Independent external fixture: nonuniform, interleaved, two color sets."""
    import base64
    import json
    import struct
    positions = struct.pack('<9f', 0, 0, 0, 1, 0, 0, 2, 1, 0)
    rows = [(0, maximum // 2, maximum, maximum // 3),
            (maximum, 0, maximum // 3, maximum),
            (maximum // 4, maximum, 0, 0)]
    # glTF vertex attributes are four-byte aligned, including RGB uint8/uint16.
    stride = (struct.calcsize(code) * width + 3) // 4 * 4
    def encode(values):
        return b''.join(struct.pack('<' + code * width, *row[:width]).ljust(stride, b'\0')
                        for row in values)
    first, second = encode(rows), encode(list(reversed(rows)))
    binary = positions + first + second
    document = {
        'asset': {'version': '2.0'},
        'buffers': [{'byteLength': len(binary), 'uri': 'data:application/octet-stream;base64,' +
                     base64.b64encode(binary).decode()}],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': 0, 'byteLength': len(positions)},
            {'buffer': 0, 'byteOffset': len(positions), 'byteLength': len(first), 'byteStride': stride},
            {'buffer': 0, 'byteOffset': len(positions) + len(first), 'byteLength': len(second), 'byteStride': stride}],
        'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3',
                       'min': [0, 0, 0], 'max': [2, 1, 0]}] + [
            {'bufferView': i, 'componentType': component, 'normalized': True,
             'count': 3, 'type': 'VEC' + str(width)} for i in (1, 2)],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0, 'COLOR_0': 1, 'COLOR_1': 2}}]}],
        'nodes': [{'mesh': 0}], 'scenes': [{'nodes': [0]}], 'scene': 0,
    }
    path = tmp_path / 'normalized.gltf'
    path.write_text(json.dumps(document))
    original = path.read_bytes()
    before = set(bpy.data.objects)
    _import_external(str(path), '.gltf', bpy.context)
    mesh, = [o.data for o in set(bpy.data.objects) - before if o.type == 'MESH']
    assert len(mesh.polygons) == 1
    assert len(mesh.color_attributes) == 2
    for name, expected_rows in [('Color', rows), ('Color.001', list(reversed(rows)))]:
        layer = mesh.color_attributes[name]
        assert layer.data_type == 'FLOAT_COLOR'
        for i, item in enumerate(layer.data):
            vertex = mesh.loops[i].vertex_index if layer.domain == 'CORNER' else i
            row = expected_rows[round(mesh.vertices[vertex].co.x)]
            expected = tuple(v / maximum for v in row[:width]) + ((1,) if width == 3 else ())
            assert tuple(item.color) == pytest.approx(expected, abs=1e-7)
    assert not any(a.name.startswith('_AA_COLOR_') for a in mesh.attributes)
    assert mesh.color_attributes.render_color_index == 0
    assert colors._scope.get() is None
    assert path.read_bytes() == original
