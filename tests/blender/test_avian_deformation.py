# SPDX-License-Identifier: GPL-3.0-or-later
"""Real Blender deformation checks for the connected Avian surface."""

import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from object_core.objects import get_provider
from blender_adapter.adapter import create_character


@unittest.skipIf(bpy is None, "requires Blender; use scripts/test_blender.py")
class AvianDeformationTests(unittest.TestCase):
    def setUp(self):
        self.scene = bpy.data.scenes.new("AvianDeformationTest")
        self.previous_scene = bpy.context.window.scene
        bpy.context.window.scene = self.scene
        self.objects_before = set(bpy.data.objects)
        self.meshes_before = set(bpy.data.meshes)
        self.armatures_before = set(bpy.data.armatures)
        self.collections_before = set(bpy.data.collections)

        provider = get_provider("avian")
        values = {field.key: field.default for field in provider.parameters}
        mesh = provider.mesh(values)
        skeleton = provider.skeleton(values)
        weights = provider.skin_weights(mesh, values)
        self.root = create_character(
            mesh,
            name="AvianDeformation",
            scene=self.scene,
            skeleton=skeleton,
            skin_weights=weights,
        )
        self.rig = next(obj for obj in self.root.children if obj.type == "ARMATURE")
        self.avian = next(obj for obj in self.root.children if obj.type == "MESH")

    def tearDown(self):
        bpy.context.window.scene = self.previous_scene
        for obj in set(bpy.data.objects) - self.objects_before:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in set(bpy.data.meshes) - self.meshes_before:
            bpy.data.meshes.remove(mesh)
        for collection in set(bpy.data.collections) - self.collections_before:
            bpy.data.collections.remove(collection)
        for armature in set(bpy.data.armatures) - self.armatures_before:
            bpy.data.armatures.remove(armature)
        bpy.data.scenes.remove(self.scene)

    def _evaluated_points(self):
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        evaluated = self.avian.evaluated_get(graph)
        return [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]

    def _indices_weighted_to(self, bone_name, minimum=0.12):
        group = self.avian.vertex_groups.get(bone_name)
        self.assertIsNotNone(group, bone_name)
        indices = []
        for vertex in self.avian.data.vertices:
            try:
                weight = group.weight(vertex.index)
            except RuntimeError:
                continue
            if weight >= minimum:
                indices.append(vertex.index)
        self.assertTrue(indices, bone_name)
        return indices

    def _assert_bone_bends_surface(self, bone_name, axis="x", angle=0.35):
        before = self._evaluated_points()
        indices = self._indices_weighted_to(bone_name)
        pose_bone = self.rig.pose.bones[bone_name]
        pose_bone.rotation_mode = "XYZ"
        setattr(pose_bone.rotation_euler, axis, angle)
        after = self._evaluated_points()
        movement = [(after[index] - before[index]).length for index in indices]
        self.assertGreater(max(movement), 0.003, bone_name)
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()

    def test_major_avian_junctions_deform_when_bent(self):
        for bone_name, axis in (
            ("wing.upper.left", "x"),
            ("wing.lower.left", "x"),
            ("leg.upper.left", "x"),
            ("leg.lower.left", "x"),
            ("foot.left", "x"),
            ("tail.1", "x"),
            ("tail.2", "x"),
            ("neck", "x"),
            ("head", "x"),
        ):
            with self.subTest(bone=bone_name):
                self._assert_bone_bends_surface(bone_name, axis)

    def test_wing_motion_stays_local_to_its_side(self):
        before = self._evaluated_points()
        target = self._indices_weighted_to("wing.upper.left", minimum=0.20)
        opposite = self._indices_weighted_to("wing.lower.right", minimum=0.20)
        bone = self.rig.pose.bones["wing.upper.left"]
        bone.rotation_mode = "XYZ"
        bone.rotation_euler.x = 0.40
        after = self._evaluated_points()
        target_move = max((after[index] - before[index]).length for index in target)
        opposite_move = max((after[index] - before[index]).length for index in opposite)
        self.assertGreater(target_move, 0.003)
        self.assertLess(opposite_move, target_move * 0.20)

    def test_leg_motion_stays_local_to_its_side(self):
        before = self._evaluated_points()
        target = self._indices_weighted_to("leg.upper.left", minimum=0.20)
        opposite = self._indices_weighted_to("leg.lower.right", minimum=0.20)
        bone = self.rig.pose.bones["leg.upper.left"]
        bone.rotation_mode = "XYZ"
        bone.rotation_euler.x = 0.40
        after = self._evaluated_points()
        target_move = max((after[index] - before[index]).length for index in target)
        opposite_move = max((after[index] - before[index]).length for index in opposite)
        self.assertGreater(target_move, 0.003)
        self.assertLess(opposite_move, target_move * 0.20)

    def test_isolated_wing_bends_leave_all_nonwing_vertices_stationary(self):
        provider = get_provider('avian')
        defaults = {f.key: f.default for f in provider.parameters}
        for values in (defaults, dict(defaults, body_length_cm=55, body_width_cm=22,
                                      body_height_cm=28, wingspan_cm=140, tail_length_cm=35)):
            mesh = provider.mesh(values)
            anatomy = provider.anatomy(values)
            root = create_character(mesh, scene=self.scene, skeleton=provider.skeleton(values),
                                    skin_weights=provider.skin_weights(mesh, values))
            self.rig = next(o for o in root.children if o.type == 'ARMATURE')
            self.avian = next(o for o in root.children if o.type == 'MESH')
            for side in ('left', 'right'):
                owned = set(next(r.vertex_indices for r in anatomy.regions if r.name == 'wing.' + side))
                for segment, axis in (('upper', 'x'), ('lower', 'z')):
                    with self.subTest(values=values, side=side, segment=segment):
                        before = self._evaluated_points()
                        bone = self.rig.pose.bones['wing.' + segment + '.' + side]
                        bone.rotation_mode = 'XYZ'
                        setattr(bone.rotation_euler, axis, .7)
                        after = self._evaluated_points()
                        self.assertGreater(max((after[i] - before[i]).length for i in owned), .003)
                        self.assertLess(max((after[i] - before[i]).length for i in range(len(before))
                                            if i not in owned), 1e-7)
                        bone.rotation_euler = (0, 0, 0)
                        bpy.context.view_layer.update()

    def test_neutral_surface_has_no_nonadjacent_crossings(self):
        from scripts.avian_review_metrics import surface_crossings
        provider = get_provider('avian')
        defaults = {f.key: f.default for f in provider.parameters}
        for values in (defaults, dict(defaults, body_length_cm=55, body_width_cm=22,
                                      body_height_cm=28, wingspan_cm=140, tail_length_cm=35)):
            with self.subTest(values=values):
                part = provider.mesh(values).parts[0]
                self.assertEqual(surface_crossings(part.vertices, part.faces), [])

    def test_surface_crossing_diagnostic_detects_crossing_and_ignores_adjacency(self):
        from scripts.avian_review_metrics import surface_crossings
        vertices = ((-1, -1, 0), (1, -1, 0), (0, 1, 0),
                    (0, 0, -1), (0, 0, 1), (.5, 0, 0))
        self.assertEqual(surface_crossings(vertices, ((0, 1, 2), (3, 4, 5))), [(0, 1)])
        self.assertEqual(surface_crossings(vertices, ((0, 1, 2), (0, 3, 4))), [])
        separated = vertices[:3] + tuple((x + 5, y, z) for x, y, z in vertices[3:])
        self.assertEqual(surface_crossings(separated, ((0, 1, 2), (3, 4, 5))), [])

    def test_coordinated_fold_reduces_span_without_moving_body_or_legs(self):
        from scripts.render_avian_review import review_part
        provider = get_provider('avian')
        defaults = {f.key: f.default for f in provider.parameters}
        for values in (defaults, dict(defaults, body_length_cm=55, body_width_cm=22,
                                      body_height_cm=28, wingspan_cm=140, tail_length_cm=35)):
            with self.subTest(values=values):
                part, report = review_part(values, 'wing-fold')
                spans = report['wing_span_cm']
                self.assertLess(spans['posed'], spans['neutral'] * .65)
                movement = report['region_max_displacement_cm']
                for region in ('body', 'leg.left', 'leg.right'):
                    self.assertLess(movement[region], .00001)
                self.assertAlmostEqual(movement['wing.left'], movement['wing.right'], places=5)
                self.assertEqual(len(report['rotations']), 4)
                for foot in report['feet'].values():
                    self.assertLess(abs(foot['minimum_z_cm']), 1e-5)
                    self.assertEqual(foot['ground_vertex_count'], 15)
                    self.assertGreater(foot['contact_width_cm'], .5)
                    self.assertGreater(foot['contact_length_cm'], 1)

    def test_wing_root_blends_with_spine_instead_of_hinging_as_a_rigid_seam(self):
        wing_group = self.avian.vertex_groups.get("wing.upper.left")
        spine_group = self.avian.vertex_groups.get("spine")
        self.assertIsNotNone(wing_group)
        self.assertIsNotNone(spine_group)
        shared = []
        for vertex in self.avian.data.vertices:
            try:
                wing_weight = wing_group.weight(vertex.index)
                spine_weight = spine_group.weight(vertex.index)
            except RuntimeError:
                continue
            if wing_weight > 0.05 and spine_weight > 0.05:
                shared.append(vertex.index)
        self.assertTrue(shared, "left wing root should have shared spine/wing influence")


if __name__ == "__main__":
    unittest.main()
