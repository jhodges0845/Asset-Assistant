# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise export readiness through registered Blender UI operators and real files."""
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from humanoid_blender.targets import get_adapter, is_ready
from humanoid_blender.materials import prepare_materials


@unittest.skipIf(bpy is None, 'requires Blender; use scripts/test_blender.py')
class ExportWorkflowTests(unittest.TestCase):
    def setUp(self):
        import humanoid_blender
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ('objects', 'meshes', 'armatures', 'collections', 'materials', 'images', 'actions')}
        self.scene = bpy.data.scenes.new('ExportWorkflowTest')
        bpy.context.window.scene = self.scene
        humanoid_blender.register()
        self.settings = self.scene.humanoid_settings
        self.temp = TemporaryDirectory()

    def tearDown(self):
        import humanoid_blender
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        humanoid_blender.unregister()
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)
        self.temp.cleanup()

    def generate(self, kind='box'):
        self.settings.object_type = kind
        self.settings.box_width_cm = 10
        self.settings.box_depth_cm = 20
        self.settings.box_height_cm = 30
        bpy.ops.humanoid.generate_blockout()
        return self.settings.target

    def test_validation_snapshot_gates_export_and_requires_explicit_refresh(self):
        root = self.generate()
        self.assertFalse(bpy.ops.humanoid.export_asset.poll())
        self.assertEqual(bpy.ops.humanoid.prepare_materials(), {'FINISHED'})
        self.assertFalse(bpy.ops.humanoid.export_asset.poll())
        bpy.ops.humanoid.validate_character()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        self.assertFalse(any(row.status in ('WARN', 'ERROR') for row in self.settings.validation_results))
        self.assertFalse(any(row.code == 'blockout' for row in self.settings.validation_results))
        mesh = root.children[0]
        mesh.data.materials.clear()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        bpy.ops.humanoid.validate_character()
        self.assertFalse(bpy.ops.humanoid.export_asset.poll())
        bpy.ops.humanoid.prepare_materials()
        self.assertFalse(bpy.ops.humanoid.export_asset.poll())
        bpy.ops.humanoid.validate_character()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        self.settings.asset_use = 'ANIMATED'
        self.assertFalse(bpy.ops.humanoid.export_asset.poll())
        self.settings.asset_use = 'STATIC'
        self.assertFalse(bpy.ops.humanoid.export_asset.poll())
        bpy.ops.humanoid.validate_character()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())

    def test_each_ui_target_exports_its_file_format(self):
        self.generate()
        bpy.ops.humanoid.prepare_materials()
        for key, extension, magic in (('GODOT', '.glb', b'glTF'),
                                      ('UNITY', '.fbx', b'Kaydara FBX Binary'),
                                      ('UNREAL', '.fbx', b'Kaydara FBX Binary'),
                                      ('CURA', '.stl', b'Object Generator')):
            self.settings.output_target = key
            bpy.ops.humanoid.validate_character()
            self.assertTrue(bpy.ops.humanoid.export_asset.poll(), key)
            path = Path(self.temp.name) / (key + extension)
            self.assertEqual(bpy.ops.humanoid.export_asset(filepath=str(path)), {'FINISHED'})
            self.assertTrue(path.read_bytes().startswith(magic))
            self.assertEqual(self.settings.last_export, str(path.resolve()))

    def test_cura_needs_geometry_but_not_materials_or_animation(self):
        root = self.generate()
        self.settings.output_target = 'CURA'
        self.settings.asset_use = 'ANIMATED'
        self.settings.require_textures = True
        bpy.ops.humanoid.validate_character()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        path = Path(self.temp.name) / 'box.stl'
        bpy.ops.humanoid.export_asset(filepath=str(path))
        data = path.read_bytes()
        count, = struct.unpack_from('<I', data, 80)
        self.assertEqual(count, 12)
        self.assertEqual(len(data), 84 + 50 * count)
        vertices = [struct.unpack_from('<12fH', data, 84 + index * 50)[3:12] for index in range(count)]
        height = max(v[i] for v in vertices for i in (2, 5, 8))
        self.assertAlmostEqual(height, 300, places=3)

        other = root.children[0].copy()
        other.data = other.data.copy()
        self.scene.collection.objects.link(other)
        other.parent = root
        other.location.x = 2
        bpy.ops.humanoid.validate_character()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        issues = get_adapter('CURA').prepare(root, bpy.context)
        shell_note = next(issue for issue in issues if issue.code == 'cura_solid')
        self.assertEqual(shell_note.status, 'INFO')

        multi_path = Path(self.temp.name) / 'two-shells.stl'
        self.assertEqual(bpy.ops.humanoid.export_asset(filepath=str(multi_path)), {'FINISHED'})
        multi_data = multi_path.read_bytes()
        multi_count, = struct.unpack_from('<I', multi_data, 80)
        self.assertEqual(multi_count, 24)

    def test_cura_rejects_open_mesh_and_uses_unit_scale(self):
        import bmesh
        from humanoid_blender.ui import HUMANOID_OT_export
        from types import SimpleNamespace
        root = self.generate()
        obj = root.children[0]
        self.scene.unit_settings.scale_length = 0.01
        self.settings.output_target = 'CURA'
        bpy.ops.humanoid.validate_character()
        path = Path(self.temp.name) / 'scaled.stl'
        bpy.ops.humanoid.export_asset(filepath=str(path))
        data = path.read_bytes()
        count, = struct.unpack_from('<I', data, 80)
        heights = [struct.unpack_from('<12fH', data, 84 + index * 50)[i]
                   for index in range(count) for i in (5, 8, 11)]
        self.assertAlmostEqual(max(heights), 3, places=4)
        bpy.ops.humanoid.validate_character()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[0]], context='FACES')
        bm.to_mesh(obj.data)
        bm.free()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        invalid_path = Path(self.temp.name) / 'invalid.stl'
        operator = SimpleNamespace(filepath=str(invalid_path), report=lambda *args: None)
        self.assertEqual(HUMANOID_OT_export.execute(operator, bpy.context), {'CANCELLED'})
        self.assertFalse(invalid_path.exists())
        self.assertFalse(bpy.ops.humanoid.export_asset.poll())

    def test_material_preparation_preserves_existing_and_shared_data(self):
        root = self.generate()
        obj = root.children[0]
        original = obj.data
        outside = obj.copy()
        self.scene.collection.objects.link(outside)
        outside.parent = None
        prepare_materials(root)
        self.assertIsNot(obj.data, original)
        self.assertIs(outside.data, original)
        self.assertEqual(len(outside.data.materials), 0)
        material = obj.data.materials[0]
        count = len(bpy.data.materials)
        prepare_materials(root)
        self.assertEqual(len(bpy.data.materials), count)
        self.assertIs(obj.data.materials[0], material)

    def test_procedural_material_requires_baking(self):
        root = self.generate()
        prepare_materials(root)
        material = root.children[0].data.materials[0]
        noise = material.node_tree.nodes.new('ShaderNodeTexNoise')
        shader = material.node_tree.nodes.get('Principled BSDF')
        material.node_tree.links.new(noise.outputs['Color'], shader.inputs['Base Color'])
        bpy.ops.humanoid.validate_character()
        self.assertFalse(bpy.ops.humanoid.export_asset.poll())
        self.assertTrue(any(issue.code == 'material_shader' for issue in get_adapter('GODOT', asset_use='STATIC').prepare(root, bpy.context)))

    def test_fbx_contains_skin_animation_and_only_scoped_objects(self):
        from io_scene_fbx import parse_fbx
        root = self.generate('human')
        bpy.ops.humanoid.add_basic_rig()
        bpy.ops.humanoid.generate_idle()
        bpy.ops.humanoid.prepare_materials()
        self.settings.asset_use = 'ANIMATED'
        outside = bpy.data.objects.new('MustNotExport', None)
        self.scene.collection.objects.link(outside)
        outside.select_set(True)
        action = bpy.data.actions.new('UnrelatedActionMustNotExport')
        selected = set(bpy.context.selected_objects)
        active = bpy.context.view_layer.objects.active
        for target in ('UNITY', 'UNREAL'):
            path = Path(self.temp.name) / (target + '.fbx')
            result = get_adapter(target).export(root, bpy.context, path)
            self.assertTrue(result.success, result.issues)
            tree, _ = parse_fbx.parse(str(path))
            elements = []
            def walk(element):
                elements.append(element)
                for child in element.elems:
                    walk(child)
            walk(tree)
            self.assertTrue(any(e.id == b'Deformer' and b'Skin' in e.props for e in elements))
            self.assertTrue(any(e.id == b'AnimationStack' for e in elements))
            self.assertFalse(any(b'MustNotExport' in value for e in elements for value in e.props if isinstance(value, bytes)))
            self.assertEqual(set(bpy.context.selected_objects), selected)
            self.assertEqual(bpy.context.view_layer.objects.active, active)

    def test_file_execution_revalidates_after_dialog_opens(self):
        from humanoid_blender.ui import HUMANOID_OT_export
        from types import SimpleNamespace
        root = self.generate()
        prepare_materials(root)
        bpy.ops.humanoid.validate_character()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        root.children[0].data.materials.clear()
        self.assertTrue(bpy.ops.humanoid.export_asset.poll())
        path = Path(self.temp.name) / 'invalid.glb'
        operator = SimpleNamespace(filepath=str(path), report=lambda *args: None)
        self.assertEqual(HUMANOID_OT_export.execute(operator, bpy.context), {'CANCELLED'})
        self.assertFalse(path.exists())

    def test_fbx_embeds_saved_texture_bytes(self):
        from io_scene_fbx import parse_fbx
        root = self.generate()
        prepare_materials(root)
        obj = root.children[0]
        obj.data.uv_layers.new()
        material = obj.data.materials[0]
        image = bpy.data.images.new('FBXTexture', width=8, height=8)
        image.pixels[0] = 0.5
        image.filepath_raw = str(Path(self.temp.name) / 'texture.png')
        image.file_format = 'PNG'
        image.save()
        node = material.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = image
        material.node_tree.links.new(node.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
        node.image = bpy.data.images.load(image.filepath_raw, check_existing=False)
        for target in ('UNITY', 'UNREAL'):
            result = get_adapter(target, asset_use='STATIC').export(root, bpy.context,
                Path(self.temp.name) / (target + '-textured.fbx'))
            self.assertTrue(result.success, result.issues)
            tree, _ = parse_fbx.parse(result.filepath)
            elements = []
            def walk(element):
                elements.append(element)
                for child in element.elems:
                    walk(child)
            walk(tree)
            self.assertTrue(any(e.id == b'Texture' for e in elements))
            self.assertTrue(any(e.id == b'Content' and e.props and e.props[0] for e in elements))

    def test_fbx_rejects_action_outside_export_range(self):
        root = self.generate('human')
        bpy.ops.humanoid.add_basic_rig()
        bpy.ops.humanoid.generate_idle()
        bpy.ops.humanoid.prepare_materials()
        self.scene.frame_start = 500
        self.scene.frame_end = 600
        for target in ('UNITY', 'UNREAL'):
            issues = get_adapter(target).prepare(root, bpy.context)
            self.assertFalse(is_ready(issues))
            self.assertTrue(any(issue.code == 'fbx_animation_range' for issue in issues))
