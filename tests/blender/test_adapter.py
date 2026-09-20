# SPDX-License-Identifier: GPL-3.0-or-later
"""Real Blender integration tests; skipped by ordinary Python discovery."""

import unittest
from unittest.mock import patch

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from object_core import BodyType, HumanoidSpec, generate_mesh, generate_proportions, generate_skeleton
from humanoid_blender.adapter import create_character


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class BlenderAdapterTests(unittest.TestCase):
    def setUp(self):
        self.scene = bpy.data.scenes.new("AdapterTest")
        self.objects_before = set(bpy.data.objects)
        self.meshes_before = set(bpy.data.meshes)
        self.armatures_before = set(bpy.data.armatures)
        self.collections_before = set(bpy.data.collections)
        self.mesh = generate_mesh(generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE)))

    def tearDown(self):
        for obj in set(bpy.data.objects) - self.objects_before:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in set(bpy.data.meshes) - self.meshes_before:
            bpy.data.meshes.remove(mesh)
        for collection in set(bpy.data.collections) - self.collections_before:
            bpy.data.collections.remove(collection)
        for data in set(bpy.data.armatures) - self.armatures_before:
            bpy.data.armatures.remove(data)
        bpy.data.scenes.remove(self.scene)

    def test_editable_parts_match_source_and_scene_units(self):
        for scale in (1.0, 0.01):
            self.scene.unit_settings.scale_length = scale
            root = create_character(self.mesh, scene=self.scene)
            self.assertEqual(root.type, "EMPTY")
            self.assertEqual(len(root.children), 15)
            parts = {obj["body_part"]: obj for obj in root.children}
            for source in self.mesh.parts:
                obj = parts[source.name]
                self.assertEqual(obj.type, "MESH")
                self.assertEqual(tuple(tuple(face.vertices) for face in obj.data.polygons), source.faces)
                self.assertFalse(obj.data.validate())
                for actual, expected in zip(obj.data.vertices, source.vertices):
                    for coordinate, value in zip(actual.co, expected):
                        self.assertAlmostEqual(coordinate * scale, value * 0.01, places=5)
                self.assertEqual(tuple(obj.scale), (1, 1, 1))
            self.assertAlmostEqual(self.scene.unit_settings.scale_length, scale)

    def test_repeated_generation_preserves_existing_objects(self):
        first = create_character(self.mesh, scene=self.scene)
        first_names = {obj.name for obj in first.children}
        second = create_character(self.mesh, scene=self.scene)
        self.assertNotEqual(first.name, second.name)
        self.assertTrue(first_names.isdisjoint({obj.name for obj in second.children}))
        self.assertEqual(len(first.children), 15)
        self.assertEqual(len(self.scene.collection.children), 2)
        self.assertTrue(self.objects_before.issubset(set(bpy.data.objects)))

    def test_failed_creation_cleans_up_only_its_own_data(self):
        import humanoid_blender.adapter as adapter
        first = create_character(self.mesh, scene=self.scene)
        before = (set(bpy.data.objects), set(bpy.data.meshes), set(bpy.data.collections))
        real_populate = adapter._populate_mesh
        calls = [0]

        def fail_second_mesh(*args):
            calls[0] += 1
            if calls[0] == 2:
                raise RuntimeError("injected mesh creation failure")
            return real_populate(*args)

        with patch.object(adapter, "_populate_mesh", side_effect=fail_second_mesh):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                create_character(self.mesh, scene=self.scene)
        self.assertEqual(before, (set(bpy.data.objects), set(bpy.data.meshes), set(bpy.data.collections)))
        self.assertEqual(len(first.children), 15)

    def test_registration_and_sidebar_operator(self):
        import humanoid_blender
        previous_scene = bpy.context.window.scene
        bpy.context.window.scene = self.scene
        humanoid_blender.register()
        try:
            self.assertEqual(self.scene.humanoid_settings.object_type, "human_experimental")
            options = self.scene.humanoid_settings.bl_rna.properties["object_type"].enum_items
            self.assertEqual(
                [(item.identifier, item.name) for item in options],
                [("human_experimental", "Human"),
                 ("box", "Box"),
                 ("quadruped", "Quadruped"),
                 ("avian", "Avian"),
                 ("human_surface_study", "Mathematical Human")],
            )
            self.assertEqual(bpy.types.HUMANOID_PT_panel.bl_label, "Asset Assistant")
            self.assertEqual(bpy.types.HUMANOID_PT_panel.bl_category, "Asset Assistant")
            self.assertEqual(bpy.types.HUMANOID_PT_panel.bl_order, 0)
            self.assertTrue(getattr(bpy.types.HUMANOID_PT_panel.draw, "_asset_assistant_workspace", False))
            for panel_name in (
                    'ASSET_ASSISTANT_PT_modify',
                    'HUMANOID_PT_rigging',
                    'HUMANOID_PT_animations',
                    'HUMANOID_PT_validation',
                    'HUMANOID_PT_export'):
                panel = getattr(bpy.types, panel_name)
                self.assertTrue(panel.is_registered)
                self.assertEqual(panel.bl_category, "Asset Assistant")
                self.assertFalse(panel.poll(bpy.context))
            tabs = self.scene.humanoid_settings.bl_rna.properties["workflow_tab"].enum_items
            self.assertEqual([tab.identifier for tab in tabs], ["MODEL", "RIGGING", "ANIMATION", "VALIDATION", "EXPORT"])
            workspace_tabs = self.scene.humanoid_settings.bl_rna.properties["asset_assistant_workspace"].enum_items
            self.assertEqual([tab.identifier for tab in workspace_tabs], ["CREATE", "ANIMATE", "COMPONENTS", "EXPORT"])
            self.scene.cursor.location = (2, 3, 4)
            for preset in BodyType:
                self.scene.humanoid_settings.human_experimental_body_type = preset.value
                self.assertEqual(bpy.ops.humanoid.generate_blockout(), {"FINISHED"})
                model = bpy.context.view_layer.objects.active
                self.assertEqual(model.type, "EMPTY")
                self.assertEqual(len(model.children), 1)
                meshes_before_rig = {obj.data for obj in model.children}
                self.assertEqual(self.scene.humanoid_settings.target, model)
                self.scene.humanoid_settings.workflow_tab = "RIGGING"
                self.assertEqual(bpy.ops.humanoid.add_basic_rig(), {"FINISHED"})
                armature = bpy.context.view_layer.objects.active
                self.assertEqual(armature.type, "ARMATURE")
                root = armature.parent
                self.assertEqual(root, model)
                self.assertEqual({obj.data for obj in root.children if obj.type == "MESH"}, meshes_before_rig)
                self.assertEqual(root["object_type"], "human_experimental")
                self.assertEqual(root["body_type"], preset.value)
                self.assertEqual(tuple(root.location), (2, 3, 4))
                self.assertEqual(len([obj for obj in root.children if obj.type == "MESH"]), 1)
            self.assertEqual(bpy.ops.humanoid.generate_blockout(), {"FINISHED"})
            unrigged = bpy.context.view_layer.objects.active
            self.assertEqual(unrigged.type, "EMPTY")
            self.assertEqual(len(unrigged.children), 1)
            self.assertTrue(all(obj.type == "MESH" for obj in unrigged.children))
            self.scene.humanoid_settings.workflow_tab = "VALIDATION"
            self.assertEqual(bpy.ops.humanoid.validate_character(), {"FINISHED"})
            self.assertTrue(any(row.code == "rig" and row.status == "ERROR"
                                for row in self.scene.humanoid_settings.validation_results))
            self.scene.humanoid_settings.asset_use = "STATIC"
            self.assertEqual(len(self.scene.humanoid_settings.validation_results), 0)
            self.assertTrue(bpy.types.HUMANOID_PT_panel.is_registered)
            generated_objects = set(self.scene.objects)
            generated_meshes = {obj.data for obj in self.scene.objects if obj.type == "MESH"}
        finally:
            humanoid_blender.unregister()
            bpy.context.window.scene = previous_scene
        self.assertFalse(hasattr(bpy.types.Scene, "humanoid_settings"))
        for panel_name in ('HUMANOID_PT_panel', 'ASSET_ASSISTANT_PT_modify', 'HUMANOID_PT_rigging',
                           'HUMANOID_PT_animations', 'HUMANOID_PT_validation', 'HUMANOID_PT_export'):
            self.assertFalse(hasattr(bpy.types, panel_name))
        self.assertEqual(set(self.scene.objects), generated_objects)
        self.assertTrue(generated_meshes.issubset(set(bpy.data.meshes)))
        humanoid_blender.register()
        humanoid_blender.unregister()

    def test_quadruped_generates_and_rigs_through_generic_blender_workflow(self):
        import humanoid_blender
        previous_scene = bpy.context.window.scene
        bpy.context.window.scene = self.scene
        humanoid_blender.register()
        try:
            settings = self.scene.humanoid_settings
            settings.object_type = "quadruped"
            settings.quadruped_body_length_cm = 82
            settings.quadruped_shoulder_height_cm = 61
            self.scene.cursor.location = (1, 2, 3)

            self.assertEqual(bpy.ops.humanoid.generate_blockout(), {"FINISHED"})
            root = settings.target
            self.assertEqual(root.type, "EMPTY")
            self.assertEqual(root["object_type"], "quadruped")
            self.assertEqual(root["body_length_cm"], 82)
            self.assertEqual(root["shoulder_height_cm"], 61)
            self.assertEqual(tuple(root.location), (1, 2, 3))
            meshes = [obj for obj in root.children if obj.type == "MESH"]
            self.assertEqual(len(meshes), 1)
            self.assertEqual(meshes[0]["body_part"], "quadruped")
            self.assertEqual(settings.asset_use, "RIGGED")

            self.assertTrue(bpy.ops.humanoid.add_basic_rig.poll())
            self.assertEqual(bpy.ops.humanoid.add_basic_rig(), {"FINISHED"})
            rig = next(obj for obj in root.children if obj.type == "ARMATURE")
            self.assertEqual(rig.parent, root)
            self.assertIn("spine", rig.data.bones)
            self.assertIn("fore_upper.left", rig.data.bones)
            self.assertIn("hind_lower.right", rig.data.bones)
            self.assertIn("tail.3", rig.data.bones)
            for obj in meshes:
                self.assertEqual(len(obj.modifiers), 1)
                self.assertIs(obj.modifiers[0].object, rig)
                self.assertGreater(len(obj.vertex_groups), 0)

            settings.animation_clip = "IDLE"
            self.assertTrue(bpy.ops.humanoid.select_animation_clip.poll())
            settings.animation_clip = "WALK"
            self.assertTrue(bpy.ops.humanoid.select_animation_clip.poll())
        finally:
            humanoid_blender.unregister()
            bpy.context.window.scene = previous_scene

    def test_rig_rest_pose_and_limb_movement(self):
        previous_scene = bpy.context.window.scene
        bpy.context.window.scene = self.scene
        try:
            skeleton = generate_skeleton(generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE)))
            for scale in (1.0, 0.01):
                self.scene.unit_settings.scale_length = scale
                root = create_character(self.mesh, scene=self.scene, skeleton=skeleton)
                root.location = (2, 3, 4)
                rig = next(obj for obj in root.children if obj.type == "ARMATURE")
                parts = {obj["body_part"]: obj for obj in root.children if obj.type == "MESH"}
                self.assertEqual(len(rig.data.bones), 16)
                for bone in skeleton.bones:
                    actual = rig.data.bones[bone.name]
                    self.assertEqual(actual.parent.name if actual.parent else None, bone.parent)
                    for a, b in zip(actual.head_local, bone.head):
                        self.assertAlmostEqual(a * scale, b * 0.01, places=5)
                bpy.context.view_layer.update()
                graph = bpy.context.evaluated_depsgraph_get()

                def evaluated_points(obj):
                    evaluated = obj.evaluated_get(graph)
                    return [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]

                for obj in parts.values():
                    self.assertEqual(len(obj.vertex_groups), 1)
                    self.assertEqual(len(obj.modifiers), 1)
                    self.assertIs(obj.modifiers[0].object, rig)
                    for actual, vertex in zip(evaluated_points(obj), obj.data.vertices):
                        self.assertLess((actual - obj.matrix_world @ vertex.co).length * scale, 1e-5)
                        self.assertEqual(obj.vertex_groups[0].weight(vertex.index), 1.0)
                hand_before = evaluated_points(parts['hand.left'])
                torso_before = evaluated_points(parts['torso'])
                rig.pose.bones['upper_arm.left'].rotation_mode = 'XYZ'
                rig.pose.bones['upper_arm.left'].rotation_euler.z = 0.5
                bpy.context.view_layer.update()
                hand_after = evaluated_points(parts['hand.left'])
                self.assertGreater((hand_after[0] - hand_before[0]).length * scale, 0.01)
                self.assertLess((evaluated_points(parts['torso'])[0] - torso_before[0]).length, 1e-5)
                self.assertAlmostEqual((hand_before[1] - hand_before[0]).length * scale,
                                       (hand_after[1] - hand_after[0]).length * scale, places=5)
        finally:
            bpy.context.window.scene = previous_scene

    def test_rig_failure_cleans_up_and_restores_context(self):
        import humanoid_blender.rigging as rigging
        previous_scene = bpy.context.window.scene
        bpy.context.window.scene = self.scene
        skeleton = generate_skeleton(generate_proportions(HumanoidSpec(180, 95, BodyType.AVERAGE)))
        before = (set(bpy.data.objects), set(bpy.data.meshes), set(bpy.data.armatures), set(bpy.data.collections))
        try:
            with patch.object(rigging, '_populate_bones', side_effect=RuntimeError('injected rig failure')):
                with self.assertRaisesRegex(RuntimeError, 'injected'):
                    create_character(self.mesh, scene=self.scene, skeleton=skeleton)
            self.assertEqual(before, (set(bpy.data.objects), set(bpy.data.meshes),
                                      set(bpy.data.armatures), set(bpy.data.collections)))
            self.assertEqual(bpy.context.mode, 'OBJECT')
        finally:
            bpy.context.window.scene = previous_scene
