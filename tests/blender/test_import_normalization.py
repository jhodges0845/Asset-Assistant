# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.animation_records import has_animation_record
from blender_adapter.asset_file_import_ui import _IMPORT_GROUP_KEY, _IMPORT_ROOT_KEY, _IMPORT_SOURCE_KEY
from blender_adapter.asset_inspection_ui import inspect_selected_asset
from blender_adapter.import_normalization import enroll_imported_working_asset, normalized_import_root


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class ImportedWorkingAssetNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.before_objects = set(bpy.data.objects)
        self.before_meshes = set(bpy.data.meshes)
        self.before_armatures = set(bpy.data.armatures)
        self.before_actions = set(bpy.data.actions)
        self.before_collections = set(bpy.data.collections)
        self.scene = bpy.data.scenes.new("ImportNormalizationTest")
        bpy.context.window.scene = self.scene

    def tearDown(self):
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for action in set(bpy.data.actions) - self.before_actions:
            bpy.data.actions.remove(action)
        for obj in set(bpy.data.objects) - self.before_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in set(bpy.data.meshes) - self.before_meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for armature in set(bpy.data.armatures) - self.before_armatures:
            if armature.users == 0:
                bpy.data.armatures.remove(armature)
        for collection in set(bpy.data.collections) - self.before_collections:
            if collection.users == 0:
                bpy.data.collections.remove(collection)

    def _importer_shape(self):
        collection = bpy.data.collections.new("ImportedFile")
        self.scene.collection.children.link(collection)
        armature_data = bpy.data.armatures.new("ImportedRig.Data")
        rig = bpy.data.objects.new("ImportedRig", armature_data)
        collection.objects.link(rig)
        mesh_data = bpy.data.meshes.new("ImportedBody.Data")
        mesh_data.from_pydata(((-1, 0, 0), (1, 0, 0), (0, 1, 0)), (), ((0, 1, 2),))
        mesh = bpy.data.objects.new("ImportedBody", mesh_data)
        collection.objects.link(mesh)
        modifier = mesh.modifiers.new(name="Armature", type="ARMATURE")
        modifier.object = rig
        return collection, rig, mesh

    def test_canonical_root_preserves_top_level_world_transforms_and_internal_links(self):
        _collection, rig, mesh = self._importer_shape()
        rig.location.x = 2.5
        mesh.location.y = -1.5
        rig_world = rig.matrix_world.copy()
        mesh_world = mesh.matrix_world.copy()

        class _ImportUi:
            _IMPORT_GROUP_KEY = _IMPORT_GROUP_KEY
            _IMPORT_ROOT_KEY = _IMPORT_ROOT_KEY
            _IMPORT_SOURCE_KEY = _IMPORT_SOURCE_KEY

        root = normalized_import_root((rig, mesh), "GLB", _ImportUi)

        self.assertEqual("EMPTY", root.type)
        self.assertTrue(root[_IMPORT_ROOT_KEY])
        self.assertEqual("GLB", root[_IMPORT_SOURCE_KEY])
        self.assertEqual(root[_IMPORT_GROUP_KEY], rig[_IMPORT_GROUP_KEY])
        self.assertEqual(root[_IMPORT_GROUP_KEY], mesh[_IMPORT_GROUP_KEY])
        self.assertIs(rig.parent, root)
        self.assertIs(mesh.parent, root)
        self.assertEqual(rig_world, rig.matrix_world)
        self.assertEqual(mesh_world, mesh.matrix_world)
        self.assertIs(mesh.modifiers[0].object, rig)

    def test_import_is_reorganized_into_one_asset_collection(self):
        importer_collection, rig, mesh = self._importer_shape()
        importer_collection_name = importer_collection.name

        class _ImportUi:
            _IMPORT_GROUP_KEY = _IMPORT_GROUP_KEY
            _IMPORT_ROOT_KEY = _IMPORT_ROOT_KEY
            _IMPORT_SOURCE_KEY = _IMPORT_SOURCE_KEY

        root = normalized_import_root((rig, mesh), "GLB", _ImportUi)

        # The importer collection is intentionally removed during normalization, so
        # keep its name before the call instead of dereferencing removed Blender RNA.
        self.assertIsNone(bpy.data.collections.get(importer_collection_name))
        self.assertEqual(1, len(root.users_collection))
        asset_collection = root.users_collection[0]
        self.assertEqual(root.name, asset_collection.name)
        self.assertEqual({root, rig, mesh}, set(asset_collection.objects))
        self.assertEqual((asset_collection,), tuple(rig.users_collection))
        self.assertEqual((asset_collection,), tuple(mesh.users_collection))

    def test_enrollment_assigns_current_asset_rig_identity_and_imported_action(self):
        _collection, rig, mesh = self._importer_shape()

        class _ImportUi:
            _IMPORT_GROUP_KEY = _IMPORT_GROUP_KEY
            _IMPORT_ROOT_KEY = _IMPORT_ROOT_KEY
            _IMPORT_SOURCE_KEY = _IMPORT_SOURCE_KEY

        root = normalized_import_root((rig, mesh), "GLB", _ImportUi)
        action = bpy.data.actions.new("Walk")
        rig.animation_data_create()
        rig.animation_data.action = action
        report = inspect_selected_asset(root)

        enrolled = enroll_imported_working_asset(bpy.context, report)

        self.assertIs(enrolled, root)
        self.assertTrue(root.get("asset_assistant_external_asset"))
        self.assertTrue(root.get("asset_assistant_asset_id"))
        self.assertEqual("ANIMATED", root.get("asset_assistant_external_capability"))
        self.assertTrue(rig.get("asset_assistant_rig_id"))
        self.assertTrue(has_animation_record(action))
        settings = getattr(self.scene, "humanoid_settings", None)
        if settings is not None:
            self.assertIs(settings.target, root)
            self.assertEqual("ANIMATED", settings.asset_use)


if __name__ == "__main__":
    unittest.main()
