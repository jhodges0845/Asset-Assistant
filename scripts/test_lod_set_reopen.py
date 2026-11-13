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
        assert len(records) == 4
        for record in records:
            group = recover_static_lod_set(record)
            sources = tuple(p.source for p in group.previews)
            assert len(sources) == 2
            before = tuple(_signature(obj) for obj in sources)
            assert before == tuple(record['expected_sources'])
            levels = tuple(obj for p in group.previews for obj in p.objects)
            expected_levels = tuple(record['expected_levels'])
            assert tuple(_signature(obj) for obj in levels) == expected_levels
            if record.name.startswith('Edited '):
                try:
                    group.apply()
                except ValueError as exc:
                    assert 'changed' in str(exc), str(exc)
                else:
                    raise AssertionError('Edited group applied')
                assert record['lod_set_state'] == 'PREVIEW'
                assert all(p.collection['asset_assistant_lod_state'] == 'PREVIEW' for p in group.previews)
                assert tuple(_signature(obj) for obj in sources) == before
                assert tuple(_signature(obj) for obj in levels) == expected_levels
            if record.name == 'Apply group':
                group.apply()
                assert record['lod_set_state'] == 'APPLIED'
            else:
                names = tuple(p.collection.name for p in group.previews)
                group.cancel()
                assert all(name not in bpy.data.collections for name in names)
            assert tuple(_signature(obj) for obj in sources) == before
        print('Fresh-process multi-mesh LOD apply/cancel and atomic edited-state rejection passed')
        return
    for name in ('Apply group', 'Cancel group', 'Edited source group', 'Edited preview group'):
        sources = []
        for index in range(2):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
            sources.append(bpy.context.object)
        group = preview_static_lod_set(sources, bpy.context.scene)
        group.record.name = name
        # Edit the last member so rejection must leave earlier members pending.
        if name == 'Edited source group':
            sources[-1].data.vertices[0].co.x += .1
        elif name == 'Edited preview group':
            group.previews[-1].objects[0].data.vertices[0].co.x += .1
        bpy.context.view_layer.update()
        group.record['expected_sources'] = [_signature(obj) for obj in sources]
        group.record['expected_levels'] = [_signature(obj) for p in group.previews for obj in p.objects]
    with TemporaryDirectory(prefix='lod-set-reopen-') as directory:
        checkpoint = Path(directory) / 'sets.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
        subprocess.run([bpy.app.binary_path, '--background', str(checkpoint),
                        '--python-exit-code', '1', '--python', str(Path(__file__).resolve()),
                        '--', 'verify'], check=True, timeout=120)


if __name__ == '__main__':
    main()
