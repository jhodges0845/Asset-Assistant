# SPDX-License-Identifier: GPL-3.0-or-later
"""Fresh-process skinned LOD preview lifecycle check."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_adapter.lod_skin_preview import preview_skin_lods, recover_skin_lod_preview, _skin_signature


def main():
    if '--' in sys.argv:
        records = [c for c in bpy.data.collections if c.get('lod_skin_preview')]
        assert len(records) == 2
        for record in records:
            preview = recover_skin_lod_preview(record)
            source = preview.source
            assert _skin_signature(source) == preview.source_signature
            if record.name == 'Apply skin':
                preview.apply()
                assert record['asset_assistant_lod_state'] == 'APPLIED'
            else:
                names = [obj.name for obj in preview.objects]
                preview.cancel()
                assert all(name not in bpy.data.objects for name in names)
            assert source.name in bpy.data.objects
        print('Fresh-process skin LOD apply/cancel passed')
        return
    for name in ('Apply skin', 'Cancel skin'):
        bpy.ops.object.armature_add()
        rig = bpy.context.object
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
        source = bpy.context.object
        source.vertex_groups.new(name=rig.data.bones[0].name).add(list(range(len(source.data.vertices))), 1, 'REPLACE')
        source.modifiers.new('Skin', 'ARMATURE').object = rig
        preview = preview_skin_lods(source, bpy.context.scene, max_distance=.3)
        preview.collection.name = name
    with TemporaryDirectory(prefix='skin-lod-reopen-') as directory:
        path = Path(directory) / 'preview.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(path))
        subprocess.run([bpy.app.binary_path, '--background', str(path), '--python-exit-code', '1',
                        '--python', str(Path(__file__).resolve()), '--', 'verify'], check=True, timeout=120)


if __name__ == '__main__':
    main()
