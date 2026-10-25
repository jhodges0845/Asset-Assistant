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
    addon.register()
    bpy.ops.object.armature_add()
    rig = bpy.context.object
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    source = bpy.context.object
    source.vertex_groups.new(name=rig.data.bones[0].name).add(list(range(len(source.data.vertices))), 1, 'REPLACE')
    source.modifiers.new('Skin', 'ARMATURE').object = rig
    assert bpy.ops.asset_assistant.skin_lod_preview(max_distance=.3) == {'FINISHED'}
    preview, = _skin_previews(bpy.context.scene)
    assert bpy.ops.asset_assistant.lod_finish(collection_name=preview.name, action='CANCEL') == {'FINISHED'}
    assert 'object_core' not in sys.modules
    addon.unregister()
print('PACKAGED_SKIN_LOD_OK')
