# SPDX-License-Identifier: GPL-3.0-or-later
"""Real static file imports use the same inspect/adopt/re-export workflow."""
from types import SimpleNamespace
import bpy
import pytest
from blender_adapter import asset_file_import_ui as files
from blender_adapter.asset_inspection_ui import inspect_selected_asset, adopt_external_asset
from blender_adapter.targets import get_adapter


@pytest.mark.parametrize('format',['blend','glb','gltf','fbx'])
def test_static_file_import_adoption_and_reexport(format,tmp_path):
    previous=bpy.context.window.scene
    kinds=('objects','meshes','armatures','collections','materials','images','actions')
    before={k:set(getattr(bpy.data,k)) for k in kinds}
    scene=bpy.data.scenes.new('Static file acceptance')
    bpy.context.window.scene=scene
    try:
        bpy.ops.mesh.primitive_cube_add(size=2.)
        cube=bpy.context.object
        material=bpy.data.materials.new('Artist material')
        cube.data.materials.append(material)
        path=tmp_path/('artist.'+format)
        if format=='blend':
            collection=bpy.data.collections.new('Artist prop')
            scene.collection.children.link(collection)
            collection.objects.link(cube)
            bpy.data.libraries.write(str(path),{collection})
            report=files.preflight_asset_file(path)
            assert report['status']=='ASSET_CANDIDATE'
            root=files._import_blend_collection(str(path),report['candidate'],bpy.context)
        else:
            if format=='fbx':
                bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,add_leaf_bones=False)
            else:
                bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB' if format=='glb' else 'GLTF_SEPARATE',use_selection=True,use_active_scene=True)
            assert files.preflight_asset_file(path)['status']=='EXTERNAL_ASSET'
            root=files._import_external(str(path),'.'+format,bpy.context)
        report=inspect_selected_asset(root)
        assert report['can_adopt']
        assert report['metrics']['meshes']==1
        assert report['metrics']['armatures']==0
        assert report['metrics']['materials']>=1
        from blender_adapter.asset_structure import asset_meshes
        points=[obj.matrix_world @ vertex.co for obj in asset_meshes(root) for vertex in obj.data.vertices]
        for axis in range(3):
            assert abs(max(p[axis] for p in points)-min(p[axis] for p in points)-2.)<.0001
        class AdoptionScene(dict):
            humanoid_settings=SimpleNamespace(target=None,asset_use='STATIC')
            unit_settings=scene.unit_settings
        adoption=AdoptionScene()
        adopted=adopt_external_asset(SimpleNamespace(scene=adoption),root)
        assert adoption.humanoid_settings.target is adopted
        assert adopted.get('asset_assistant_external_asset')
        assert not adopted.get('generator')
        result=get_adapter('GODOT',asset_use='STATIC').export(adopted,bpy.context,tmp_path/'roundtrip.glb')
        assert result.success,result.issues
        assert (tmp_path/'roundtrip.glb').stat().st_size>0
        assert cube.name in bpy.data.objects  # Unrelated source survives import.
    finally:
        bpy.context.window.scene=previous
        bpy.data.scenes.remove(scene)
        for kind in kinds:
            for item in set(getattr(bpy.data,kind))-before[kind]:
                getattr(bpy.data,kind).remove(item,do_unlink=True)


def test_open_game_surface_does_not_relax_print_or_degenerate_checks():
    from blender_adapter.validation import inspect_objects
    mesh=bpy.data.meshes.new('Surface validity')
    obj=bpy.data.objects.new('Surface validity',mesh)
    try:
        mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0)],[],[(0,1,2)])
        assert not inspect_objects([obj],require_manifold_geometry=False).invalid_meshes
        assert inspect_objects([obj],require_manifold_geometry=True).invalid_meshes
        mesh.vertices[2].co=(2,0,0)
        mesh.update()
        assert inspect_objects([obj],require_manifold_geometry=False).invalid_meshes
    finally:
        bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.meshes.remove(mesh)


@pytest.mark.parametrize("extension", ["gltf", "glb"])
def test_multiscene_import_rejection_restores_artist_scene(extension, tmp_path):
    import json
    import struct
    document = {
        "asset": {"version": "2.0"}, "scene": 0,
        "scenes": [{"nodes": [0]}, {"nodes": [1]}],
        "nodes": [{"name": "First scene object"}, {"name": "Other scene object"}],
    }
    payload = json.dumps(document).encode("utf-8")
    path = tmp_path / ("multiple-scenes." + extension)
    if extension == "glb":
        payload += b" " * (-len(payload) % 4)
        path.write_bytes(struct.pack("<4sII", b"glTF", 2, 20 + len(payload))
                         + struct.pack("<I4s", len(payload), b"JSON") + payload)
    else:
        path.write_bytes(payload)
    scene = bpy.context.window.scene
    layer = bpy.context.window.view_layer
    selected = set(bpy.context.selected_objects)
    active = layer.objects.active
    before = {kind: set(getattr(bpy.data, kind)) for kind in files._IMPORT_DATA_KINDS}
    with pytest.raises(ValueError, match="Export one scene"):
        files._import_external(str(path), "." + extension, bpy.context)
    assert bpy.context.window.scene == scene
    assert bpy.context.window.view_layer == layer
    assert set(bpy.context.selected_objects) == selected
    assert layer.objects.active == active
    for kind, original in before.items():
        assert set(getattr(bpy.data, kind)) == original, kind


def test_import_activation_failure_removes_partial_data(monkeypatch, tmp_path):
    import json
    path = tmp_path / "single.gltf"
    path.write_text(json.dumps({
        "asset": {"version": "2.0"}, "scene": 0,
        "scenes": [{"nodes": [0]}], "nodes": [{"name": "Imported empty"}],
    }))
    before = {kind: set(getattr(bpy.data, kind)) for kind in files._IMPORT_DATA_KINDS}
    selected = set(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active

    def fail_activation(*args, **kwargs):
        bpy.data.materials.new("Partial import material")
        bpy.data.actions.new("Partial import action")
        raise RuntimeError("Injected activation failure")

    monkeypatch.setattr(files, "_activate_imported_object", fail_activation)
    with pytest.raises(RuntimeError, match="Injected activation failure"):
        files._import_external(str(path), ".gltf", bpy.context)
    for kind, original in before.items():
        assert set(getattr(bpy.data, kind)) == original, kind
    assert set(bpy.context.selected_objects) == selected
    assert bpy.context.view_layer.objects.active == active
