# SPDX-License-Identifier: GPL-3.0-or-later
"""FBX export regression coverage for generated in-memory textures."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_asset
from blender_adapter.materials import prepare_materials
from blender_adapter.targets import get_adapter
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, 'requires Blender; use scripts/test_blender.py')
class FBXGeneratedTextureTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ('objects', 'meshes', 'armatures', 'collections', 'materials', 'images', 'actions')}
        self.scene = bpy.data.scenes.new('FBXGeneratedTextureTest')
        bpy.context.window.scene = self.scene
        provider = get_provider('human')
        values = {field.key: field.default for field in provider.parameters}
        self.root = create_asset(provider.mesh(values), name='FBXHuman', scene=self.scene)
        self.root['object_type'] = provider.key
        for key, value in values.items():
            self.root[key] = value
        prepare_materials(self.root)

    def tearDown(self):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)

    def _generated_image(self):
        for obj in self.root.children:
            if obj.type != 'MESH':
                continue
            for slot in obj.material_slots:
                material = slot.material
                if material is None or not material.use_nodes:
                    continue
                shader = material.node_tree.nodes.get('Principled BSDF')
                if shader is None or not shader.inputs['Base Color'].is_linked:
                    continue
                node = shader.inputs['Base Color'].links[0].from_node
                if node.type == 'TEX_IMAGE' and node.image is not None:
                    return node.image
        self.fail('generated Human texture not found')

    def test_unity_validation_allows_generated_texture_and_export_stages_it(self):
        image = self._generated_image()
        self.assertTrue(image.get('asset_assistant_generated_texture', False))
        self.assertTrue(image.packed_file or getattr(image, 'packed_files', ()))
        original_path = image.filepath_raw
        original_format = image.file_format
        adapter = get_adapter('UNITY', asset_use='STATIC')

        issues = adapter.prepare(self.root, bpy.context)
        self.assertFalse(any(issue.code == 'fbx_texture' and issue.status == 'ERROR' for issue in issues))
        self.assertTrue(any(issue.code == 'fbx_texture' and issue.status == 'INFO' for issue in issues))

        with TemporaryDirectory() as directory:
            output = Path(directory) / 'human.fbx'
            result = adapter.export(self.root, bpy.context, output)
            self.assertTrue(result.success, result.issues)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

        self.assertEqual(image.filepath_raw, original_path)
        self.assertEqual(image.file_format, original_format)
        self.assertTrue(image.packed_file or getattr(image, 'packed_files', ()))
