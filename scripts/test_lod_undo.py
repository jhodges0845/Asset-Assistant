# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise Blender undo snapshots across LOD operations in an isolated runtime.

Explicit undo pushes are required in background scripts; this does not certify
interactive event dispatch or keyboard shortcuts.
"""
from pathlib import Path
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_adapter import lod_ui
from blender_adapter.lod import recover_static_lod_preview, _signature


def main():
    lod_ui.register()
    bpy.context.preferences.edit.use_global_undo = True
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
    source_name = bpy.context.object.name
    signature = _signature(bpy.context.object)
    bpy.ops.ed.undo_push(message='LOD source')
    bpy.ops.asset_assistant.lod_preview()
    bpy.ops.ed.undo_push(message='LOD preview')
    collection, = lod_ui._previews(bpy.context.scene)
    name = collection.name
    bpy.ops.asset_assistant.lod_finish(collection_name=name, action='APPLY')
    applied_name = next(c.name for c in bpy.data.collections if c.get('asset_assistant_lod_state') == 'APPLIED')
    bpy.ops.ed.undo_push(message='LOD applied')
    bpy.ops.ed.undo()
    recovered = recover_static_lod_preview(bpy.data.collections[name])
    assert recovered.source == bpy.data.objects[source_name]
    assert _signature(recovered.source) == signature
    bpy.ops.ed.redo()
    assert bpy.data.collections[applied_name]['asset_assistant_lod_state'] == 'APPLIED'
    bpy.ops.ed.undo()
    bpy.ops.asset_assistant.lod_finish(collection_name=name, action='CANCEL')
    bpy.ops.ed.undo_push(message='LOD discarded')
    assert name not in bpy.data.collections
    bpy.ops.ed.undo()
    recovered = recover_static_lod_preview(bpy.data.collections[name])
    assert len(recovered.objects) == 2
    assert _signature(recovered.source) == signature
    bpy.ops.ed.redo()
    assert name not in bpy.data.collections
    assert _signature(bpy.data.objects[source_name]) == signature
    print('LOD snapshot undo/redo passed for apply and discard')
    lod_ui.unregister()


if __name__ == '__main__':
    main()
