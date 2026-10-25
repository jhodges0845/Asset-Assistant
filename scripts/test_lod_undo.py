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
    check_group_undo()
    lod_ui.unregister()


def check_group_undo():
    from blender_adapter.lod_sets import recover_static_lod_set
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    names = []
    for index in range(2):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
        names.append(bpy.context.object.name)
    for name in names:
        bpy.data.objects[name].select_set(True)
    signatures = tuple(_signature(bpy.data.objects[name]) for name in names)
    bpy.ops.ed.undo_push(message='Group sources')
    bpy.ops.asset_assistant.lod_preview(use_selection=True)
    record, = lod_ui._groups(bpy.context.scene)
    record_name = record.name
    bpy.ops.ed.undo_push(message='Group preview')
    bpy.ops.asset_assistant.lod_finish(collection_name=record_name, action='APPLY')
    bpy.ops.ed.undo_push(message='Group applied')
    bpy.ops.ed.undo()
    restored = recover_static_lod_set(bpy.data.collections[record_name])
    assert len(restored.previews) == 2
    assert {p.source.name for p in restored.previews} == set(names)
    bpy.ops.ed.redo()
    assert bpy.data.collections[record_name]['lod_set_state'] == 'APPLIED'
    bpy.ops.ed.undo()
    bpy.ops.asset_assistant.lod_finish(collection_name=record_name, action='CANCEL')
    bpy.ops.ed.undo_push(message='Group discarded')
    assert record_name not in bpy.data.collections
    bpy.ops.ed.undo()
    restored = recover_static_lod_set(bpy.data.collections[record_name])
    assert len(restored.previews) == 2
    assert all(len(p.objects) == 2 for p in restored.previews)
    bpy.ops.ed.redo()
    assert record_name not in bpy.data.collections
    assert tuple(_signature(bpy.data.objects[name]) for name in names) == signatures
    assert {obj.name for obj in bpy.context.selected_objects} == set(names)
    print('Multi-mesh LOD snapshot undo/redo passed for apply and discard')


if __name__ == '__main__':
    main()
