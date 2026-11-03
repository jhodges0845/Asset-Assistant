# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise skinned preview operators from an isolated release ZIP."""
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
    assert 'object_core' not in sys.modules
    addon_utils.disable('humanoid_blender', default_set=True)
print('PACKAGED_SKIN_LOD_OK')
