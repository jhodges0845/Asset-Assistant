# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from object_core.modification import SemanticOperation
from object_core.objects import get_provider


class AvianSemanticGeometryTests(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider("avian")
        self.values = {field.key: field.default for field in self.provider.parameters}

    def test_hooked_beak_preserves_topology_and_changes_forward_geometry(self):
        base = self.provider.mesh(self.values)
        operation = SemanticOperation(
            "shape", "beak", (("profile", "hooked"), ("amount", 0.9)),
        )
        patched = self.provider.semantic_mesh(base, self.values, (operation,))
        self.assertEqual(base.face_count, patched.face_count)
        self.assertEqual(base.vertex_count, patched.vertex_count)
        self.assertEqual(base.parts[0].faces, patched.parts[0].faces)
        self.assertNotEqual(base.parts[0].vertices, patched.parts[0].vertices)

    def test_semantic_operations_compose_in_order(self):
        base = self.provider.mesh(self.values)
        operations = (
            SemanticOperation("shape", "beak", (("profile", "hooked"), ("amount", 0.7))),
            SemanticOperation("shape", "chest", (("profile", "powerful"), ("amount", 0.8))),
            SemanticOperation("shape", "wing.left", (("profile", "broad"), ("amount", 0.6))),
            SemanticOperation("shape", "wing.right", (("profile", "broad"), ("amount", 0.6))),
            SemanticOperation("shape", "tail", (("profile", "fan"), ("amount", 0.5))),
        )
        patched = self.provider.semantic_mesh(base, self.values, operations)
        self.assertEqual(base.parts[0].faces, patched.parts[0].faces)
        self.assertNotEqual(base.bounds_cm, patched.bounds_cm)

    def test_powerful_chest_preserves_authored_wings_and_legs(self):
        for changes in ({}, dict(body_length_cm=65,body_width_cm=24,body_height_cm=30,
                                 wingspan_cm=145,tail_length_cm=35)):
            values = dict(self.values, **changes)
            base = self.provider.mesh(values)
            regions = self.provider.anatomy(values).regions
            body = set(next(r.vertex_indices for r in regions if r.name == 'body'))
            for amount in (0., .6, 1.5):
                with self.subTest(values=changes, amount=amount):
                    operation = SemanticOperation('shape','chest',(('profile','powerful'),('amount',amount)))
                    result = self.provider.semantic_mesh(base, values, (operation,))
                    before, after = base.parts[0], result.parts[0]
                    self.assertEqual(before.faces, after.faces)
                    self.assertEqual(before.uvs, after.uvs)
                    for index in range(len(before.vertices)):
                        if index not in body:
                            self.assertEqual(before.vertices[index], after.vertices[index])
                    movement = sum(abs(a-b) for i in body
                                   for a,b in zip(before.vertices[i],after.vertices[i]))
                    if amount:
                        self.assertGreater(movement, .1)
                    else:
                        self.assertLess(movement, 1e-10)

    def test_powerful_chest_rejects_changed_topology(self):
        from object_core.models import MeshPart, ObjectMesh
        part = self.provider.mesh(self.values).parts[0]
        changed = ObjectMesh((MeshPart(part.name,part.vertices,part.faces[:-1]),))
        operation = SemanticOperation('shape','chest',(('profile','powerful'),))
        with self.assertRaisesRegex(ValueError,'authored topology'):
            self.provider.semantic_mesh(changed,self.values,(operation,))

    def test_scale_operation_rejects_extreme_values(self):
        base = self.provider.mesh(self.values)
        operation = SemanticOperation("scale", "head", (("factor", 12.0),))
        with self.assertRaisesRegex(ValueError, "scale must be between"):
            self.provider.semantic_mesh(base, self.values, (operation,))

    def test_unknown_profile_is_rejected_in_provider_owned_layer(self):
        base = self.provider.mesh(self.values)
        operation = SemanticOperation("shape", "beak", (("profile", "dragon"),))
        with self.assertRaisesRegex(ValueError, "Unsupported Avian semantic profile"):
            self.provider.semantic_mesh(base, self.values, (operation,))


if __name__ == "__main__":
    unittest.main()
