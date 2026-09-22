# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from unittest.mock import patch

from object_core.objects import (
    AvianProvider as RegistryAvianProvider,
    BoxProvider as RegistryBoxProvider,
    HumanProvider as RegistryHumanProvider,
    HumanoidProvider as RegistryHumanoidProvider,
    Parameter as RegistryParameter,
    QuadrupedProvider as RegistryQuadrupedProvider,
    get_provider,
)
from object_core.providers import (
    AvianProvider,
    BoxProvider,
    HumanProvider,
    HumanoidProvider,
    Parameter,
    QuadrupedProvider,
)


class ProviderBoundaryTests(unittest.TestCase):
    def test_registry_reexports_existing_provider_symbols(self):
        self.assertIs(RegistryParameter, Parameter)
        self.assertIs(RegistryAvianProvider, AvianProvider)
        self.assertIs(RegistryBoxProvider, BoxProvider)
        self.assertIs(RegistryHumanoidProvider, HumanoidProvider)
        self.assertIs(RegistryHumanProvider, HumanProvider)
        self.assertIs(RegistryQuadrupedProvider, QuadrupedProvider)

    def test_human_v2_uses_mathematical_surface_geometry(self):
        human = get_provider("human")
        from object_core.geometry.surface_human_builder import HumanSurfaceBuilder
        surface = HumanSurfaceBuilder()
        human_mesh = human.mesh({"height_cm": 175, "weight_kg": 95, "body_type": "average"})
        surface_mesh = surface.mesh({
            "height_cm": 175,
            "shoulder_scale": 1.0,
            "hip_scale": 1.0,
            "waist_scale": 1.0,
            "chest_fullness": 0.55,
            "muscle_definition": 0.45,
        })
        self.assertEqual(human_mesh.parts[0].vertices, surface_mesh.parts[0].vertices)
        self.assertEqual(human_mesh.parts[0].faces, surface_mesh.parts[0].faces)

    def test_human_v2_reuses_immutable_mesh_for_identical_height(self):
        human = get_provider("human")
        values = {"height_cm": 180, "weight_kg": 95, "body_type": "average"}
        first = human.mesh(values)
        second = human.mesh(dict(values))
        self.assertIs(first, second)

    def test_human_v2_reuses_immutable_skinning_for_base_mesh(self):
        human = get_provider("human")
        values = {"height_cm": 180, "weight_kg": 95, "body_type": "average"}
        mesh = human.mesh(values)
        first_skeleton = human.skeleton(values)
        second_skeleton = human.skeleton(dict(values))
        first_weights = human.skin_weights(mesh, values)
        second_weights = human.skin_weights(mesh, dict(values))
        self.assertIs(first_skeleton, second_skeleton)
        self.assertIs(first_weights, second_weights)

    def test_human_v2_honors_full_height_range_and_shape_controls(self):
        human = get_provider("human")
        values = {"height_cm": 175, "weight_kg": 95, "body_type": "average"}
        neutral = human.mesh(values)
        for height in (120, 240):
            mesh = human.mesh(dict(values, height_cm=height))
            zs = [v[2] for v in mesh.parts[0].vertices]
            self.assertAlmostEqual(max(zs) - min(zs), height)
        for changed in (dict(values, weight_kg=60), dict(values, body_type="muscular")):
            self.assertNotEqual(neutral.parts[0].vertices, human.mesh(changed).parts[0].vertices)
            self.assertEqual(neutral.parts[0].faces, human.mesh(changed).parts[0].faces)
            self.assertNotEqual(human.skeleton(values), human.skeleton(changed))

    def test_human_v2_rig_follows_surface_arm_and_leg_centerlines(self):
        human = get_provider("human")
        bones = {b.name: b for b in human.skeleton(
            {"height_cm": 175, "weight_kg": 95, "body_type": "average"}).bones}
        self.assertAlmostEqual(bones["forearm.left"].tail[0], 30.8)
        self.assertAlmostEqual(bones["lower_leg.left"].tail[0], 18.7)
        self.assertGreater(bones["lower_leg.left"].tail[0], bones["upper_leg.left"].head[0])
        for name in ("upper_arm", "forearm", "hand", "upper_leg", "lower_leg", "foot"):
            left, right = bones[name + ".left"], bones[name + ".right"]
            self.assertEqual(left.head[1:], right.head[1:])
            self.assertEqual(left.tail[1:], right.tail[1:])
            self.assertAlmostEqual(left.head[0], -right.head[0])

    def test_edited_surface_recomputes_skin_weights(self):
        from object_core.models.mesh import MeshPart, ObjectMesh
        human = get_provider("human")
        values = {"height_cm": 175, "weight_kg": 95, "body_type": "average"}
        part = human.mesh(values).parts[0]
        moved = ((part.vertices[0][0] + 1, *part.vertices[0][1:]),) + part.vertices[1:]
        edited = ObjectMesh((MeshPart(part.name, moved, part.faces, part.uvs),))
        with patch("object_core.providers.human.generate_skin_weights", return_value=()) as weights:
            human.skin_weights(edited, values)
        weights.assert_called_once()
        self.assertEqual(weights.call_args.args, (edited, human.skeleton(values)))
        self.assertTrue(callable(weights.call_args.kwargs["bone_filter"]))

    def test_surface_wrist_weights_cannot_pull_hip_or_torso(self):
        from object_core.providers.human import _neutral_surface_data
        human = get_provider("human")
        values = {"height_cm": 180, "weight_kg": 95, "body_type": "average"}
        mesh = human.mesh(values)
        weights = human.skin_weights(mesh, values)[0].vertices
        _, arms = _neutral_surface_data()
        owners = {index: side for side, indices in arms for index in indices}
        self.assertEqual(set(owners.values()), {"left", "right"})
        wrist_vertices = 0
        for index, influences in enumerate(weights):
            self.assertAlmostEqual(sum(w.weight for w in influences), 1.0)
            for influence in influences:
                if influence.bone_name.startswith(("hand.", "forearm.")):
                    self.assertIn(index, owners)
                    self.assertTrue(influence.bone_name.endswith("." + owners[index]))
                    wrist_vertices += influence.bone_name.startswith("hand.")
        self.assertGreater(wrist_vertices, 100)

    def test_registry_resolves_extracted_provider_implementations(self):
        self.assertIsInstance(get_provider("avian"), AvianProvider)
        self.assertIsInstance(get_provider("box"), BoxProvider)
        self.assertIsInstance(get_provider("humanoid"), HumanoidProvider)
        self.assertIsInstance(get_provider("human"), HumanProvider)
        self.assertIsInstance(get_provider("quadruped"), QuadrupedProvider)


if __name__ == "__main__":
    unittest.main()
