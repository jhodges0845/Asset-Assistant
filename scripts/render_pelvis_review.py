# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the standalone Human V2 neutral-pelvis prototype."""
from __future__ import annotations
import argparse, math, os, sys
from pathlib import Path
import bpy
from mathutils import Vector
REPO_ROOT=Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path: sys.path.insert(0,str(REPO_ROOT))
from object_core.geometry.neutral_pelvis import NeutralPelvisShape, generate_neutral_pelvis
# The constructor projects the glutes toward -Y; the fixed camera looks from -Y.
VIEWS=(("Front",180.0),("3/4",135.0),("Side",90.0),("Back",0.0)); MODES=("clay","silhouette","wireframe")
def args():
 p=argparse.ArgumentParser(); p.add_argument("--output",default="pelvis_review.png"); p.add_argument("--modes",nargs="+",choices=MODES,default=list(MODES)); p.add_argument("--width",type=float,default=34.0); p.add_argument("--depth",type=float,default=24.0); p.add_argument("--height",type=float,default=20.0); p.add_argument("--hip-fullness",type=float,default=1.0); p.add_argument("--glute-projection",type=float,default=1.0); p.add_argument("--crotch-width",type=float,default=7.0); p.add_argument("--thigh-spacing",type=float,default=4.0); av=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []; return p.parse_args(av)
def clear(): bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
def look(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
def mat(): m=bpy.data.materials.new("Pelvis Review"); m.use_nodes=True; return m
def config(m,mode):
 n=m.node_tree.nodes; n.clear(); out=n.new("ShaderNodeOutputMaterial")
 if mode=="clay":
  sh=n.new("ShaderNodeBsdfPrincipled"); sh.inputs["Base Color"].default_value=(.65,.67,.70,1); sh.inputs["Roughness"].default_value=.78; sh.inputs["Metallic"].default_value=0.0; m.node_tree.links.new(sh.outputs["BSDF"],out.inputs["Surface"])
 elif mode=="silhouette": sh=n.new("ShaderNodeEmission"); sh.inputs["Color"].default_value=(.95,.95,.95,1); sh.inputs["Strength"].default_value=1.0; m.node_tree.links.new(sh.outputs["Emission"],out.inputs["Surface"])
 else:
  sh=n.new("ShaderNodeEmission"); sh.inputs["Color"].default_value=(.88,.88,.86,1); m.node_tree.links.new(sh.outputs["Emission"],out.inputs["Surface"])

def main():
 a=args(); clear(); shape=NeutralPelvisShape(width=a.width,depth=a.depth,height=a.height,hip_fullness=a.hip_fullness,glute_projection=a.glute_projection,crotch_width=a.crotch_width,thigh_spacing=a.thigh_spacing); verts,faces,_=generate_neutral_pelvis(shape); material=mat()
 min_x=min(v[0] for v in verts); max_x=max(v[0] for v in verts); min_y=min(v[1] for v in verts); max_y=max(v[1] for v in verts); min_z=min(v[2] for v in verts); max_z=max(v[2] for v in verts); c=Vector(((min_x+max_x)*.5,(min_y+max_y)*.5,(min_z+max_z)*.5)); cv=tuple((x-c.x,y-c.y,z-c.z) for x,y,z in verts); h=max_z-min_z
 widths=[]; centers=[]
 for _,angle in VIEWS:
  r=math.radians(angle); ca=math.cos(r); sa=math.sin(r); px=[x*ca-y*sa for x,y,_ in cv]; widths.append(max(px)-min(px)); centers.append((max(px)+min(px))*.5)
 # Use each view's own width when laying out the diagnostic strip. This keeps all
 # four views visible while wasting much less frame space than max-width slots.
 gutter=max(2.5,max(widths)*.09); total=sum(widths)+gutter*3; cursor=-total*.5; xs=[]
 for w,center in zip(widths,centers):
  xs.append(cursor+w*.5-center); cursor+=w+gutter
 for (name,angle),x in zip(VIEWS,xs):
  mesh=bpy.data.meshes.new(name+"Mesh"); mesh.from_pydata(cv,[],faces); mesh.update(calc_edges=True)
  # Clay should diagnose the finished surface, not polygon-normal faceting. The
  # separate wireframe render still shows every authored control edge explicitly.
  for polygon in mesh.polygons: polygon.use_smooth=True
  obj=bpy.data.objects.new("Pelvis "+name,mesh); bpy.context.collection.objects.link(obj); obj.location=(x,0,0); obj.rotation_euler.z=math.radians(angle); obj.data.materials.append(material)
 # Draw authored mesh edges, not shader tessellation diagonals inside quads.
 edge_material=bpy.data.materials.new("Topology edges"); edge_material.use_nodes=True
 nodes=edge_material.node_tree.nodes; nodes.clear(); output=nodes.new("ShaderNodeOutputMaterial"); emission=nodes.new("ShaderNodeEmission"); emission.inputs["Color"].default_value=(.025,.03,.04,1); edge_material.node_tree.links.new(emission.outputs["Emission"],output.inputs["Surface"])
 edge_objects=[]
 for obj in tuple(bpy.context.scene.objects):
  if obj.type!="MESH": continue
  curve=bpy.data.curves.new(obj.name+" edges","CURVE"); curve.dimensions="3D"; curve.bevel_depth=h*.0035; curve.bevel_resolution=0; curve.resolution_u=1
  for edge in obj.data.edges:
   spline=curve.splines.new("POLY"); spline.points.add(1)
   for point,index in zip(spline.points,edge.vertices): point.co=(*obj.data.vertices[index].co,1.0)
  overlay=bpy.data.objects.new(obj.name+" edges",curve); bpy.context.collection.objects.link(overlay); overlay.location=obj.location; overlay.rotation_euler=obj.rotation_euler; curve.materials.append(edge_material); overlay.hide_render=True; edge_objects.append(overlay)
 scene=bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.device="CPU"; scene.cycles.samples=32; scene.cycles.use_denoising=True; scene.render.resolution_x=1800; scene.render.resolution_y=500; scene.render.resolution_percentage=100; scene.render.image_settings.file_format="PNG"; scene.view_settings.view_transform="AgX"; scene.view_settings.look="AgX - Medium High Contrast"; scene.view_settings.exposure=.35
 world=scene.world or bpy.data.worlds.new("Pelvis World"); scene.world=world; world.use_nodes=True; bg=world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(.42,.45,.49,1); bg.inputs["Strength"].default_value=.25
 # Separate the camera backdrop from ambient illumination so pale clay stays
 # legible without flattening the surface with an equally bright environment.
 camera_bg=world.node_tree.nodes.new("ShaderNodeBackground"); camera_bg.inputs["Color"].default_value=(.045,.055,.07,1)
 light_path=world.node_tree.nodes.new("ShaderNodeLightPath"); mix=world.node_tree.nodes.new("ShaderNodeMixShader")
 world.node_tree.links.new(light_path.outputs["Is Camera Ray"],mix.inputs[0]); world.node_tree.links.new(bg.outputs[0],mix.inputs[1]); world.node_tree.links.new(camera_bg.outputs[0],mix.inputs[2]); world.node_tree.links.new(mix.outputs[0],world.node_tree.nodes.get("World Output").inputs["Surface"])
 # Ask Blender for the actual frame: AUTO sensor fit uses the horizontal
 # span in a landscape render, not the vertical span assumed previously.
 camd=bpy.data.cameras.new("Camera"); camd.type="ORTHO"; camd.ortho_scale=1.0
 frame=camd.view_frame(scene=scene)
 frame_width=max(v.x for v in frame)-min(v.x for v in frame)
 frame_height=max(v.y for v in frame)-min(v.y for v in frame)
 camd.ortho_scale=max(total*1.08/frame_width,h*1.18/frame_height)
 cam=bpy.data.objects.new("Camera",camd); bpy.context.collection.objects.link(cam); cam.location=(0,-150,0); look(cam,(0,0,0)); scene.camera=cam
 # Fail before rendering if any diagnostic view would be clipped.
 from bpy_extras.object_utils import world_to_camera_view
 bpy.context.view_layer.update()
 for obj in (o for o in scene.objects if o.type=="MESH"):
  for vertex in obj.data.vertices:
   projected=world_to_camera_view(scene,cam,obj.matrix_world @ vertex.co)
   if not (0.0 < projected.x < 1.0 and 0.0 < projected.y < 1.0 and projected.z > 0):
    raise RuntimeError("Pelvis diagnostic view falls outside camera: "+obj.name)
 # Broad, frontal studio illumination. The purpose is shape diagnosis, not drama:
 # no region of the clay should disappear into shadow.
 for name,energy,size,loc,target in (("Key",5000,90,(-45,-75,60),(0,0,0)),("Fill",1500,100,(45,-65,35),(0,0,0)),("Top",2000,100,(0,-25,85),(0,0,0)),("Under",800,90,(0,-35,-55),(0,0,0)),("Back Fill",1600,100,(0,55,35),(0,0,0))):
  ld=bpy.data.lights.new(name,"AREA"); ld.energy=energy*8; ld.size=size; ob=bpy.data.objects.new(name,ld); bpy.context.collection.objects.link(ob); ob.location=loc; look(ob,target)
 out=Path(a.output); out=out if out.is_absolute() else REPO_ROOT/out; out.parent.mkdir(parents=True,exist_ok=True)
 for mode in a.modes:
  scene.cycles.use_denoising=mode=="clay"
  for overlay in edge_objects: overlay.hide_render=mode!="wireframe"
  config(material,mode); target=out if mode=="clay" else out.with_name(out.stem+"_"+mode+out.suffix); scene.render.filepath=os.fspath(target); bpy.ops.render.render(write_still=True); print("Pelvis review",mode,"written to",target)
if __name__=="__main__": main()
