# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from object_core.component_primitives import hair_shell_mesh
from object_core.providers.human import HumanProvider
from object_core.providers.human_hair import fit_parent_skinned_hair


class HumanHairTests(unittest.TestCase):
    def _skeleton(self):
        provider = HumanProvider()
        values = {field.key: field.default for field in provider.parameters}
        return provider.skeleton(values)

    def test_hair_is_fitted_near_human_head_and_weighted(self):
        source = hair_shell_mesh(back_length_cm=24.0)
        fitted, weights = fit_parent_skinned_hair(source, self._skeleton())

        self.assertEqual(source.vertex_count, fitted.vertex_count)
        self.assertEqual(1, len(weights))
        self.assertEqual(source.vertex_count, len(weights[0].vertices))
        self.assertGreater(fitted.bounds_cm[0][2], 100.0)
        for influences in weights[0].vertices:
            self.assertAlmostEqual(1.0, sum(item.weight for item in influences), places=6)

    def test_cap_is_head_driven_and_long_back_blends_lower_bones(self):
        source = hair_shell_mesh(back_length_cm=30.0)
        _fitted, weights = fit_parent_skinned_hair(source, self._skeleton())
        names_by_vertex = [set(item.bone_name for item in influences) for influences in weights[0].vertices]

        self.assertIn({"head"}, names_by_vertex)
        self.assertTrue(any("neck" in names for names in names_by_vertex))
        self.assertTrue(any("torso" in names for names in names_by_vertex))


if __name__ == "__main__":
    unittest.main()
