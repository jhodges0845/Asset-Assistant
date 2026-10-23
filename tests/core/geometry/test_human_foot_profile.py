# SPDX-License-Identifier: GPL-3.0-or-later
"""Human foot shape, floor datum and rest-rig alignment regressions."""
import unittest
from math import sin, cos, pi
from unittest.mock import patch
from object_core.geometry.surface_human import (
    HUMAN_FOOT_FLOOR, human_foot_profile, generate_surface_human, _sample)


def legacy_foot_profile(t):
    return (-.006+.18*t, .09-.059*min(t/.24,1)-.003*t,
            _sample([(0,.022),(.20,.031),(.65,.045),(.95,.039),(1,.032)],t)[0],
            .026*(1-t)+.014*t, pi/2*min(1,t*2))


class HumanFootProfileTests(unittest.TestCase):
    def test_heel_ball_grounding_and_raised_instep(self):
        for t in (.25,.75):
            y,z,rx,ry,angle = human_foot_profile(t)
            self.assertAlmostEqual(z-ry*sin(angle), HUMAN_FOOT_FLOOR)
        for k in range(33):
            y,z,rx,ry,angle = human_foot_profile(k/32)
            self.assertGreaterEqual(z-ry*sin(angle), HUMAN_FOOT_FLOOR-1e-12)
        self.assertEqual(human_foot_profile(0)[:2], (.005,.09))
        _,z,_,ry,angle = human_foot_profile(.45)
        _,old_z,_,old_ry,old_angle = legacy_foot_profile(.45)
        self.assertGreater(z+ry*sin(angle),old_z+old_ry*sin(old_angle)+.015)

    def test_upper_contour_has_no_ankle_fold(self):
        rows = [human_foot_profile(k/128) for k in range(129)]
        top = [(y+r*cos(a), z+r*sin(a)) for y,z,x,r,a in rows]
        bottom = [y-r*cos(a) for y,z,x,r,a in rows]
        self.assertTrue(all(b[0] > a[0] and b[1] <= a[1] for a,b in zip(top,top[1:])))
        self.assertTrue(all(b > a for a,b in zip(bottom,bottom[1:])))

    def test_shorter_foot_preserves_topology_and_every_nonfoot_point(self):
        new = generate_surface_human().parts[0]
        with patch('object_core.geometry.surface_human.human_foot_profile', side_effect=legacy_foot_profile):
            old = generate_surface_human().parts[0]
        self.assertEqual(new.faces, old.faces)
        changed = 0
        for a,b in zip(old.vertices,new.vertices):
            if a[2] > 9.:
                for u,v in zip(a,b): self.assertAlmostEqual(u,v,places=10)
            elif a != b:
                changed += 1
        self.assertGreater(changed,1000)
        def length(part):
            points = [v for v in part.vertices if v[0]>0 and v[2]<9.]
            return max(v[1] for v in points)-min(v[1] for v in points)
        self.assertLess(length(new),length(old)*.95)
        self.assertAlmostEqual(min(v[2] for v in new.vertices),0.)

    def test_toe_bone_ends_at_surface_cap_center_for_body_controls(self):
        from object_core.providers import human
        for height,weight,body in ((180,95,'average'),(160,55,'average'),(200,120,'muscular')):
            mesh=human._human_mesh(height,weight,body).parts[0]
            anatomy=human._human_anatomy(height,weight,body)
            points={p.name:p.position for p in anatomy.landmarks}
            for side in ('left','right'):
                region=next(r for r in anatomy.regions if r.name=='leg.'+side)
                # Each authored leg ends in the cap center after all foot rings.
                cap=mesh.vertices[region.vertex_indices[-1]]
                for actual,expected in zip(cap,points['toe.'+side]):
                    self.assertAlmostEqual(actual,expected,places=9)
