# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify multi-mesh LOD grouping across a fresh Blender process."""
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_adapter.lod_sets import preview_static_lod_set, recover_static_lod_set
from blender_adapter.lod import _signature


def main():
    if '--' in sys.argv:
        records = [c for c in bpy.data.collections if c.get('lod_set_state') == 'PREVIEW']
        assert len(records) == 2
        for record in records:
            group = recover_static_lod_set(record)
            sources = tuple(p.source for p in group.previews)
            assert len(sources) == 2
            before = tuple(_signature(obj) for obj in sources)
            assert before == tuple(p.source_signature for p in group.previews)
            if record.name == 'Apply group':
                group.apply()
                assert record['lod_set_state'] == 'APPLIED'
            else:
                names = tuple(p.collection.name for p in group.previews)
                group.cancel()
                assert all(name not in bpy.data.collections for name in names)
            assert tuple(_signature(obj) for obj in sources) == before
        print('Fresh-process multi-mesh LOD apply/cancel passed')
        return
    for name in ('Apply group', 'Cancel group'):
        sources = []
        for index in range(2):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
            sources.append(bpy.context.object)
        group = preview_static_lod_set(sources, bpy.context.scene)
        group.record.name = name
    with TemporaryDirectory(prefix='lod-set-reopen-') as directory:
        checkpoint = Path(directory) / 'sets.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
        subprocess.run([bpy.app.binary_path, '--background', str(checkpoint),
                        '--python-exit-code', '1', '--python', str(Path(__file__).resolve()),
                        '--', 'verify'], check=True, timeout=120)


if __name__ == '__main__':
    main()
