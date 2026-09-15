# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core import BodyType, HumanoidSpec, generate_proportions
from object_core.geometry import generate_anatomical_human_mesh, is_closed_manifold
from object_core.proportions.landmarks import generate_landmarks

class AnatomicalHumanTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proportions=generate_proportions(HumanoidSpec(180,95,BodyType.AVERAGE)); cls.mesh=generate_anatomical_human_mesh(cls.proportions); cls.part=cls.mesh.parts[0]; cls.landmarks=generate_landmarks(cls.proportions)

    def test_generates_one_closed_symmetric_surface_with_uvs(self):
        self.assertEqual(len(self.mesh.parts),1); self.assertTrue(is_closed_manifold(self.part)); self.assertEqual(len(self.part.faces),len(self.part.uvs))
        for face,face_uvs in zip(self.part.faces,self.part.uvs): self.assertEqual(len(face),len(face_uvs))
        rounded={(round(x,6),round(y,6),round(z,6)) for x,y,z in self.part.vertices}
        for x,y,z in tuple(rounded): self.assertIn((round(-x,6),y,z),rounded)

    def test_torso_sections_are_constructed_with_sixteen_point_loops(self):
        hip_z=self.landmarks["hip_center"][2]; waist_z=hip_z+self.proportions.torso_length_cm*.35
        self.assertEqual(len([v for v in self.part.vertices if abs(v[2]-waist_z)<=1e-7]),16)

    def test_pelvis_boundary_is_an_anatomical_saddle_not_flat_belt(self):
        hip_z=self.landmarks["hip_center"][2]; p=self.proportions; window=p.thigh_thickness_cm*.25
        pelvic=[v for v in self.part.vertices if hip_z-window<=v[2]<=hip_z+window]
        lateral=[v for v in pelvic if abs(v[0])>p.hip_width_cm*.35]
        medial=[v for v in pelvic if abs(v[0])<p.hip_width_cm*.12]
        self.assertTrue(lateral); self.assertTrue(medial)
        self.assertGreater(max(v[2] for v in lateral),min(v[2] for v in medial))

    def test_pelvis_has_no_full_width_conversion_belts(self):
        hip_z=self.landmarks["hip_center"][2]
        # Human V2 previously inserted complete 16-vertex loops at both of these
        # offsets before splitting into the thighs.  Those circumferential belts
        # created the visible skirt/shelf in the diagnostic wireframe.
        for old_level in (hip_z-1.5,hip_z-3.8):
            self.assertLess(len([v for v in self.part.vertices if abs(v[2]-old_level)<=1e-7]),16)

    def test_pelvis_carries_rear_volume_into_upper_thigh(self):
        hip=self.landmarks["hip.left"]; knee=self.landmarks["knee.left"]
        z18=hip[2]+(knee[2]-hip[2])*.18; z52=hip[2]+(knee[2]-hip[2])*.52
        rear18=min(v[1] for v in self.part.vertices if abs(v[2]-z18)<=1e-7 and v[0]>0)
        rear52=min(v[1] for v in self.part.vertices if abs(v[2]-z52)<=1e-7 and v[0]>0)
        self.assertLess(rear18,rear52)

    def test_legs_have_anatomical_longitudinal_support_loops(self):
        hip=self.landmarks["hip.left"]; knee=self.landmarks["knee.left"]
        for fraction in (.18,.30,.52,.82):
            z=hip[2]+(knee[2]-hip[2])*fraction; ring=[v for v in self.part.vertices if abs(v[2]-z)<=1e-7 and v[0]>0]; self.assertEqual(len(ring),16)
        self.assertGreaterEqual(len([v for v in self.part.vertices if abs(v[2]-knee[2])<=1e-7 and v[0]>0]),16)

    def test_upper_thigh_transitions_from_hip_volume(self):
        hip=self.landmarks["hip.left"]; knee=self.landmarks["knee.left"]
        def span(f):
            z=hip[2]+(knee[2]-hip[2])*f; xs=[v[0] for v in self.part.vertices if abs(v[2]-z)<=1e-7 and v[0]>0]; return max(xs)-min(xs)
        self.assertGreater(span(.18),span(.52))

    def test_calf_belly_is_wider_than_lower_calf(self):
        knee=self.landmarks["knee.left"]; ankle=self.landmarks["ankle.left"]
        def span(f):
            z=knee[2]+(ankle[2]-knee[2])*f; xs=[v[0] for v in self.part.vertices if abs(v[2]-z)<=1e-7 and v[0]>0]; return max(xs)-min(xs)
        self.assertGreater(span(.55),span(.76))

    def test_neck_and_head_keep_legacy_eight_point_layout(self):
        shoulder_z=self.landmarks["shoulder_center"][2]; chin_z=self.landmarks["chin"][2]; neck_z=shoulder_z+(chin_z-shoulder_z)*.18
        self.assertEqual(len([v for v in self.part.vertices if abs(v[2]-neck_z)<=1e-7]),8)

    def test_standing_height_and_ground_are_preserved(self):
        zs=[v[2] for v in self.part.vertices]; self.assertAlmostEqual(min(zs),0.0); self.assertAlmostEqual(max(zs),self.proportions.standing_height_cm)

    def test_constructor_is_deterministic_across_supported_extremes(self):
        for height,body_type in ((120,BodyType.SLIM),(240,BodyType.OVERWEIGHT)):
            with self.subTest(height=height,body_type=body_type):
                p=generate_proportions(HumanoidSpec(height,95,body_type)); self.assertEqual(generate_anatomical_human_mesh(p),generate_anatomical_human_mesh(p))

    def test_requires_proportions(self):
        with self.assertRaises(TypeError): generate_anatomical_human_mesh(None)

if __name__=="__main__": unittest.main()
