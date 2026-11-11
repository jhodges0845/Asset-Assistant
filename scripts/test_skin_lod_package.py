# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise LOD lifecycles and export from an isolated release ZIP."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import bpy
root = Path(__file__).resolve().parents[1]
sys.path[:] = [p for p in sys.path if Path(p or '.').resolve() not in (root, root / 'scripts')]
with TemporaryDirectory() as directory:
    with ZipFile(root / 'dist/asset_assistant.zip') as z:
        z.extractall(directory)
    sys.path.insert(0, directory)
    import humanoid_blender as addon
    from humanoid_blender.lod_ui import _skin_previews
    import addon_utils
    addon_utils.enable('humanoid_blender', default_set=True, persistent=False)
    bpy.ops.object.armature_add()
    rig = bpy.context.object
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    source = bpy.context.object
    source.vertex_groups.new(name=rig.data.bones[0].name).add(list(range(len(source.data.vertices))), 1, 'REPLACE')
    source.modifiers.new('Skin', 'ARMATURE').object = rig
    assert bpy.ops.asset_assistant.skin_lod_preview(max_distance=.3) == {'FINISHED'}
    preview, = _skin_previews(bpy.context.scene)
    assert bpy.ops.asset_assistant.lod_finish(collection_name=preview.name, action='CANCEL') == {'FINISHED'}
    # The real installed package exposes the supported glTF extension factory.
    from humanoid_blender.lod_export import LODExportLevel
    from humanoid_blender.lod_skin_export import stage_skin_lod_level
    from humanoid_blender.lod_weight_export import preserve_weights, extension_available
    assert extension_available()
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bone = rig.data.edit_bones.new('Tiny')
    bone.head, bone.tail = (1, 0, 0), (1, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    indices = list(range(len(source.data.vertices)))
    source.vertex_groups.new(name='Tiny').add(indices, .00001, 'REPLACE')
    source.vertex_groups[0].add(indices, .99999, 'REPLACE')
    path = Path(directory) / 'weights.glb'
    with stage_skin_lod_level(LODExportLevel(0, (source,), (rig,), 0), bpy.context.scene) as staged:
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        for obj in staged.children:
            obj.select_set(True)
        with preserve_weights(staged, dict(filepath=str(path), use_selection=True,
                                          export_all_influences=True)) as options:
            assert bpy.ops.export_scene.gltf(**options) == {'FINISHED'}
    import json
    import struct
    raw = path.read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + length])
    for primitive in document['meshes'][0]['primitives']:
        assert not any(key.startswith('_AA_LOD_') for key in primitive['attributes'])
        accessor = document['accessors'][primitive['attributes']['WEIGHTS_0']]
        view = document['bufferViews'][accessor['bufferView']]
        offset = 28 + length + view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        weights = struct.unpack_from('<4f', raw, offset)
        assert abs(sorted(w for w in weights if w > 0)[0] - .00001) < 1e-10
    # Exercise the complete static path through registered packaged operators.
    # Import each exported level independently; do not infer round-trip success
    # from a nonempty file or from the manifest alone.
    from humanoid_blender.lod import _signature, _triangles
    from humanoid_blender.lod_ui import _previews
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    static_source = bpy.context.object
    paint = static_source.data.color_attributes.new(name='Paint', type='FLOAT_COLOR', domain='CORNER')
    for item in paint.data:
        item.color = (.2, .4, .6, 1)
    material = bpy.data.materials.new('Packaged LOD material')
    material.use_nodes = True
    color = material.node_tree.nodes.new('ShaderNodeVertexColor')
    color.layer_name = 'Paint'
    material.node_tree.links.new(color.outputs['Color'],
                                material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    static_source.data.materials.append(material)
    source_signature = _signature(static_source)
    assert bpy.ops.asset_assistant.lod_preview(level_count=2) == {'FINISHED'}
    static_preview, = _previews(bpy.context.scene)
    assert bpy.ops.asset_assistant.lod_finish(
        collection_name=static_preview.name, action='APPLY') == {'FINISHED'}
    assert not _previews(bpy.context.scene)
    original_objects = set(bpy.data.objects)
    selected = set(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    assert bpy.ops.asset_assistant.lod_export_bundle(
        collection_name=static_preview.name, directory=directory,
        bundle_name='static-roundtrip') == {'FINISHED'}
    assert set(bpy.data.objects) == original_objects
    assert set(bpy.context.selected_objects) == selected
    assert bpy.context.view_layer.objects.active == active
    bundle = Path(directory) / 'static-roundtrip'
    manifest = json.loads((bundle / 'lod-manifest.json').read_text())
    assert manifest['engine_lod_configured'] is False
    assert [level['index'] for level in manifest['levels']] == [0, 1, 2]
    counts = []
    for level in manifest['levels']:
        before = set(bpy.data.objects)
        from humanoid_blender.asset_file_import_ui import _import_external
        _import_external(str(bundle / level['file']), '.glb', bpy.context)
        imported = set(bpy.data.objects) - before
        meshes = [obj for obj in imported if obj.type == 'MESH']
        assert len(meshes) == level['mesh_count'] == 1
        count = sum(_triangles(obj.data) for obj in meshes)
        assert count == level['triangles']
        counts.append(count)
        for obj in meshes:
            assert obj.data.uv_layers.active is not None
            colors = obj.data.color_attributes['Color']
            assert colors.data_type == 'FLOAT_COLOR'
            assert all(abs(value - expected) < 1e-7 for item in colors.data
                       for value, expected in zip(item.color, (.2, .4, .6, 1)))
            assert not any(attr.name.startswith('_AA_COLOR_') for attr in obj.data.attributes)
            assert len(obj.data.materials) == 1 and obj.data.materials[0] is not None
        if level['index'] == 0:
            # Imported glTF seam vertices can leave wires during reduction.
            # Exercise the packaged cleanup through the artist-facing operators.
            imported_source, = meshes
            imported_signature = _signature(imported_source)
            bpy.ops.object.select_all(action='DESELECT')
            imported_source.select_set(True)
            bpy.context.view_layer.objects.active = imported_source
            before_preview = {kind: set(getattr(bpy.data, kind))
                              for kind in ('objects', 'meshes', 'collections')}
            assert bpy.ops.asset_assistant.lod_preview(level_count=1) == {'FINISHED'}
            recovered, = _previews(bpy.context.scene)
            from humanoid_blender.validation import inspect_objects
            assert not inspect_objects(tuple(recovered.objects), require_manifold_geometry=False).invalid_meshes
            assert _signature(imported_source) == imported_signature
            assert bpy.ops.asset_assistant.lod_finish(
                collection_name=recovered.name, action='CANCEL') == {'FINISHED'}
            assert not _previews(bpy.context.scene)
            assert _signature(imported_source) == imported_signature
            assert all(set(getattr(bpy.data, kind)) == previous
                       for kind, previous in before_preview.items())
            print('PACKAGED_IMPORTED_LOD_PREVIEW_OK: reduction, discard and source preservation')
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)
        assert _signature(static_source) == source_signature
    assert counts[0] > counts[1] > counts[2] > 0
    assert set(bpy.data.objects) == original_objects
    print('PACKAGED_STATIC_LOD_ROUNDTRIP_OK: applied levels, UV/material presence, triangle counts and source preservation')
    from humanoid_blender import gltf_color_import
    Path(gltf_color_import.__file__).resolve().relative_to(Path(directory).resolve())
    assert gltf_color_import._scope.get() is None
    assert 'object_core' not in sys.modules
    addon_utils.disable('humanoid_blender', default_set=True)
print('PACKAGED_SKIN_LOD_OK')
