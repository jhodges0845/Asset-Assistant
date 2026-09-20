"""Compare adjacent control-face normals in the default pelvis region."""
import argparse,json,math,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args()
sys.path.insert(0,str(Path(a.source).resolve()))
from object_core.geometry.surface_human import generate_surface_human,SurfaceHumanSpec
part=generate_surface_human(SurfaceHumanSpec()).parts[0]
edges={};normals=[]
for index,face in enumerate(part.faces):
    normal=[0.,0.,0.]
    for i,j in zip(face,face[1:]+face[:1]):
        v,w=part.vertices[i],part.vertices[j]
        normal[0]+=(v[1]-w[1])*(v[2]+w[2])
        normal[1]+=(v[2]-w[2])*(v[0]+w[0])
        normal[2]+=(v[0]-w[0])*(v[1]+w[1])
        edges.setdefault(tuple(sorted((i,j))),[]).append(index)
    length=math.sqrt(sum(c*c for c in normal))
    normals.append(tuple(c/length for c in normal))
angles=[];locations=[]
for (i,j),faces in edges.items():
    if len(faces)!=2 or not all(88<=part.vertices[v][2]<=107 and abs(part.vertices[v][0])<22 for v in (i,j)):continue
    dot=sum(x*y for x,y in zip(normals[faces[0]],normals[faces[1]]))
    angle=math.degrees(math.acos(max(-1,min(1,dot))))
    angles.append(angle)
    locations.append((angle,part.vertices[i],part.vertices[j]))
angles.sort()
report={'outer_sharpest':sorted((v for v in locations if abs(v[1][0])>12),reverse=True)[:5],'front_sharpest':sorted((v for v in locations if v[1][1]>7),reverse=True)[:5],'sharpest_edges':sorted(locations,reverse=True)[:12],'region_cm':{'z':[88,107],'abs_x_max':22},'edge_count':len(angles),'p95_degrees':angles[int(.95*(len(angles)-1))],'maximum_degrees':max(angles),'edges_over_45_degrees':sum(v>45 for v in angles),'interpretation':'Control-face normal differences, not a realism score.'}
Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
