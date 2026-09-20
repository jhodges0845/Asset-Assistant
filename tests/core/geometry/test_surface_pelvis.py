# SPDX-License-Identifier: GPL-3.0-or-later
import math
import unittest
from object_core.geometry.surface_pelvis import refine_pelvic_planes, fair_pelvic_patch
from object_core.geometry.surface_human import SurfaceHumanSpec, generate_surface_human


class SurfacePelvisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.part=generate_surface_human(SurfaceHumanSpec()).parts[0]

    def test_fairing_is_bounded_and_preserves_distant_vertices(self):
        points=[(0,.2,.99),(.1,0,.99),(-.1,0,.99),(0,0,1.4)]
        result=fair_pelvic_patch(points,[(0,1,2),(1,2,3)])
        self.assertEqual(len(result),len(points))
        self.assertEqual(result[3],points[3])
        self.assertNotEqual(result[0],points[0])
        self.assertLessEqual(max(math.dist(a,b) for a,b in zip(points,result)),.0200000001)

    def test_pelvis_has_no_large_control_face_normal_jumps(self):
        part=self.part;edges={};normals=[]
        for index,face in enumerate(part.faces):
            normal=[0.,0.,0.]
            for a,b in zip(face,face[1:]+face[:1]):
                v,w=part.vertices[a],part.vertices[b]
                normal[0]+=(v[1]-w[1])*(v[2]+w[2])
                normal[1]+=(v[2]-w[2])*(v[0]+w[0])
                normal[2]+=(v[0]-w[0])*(v[1]+w[1])
                edges.setdefault(tuple(sorted((a,b))),[]).append(index)
            length=math.sqrt(sum(c*c for c in normal))
            normals.append(tuple(c/length for c in normal))
        angles=[]
        for edge,faces in edges.items():
            if len(faces)!=2 or not all(88<=part.vertices[i][2]<=107 and abs(part.vertices[i][0])<22 for i in edge):continue
            dot=sum(a*b for a,b in zip(normals[faces[0]],normals[faces[1]]))
            angles.append(math.degrees(math.acos(max(-1,min(1,dot)))))
        self.assertTrue(angles)
        self.assertLess(max(angles),45.)

    def test_relief_is_local_symmetric_and_preserves_x_z(self):
        points=[(.082,-.12,.965),(-.082,-.12,.965),(0,.1,1.3),(0,-.1,.7)]
        result=refine_pelvic_planes(points)
        self.assertEqual(result[2:],points[2:])
        self.assertLess(result[0][1],points[0][1])
        self.assertEqual(result[0][1],result[1][1])
        for before,after in zip(points,result):
            self.assertEqual((before[0],before[2]),(after[0],after[2]))

    def test_pelvis_no_long_abdomen_to_thigh_fan_edges(self):
        part=self.part
        lengths=[]
        for face in part.faces:
            if all(88<=part.vertices[i][2]<=100 for i in face):
                for a,b in zip(face,face[1:]+face[:1]):
                    lengths.append(math.dist(part.vertices[a],part.vertices[b]))
        self.assertTrue(lengths)
        self.assertLess(max(lengths),5.0)
