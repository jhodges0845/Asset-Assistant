# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core.objects import (
    AvianProvider as RegistryAvianProvider,
    BoxProvider as RegistryBoxProvider,
    HumanExperimentalProvider as RegistryHumanExperimentalProvider,
    HumanoidProvider as RegistryHumanoidProvider,
    Parameter as RegistryParameter,
    QuadrupedProvider as RegistryQuadrupedProvider,
    get_provider,
)
from object_core.providers import (
    AvianProvider,
    BoxProvider,
    HumanExperimentalProvider,
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
        self.assertIs(RegistryHumanExperimentalProvider, HumanExperimentalProvider)
        self.assertIs(RegistryQuadrupedProvider, QuadrupedProvider)

    def test_human_v2_uses_mathematical_surface_geometry(self):
        human = get_provider("human_experimental")
        surface = get_provider("human_surface_study")
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
        human = get_provider("human_experimental")
        values = {"height_cm": 180, "weight_kg": 95, "body_type": "average"}
        first = human.mesh(values)
        second = human.mesh(dict(values))
        self.assertIs(first, second)

    def test_registry_resolves_extracted_provider_implementations(self):
        self.assertIsInstance(get_provider("avian"), AvianProvider)
        self.assertIsInstance(get_provider("box"), BoxProvider)
        self.assertIsInstance(get_provider("humanoid"), HumanoidProvider)
        self.assertIsInstance(get_provider("human_experimental"), HumanExperimentalProvider)
        self.assertIsInstance(get_provider("quadruped"), QuadrupedProvider)


if __name__ == "__main__":
    unittest.main()
