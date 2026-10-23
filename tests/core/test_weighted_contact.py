# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import random
import unittest
from types import SimpleNamespace as NS
from object_core.animation.weighted_contact import LimbSurface

class ContactEnvelopeTests(unittest.TestCase):
    def test_reduction_matches_exhaustive_weighted_surface_in_arbitrary_poses(self):
        vertices=tuple((0.,y/5,z/5) for y in range(-20,21) for z in range(21))
        rows=tuple((NS(bone_name='upper',weight=.25),NS(bone_name='foot',weight=.75))
                   if y<0 else (NS(bone_name='lower',weight=.4),NS(bone_name='foot',weight=.6))
                   for _,y,z in vertices)
        weights=NS(vertices=rows)
        bones=tuple(NS(name=n,head=h) for n,h in (('upper',(0.,0.,8.)),('lower',(0.,0.,4.)),('foot',(0.,0.,1.))))
        surface=LimbSurface(NS(parts=(NS(vertices=vertices),)),weights,NS(vertex_indices=tuple(range(len(vertices)))),bones,.5)
        exhaustive=copy.copy(surface)
        names={b.name:i for i,b in enumerate(bones)}
        exhaustive.rows=tuple(tuple((names[w.bone_name],w.weight,y*w.weight,z*w.weight) for w in row)
                              for (_,y,z),row in zip(vertices,rows))
        self.assertLess(len(surface.rows),len(exhaustive.rows)/10)
        rng=random.Random(173)
        for _ in range(100):
            angles=(rng.uniform(-2,2),rng.uniform(-2,2))
            surface.paw_pitch=exhaustive.paw_pitch=rng.uniform(-1,1)
            surface.crouch=exhaustive.crouch=rng.uniform(0,2)
            for a,b in zip(surface.measure(angles),exhaustive.measure(angles)):
                self.assertAlmostEqual(a,b,places=11)
