# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify LOD preview recovery in a separate Blender process."""
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_adapter.lod import preview_static_lods, recover_static_lod_preview, _signature


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if args:
        for collection in list(bpy.data.collections):
            if collection.get('asset_assistant_lod_state') != 'PREVIEW':
                continue
            preview = recover_static_lod_preview(collection)
            source = preview.source
            before = _signature(source)
            assert before == preview.source_signature
            assert source.material_slots[0].link == 'OBJECT'
            assert all(obj.material_slots[0].material == source.material_slots[0].material
                       for obj in preview.objects)
            if source.name == 'Apply source':
                preview.apply()
                assert collection['asset_assistant_lod_state'] == 'APPLIED'
            else:
                names = [obj.name for obj in preview.objects]
                preview.cancel()
                assert all(name not in bpy.data.objects for name in names)
            assert _signature(source) == before
        assert len([c for c in bpy.data.collections if c.get('asset_assistant_lod_state') == 'APPLIED']) == 1
        print('Fresh-process LOD apply/cancel passed')
        return
    with TemporaryDirectory(prefix='asset-assistant-lod-') as directory:
        for name in ('Apply source', 'Cancel source'):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
            source = bpy.context.object
            source.name = name
            source.data.materials.append(bpy.data.materials.new(name + ' material'))
            source.material_slots[0].link = 'OBJECT'
            source.material_slots[0].material = bpy.data.materials.new(name + ' visible override')
            preview_static_lods(source, bpy.context.scene)
        checkpoint = Path(directory) / 'preview.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
        subprocess.run([bpy.app.binary_path, '--background', str(checkpoint),
                        '--python-exit-code', '1', '--python', str(Path(__file__).resolve()),
                        '--', 'verify'], check=True, timeout=120)


if __name__ == '__main__':
    main()
