# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core.geometry.anatomical_pelvis import pelvis_ring, pelvic_transition_ring, upper_thigh_ring


class AnatomicalPelvisProfileTests(unittest.TestCase):
    def test_pelvis_profile_is_symmetric_and_non_planar(self):
        ring=pelvis_ring(90.0,34.0,24.0,16.0)
        self.assertEqual(len(ring),16)
        rounded={(round(x,6),round(y,6),round(z,6)) for x,y,z in ring}
        for x,y,z in tuple(rounded): self.assertIn((round(-x,6),y,z),rounded)
        self.assertGreater(max(v[2] for v in ring)-min(v[2] for v in ring),2.0)

    def test_transition_ring_fades_but_keeps_pelvic_shape(self):
        pelvis=pelvis_ring(90.0,34.0,24.0,16.0)
        transition=pelvic_transition_ring(100.0,30.0,21.0,16.0)
        self.assertEqual(len(transition),16)
        self.assertGreater(max(v[2] for v in transition)-min(v[2] for v in transition),0.5)
        self.assertLess(max(v[2] for v in transition)-min(v[2] for v in transition),max(v[2] for v in pelvis)-min(v[2] for v in pelvis))

    def test_upper_thigh_inherits_pelvic_volume_then_can_fade_to_neutral(self):
        center=(9.0,0.0,75.0)
        root=upper_thigh_ring(center,17.0,16.0,"left",1.0)
        neutral=upper_thigh_ring(center,17.0,16.0,"left",0.0)
        self.assertEqual(len(root),16); self.assertEqual(len(neutral),16)
        self.assertGreater(max(v[0] for v in root),max(v[0] for v in neutral))
        self.assertLess(min(v[1] for v in root),min(v[1] for v in neutral))

    def test_left_and_right_thigh_profiles_mirror(self):
        left=upper_thigh_ring((9.0,0.0,75.0),17.0,16.0,"left",.8)
        right=upper_thigh_ring((-9.0,0.0,75.0),17.0,16.0,"right",.8)
        left_set={(round(-x,6),round(y,6),round(z,6)) for x,y,z in left}
        right_set={(round(x,6),round(y,6),round(z,6)) for x,y,z in right}
        self.assertEqual(left_set,right_set)


if __name__=="__main__": unittest.main()
