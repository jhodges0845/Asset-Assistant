# SPDX-License-Identifier: GPL-3.0-or-later
"""Headless glTF export integration, including artifact content and scene scope."""
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from object_core import BodyType, HumanoidSpec, generate_mesh, generate_proportions
from humanoid_blender.adapter import create_character
from humanoid_blender.animation import add_idle
from humanoid_blender.workflow import add_basic_rig
from humanoid_blender.targets import get_adapter
from humanoid_blender.materials import prepare_materials


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and length == len(data)
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    return json.loads(data[20:20 + size].decode('utf8'))


@unittest.skipIf(bpy is None, 'requires Blender; use scripts/test_blender.py')
class GodotExportTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ('objects', 'meshes', 'armatures', 'collections', 'materials', 'images', 'actions')}
        self.scene = bpy.data.scenes.new('GodotExportTest')
        bpy.context.window.scene = self.scene
        self.root = create_character(generate_mesh(generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE))), scene=self.scene)
        self.root['height_cm'], self.root['weight_kg'], self.root['body_type'] = 180, 95, 'average'
        prepare_materials(self.root)
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / 'asset.glb'
        self.adapter = get_adapter('GODOT', asset_use='STATIC')

    def tearDown(self):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)
        self.temp.cleanup()

    def test_static_glb_excludes_other_asset_and_restores_selection(self):
        other = create_character(generate_mesh(generate_proportions(HumanoidSpec(175, 80, BodyType.AVERAGE))), scene=self.scene)
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        other.select_set(True)
        bpy.context.view_layer.objects.active = other
        self.scene.frame_set(7, subframe=0.25)
        result = self.adapter.export(self.root, bpy.context, self.path)
        self.assertTrue(result.success, result.issues)
        document = read_glb(result.filepath)
        names = {node.get('name') for node in document['nodes']}
        self.assertIn(self.root.name, names)
        self.assertNotIn(other.name, names)
        self.assertEqual(len(document['meshes']), 15)
        self.assertEqual(set(bpy.context.selected_objects), {other})
        self.assertEqual(bpy.context.view_layer.objects.active, other)
        self.assertEqual(self.scene.frame_current, 7)
        self.assertAlmostEqual(self.scene.frame_subframe, 0.25)

    def test_animated_glb_contains_skin_and_animation(self):
        add_basic_rig(self.root, bpy.context)
        add_idle(self.root, self.scene)
        result = get_adapter('GODOT').export(self.root, bpy.context, self.path)
        self.assertTrue(result.success, result.issues)
        document = read_glb(result.filepath)
        self.assertTrue(document['skins'])
        self.assertTrue(document['animations'][0]['channels'])

    def test_gltf_mesh_root_material_and_texture(self):
        obj = next(child for child in self.root.children if child.type == 'MESH')
        obj.parent = None
        material = bpy.data.materials.new('ExportMaterial')
        material.use_nodes = True
        obj.data.materials.clear()
        obj.data.materials.append(material)
        obj.data.uv_layers.new()
        node = material.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.new('ExportTexture', width=8, height=8)
        node.image.pixels[0] = 0.5
        node.image.pack()
        material.node_tree.links.new(node.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
        result = self.adapter.export(obj, bpy.context, self.path.with_suffix('.gltf'))
        self.assertTrue(result.success, result.issues)
        document = json.loads(Path(result.filepath).read_text())
        self.assertEqual(len(document['meshes']), 1)
        self.assertTrue(document['materials'])
        self.assertTrue(document['textures'])
        for item in document['buffers'] + document['images']:
            self.assertTrue((self.path.parent / item['uri']).is_file())

    def test_preflight_errors_do_not_write_or_change_selection(self):
        before = set(bpy.context.selected_objects)
        result = get_adapter('GODOT').export(self.root, bpy.context, self.path)
        self.assertFalse(result.success)
        self.assertTrue(any(issue.code == 'rig' and issue.status == 'ERROR' for issue in result.issues))
        self.assertFalse(self.path.exists())
        self.assertEqual(set(bpy.context.selected_objects), before)
        self.root.hide_select = True
        self.assertTrue(any(issue.code == 'export_scope' for issue in self.adapter.prepare(self.root, bpy.context)))
        self.root.hide_select = False
        self.scene.unit_settings.scale_length = 0.01
        self.assertTrue(any(issue.code == 'export_units' for issue in self.adapter.prepare(self.root, bpy.context)))

    def test_export_failure_restores_context_and_reports_error(self):
        selected = set(bpy.context.selected_objects)
        active = bpy.context.view_layer.objects.active
        with patch('humanoid_blender.targets._export_gltf', side_effect=RuntimeError('injected failure')):
            result = self.adapter.export(self.root, bpy.context, self.path)
        self.assertFalse(result.success)
        self.assertTrue(any(issue.code == 'export_failed' for issue in result.issues))
        self.assertEqual(set(bpy.context.selected_objects), selected)
        self.assertEqual(bpy.context.view_layer.objects.active, active)

    def test_existing_file_is_preserved(self):
        self.path.write_bytes(b'existing')
        result = self.adapter.export(self.root, bpy.context, self.path)
        self.assertFalse(result.success)
        self.assertEqual(self.path.read_bytes(), b'existing')

    def test_unsupported_objects_transforms_and_nla_are_reported(self):
        camera_data = bpy.data.cameras.new('UnsupportedCamera')
        camera = bpy.data.objects.new('UnsupportedCamera', camera_data)
        self.scene.collection.objects.link(camera)
        camera.parent = self.root
        try:
            issues = self.adapter.prepare(self.root, bpy.context)
            self.assertTrue(any(issue.code == 'export_type' for issue in issues))
        finally:
            bpy.data.objects.remove(camera, do_unlink=True)
            bpy.data.cameras.remove(camera_data)
        self.root.scale.x = 0
        self.assertTrue(any(issue.code == 'export_transform' and issue.status == 'ERROR'
                            for issue in self.adapter.prepare(self.root, bpy.context)))
        self.root.scale.x = 1
        self.root.animation_data_create().nla_tracks.new().mute = True
        self.assertTrue(any(issue.code == 'export_nla' for issue in self.adapter.prepare(self.root, bpy.context)))

    def test_muted_strip_blocks_export_without_changing_artist_state(self):
        action = bpy.data.actions.new('Artist muted clip')
        track = self.root.animation_data_create().nla_tracks.new()
        strip = track.strips.new('Muted clip', 1, action)
        strip.mute = True
        try:
            result = self.adapter.export(self.root, bpy.context, self.path)
            self.assertFalse(result.success)
            self.assertTrue(any(issue.code == 'export_nla' and issue.status == 'ERROR'
                                for issue in result.issues))
            self.assertFalse(self.path.exists())
            self.assertTrue(strip.mute)
            self.assertFalse(track.mute)
            self.assertIs(strip.action, action)
        finally:
            self.root.animation_data.nla_tracks.remove(track)
            bpy.data.actions.remove(action)

    def test_cancelled_operator_is_not_success(self):
        with patch('humanoid_blender.targets._export_gltf', return_value={'CANCELLED'}):
            result = self.adapter.export(self.root, bpy.context, self.path)
        self.assertFalse(result.success)
        self.assertTrue(any(issue.code == 'export_failed' for issue in result.issues))
