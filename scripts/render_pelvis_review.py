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
VIEWS=(("Front",0.0),("3/4",-45.0),("Side",-90.0),("Back",180.0)); MODES=("clay","silhouette","wireframe")
def args():
 p=argparse.ArgumentParser(); p.add_argument("--output",default="pelvis_review.png"); p.add_argument("--modes",nargs="+",choices=MODES,default=list(MODES)); p.add_argument("--width",type=float,default=34.0); p.add_argument("--depth",type=float,default=24.0); p.add_argument("--height",type=float,default=20.0); p.add_argument("--hip-fullness",type=float,default=1.0); p.add_argument("--glute-projection",type=float,default=1.0); p.add_argument("--crotch-width",type=float,default=7.0); p.add_argument("--thigh-spacing",type=float,default=4.0); av=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []; return p.parse_args(av)
def clear(): bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
def look(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
def mat(): m=bpy.data.materials.new("Pelvis Review"); m.use_nodes=True; return m
def config(m,mode):
 n=m.node_tree.nodes; n.clear(); out=n.new("ShaderNodeOutputMaterial")
 if mode=="clay":
  sh=n.new("ShaderNodeBsdfPrincipled"); sh.inputs["Base Color"].default_value=(.92,.92,.90,1); sh.inputs["Roughness"].default_value=.78; sh.inputs["Metallic"].default_value=0.0; m.node_tree.links.new(sh.outputs["BSDF"],out.inputs["Surface"])
 elif mode=="silhouette": sh=n.new("ShaderNodeEmission"); sh.inputs["Color"].default_value=(.03,.035,.045,1); sh.inputs["Strength"].default_value=1.0; m.node_tree.links.new(sh.outputs["Emission"],out.inputs["Surface"])
 else:
  sh=n.new("ShaderNodeEmission"); wire=n.new("ShaderNodeWireframe"); wire.use_pixel_size=True; wire.inputs["Size"].default_value=1.25; ramp=n.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position=.40; ramp.color_ramp.elements[0].color=(.88,.88,.86,1); ramp.color_ramp.elements[1].position=.60; ramp.color_ramp.elements[1].color=(.04,.045,.055,1); m.node_tree.links.new(wire.outputs["Fac"],ramp.inputs["Fac"]); m.node_tree.links.new(ramp.outputs["Color"],sh.inputs["Color"]); m.node_tree.links.new(sh.outputs["Emission"],out.inputs["Surface"])
def main():
 a=args(); clear(); shape=NeutralPelvisShape(width=a.width,depth=a.depth,height=a.height,hip_fullness=a.hip_fullness,glute_projection=a.glute_projection,crotch_width=a.crotch_width,thigh_spacing=a.thigh_spacing); verts,faces,_=generate_neutral_pelvis(shape); material=mat()
 min_x=min(v[0] for v in verts); max_x=max(v[0] for v in verts); min_y=min(v[1] for v in verts); max_y=max(v[1] for v in verts); min_z=min(v[2] for v in verts); max_z=max(v[2] for v in verts); c=Vector(((min_x+max_x)*.5,(min_y+max_y)*.5,(min_z+max_z)*.5)); cv=tuple((x-c.x,y-c.y,z-c.z) for x,y,z in verts); h=max_z-min_z
 widths=[]
 for _,angle in VIEWS:
  r=math.radians(angle); ca=math.cos(r); sa=math.sin(r); px=[x*ca-y*sa for x,y,_ in cv]; widths.append(max(px)-min(px))
 # Use each view's own width when laying out the diagnostic strip. This keeps all
 # four views visible while wasting much less frame space than max-width slots.
 gutter=max(2.5,max(widths)*.09); total=sum(widths)+gutter*3; cursor=-total*.5; xs=[]
 for w in widths:
  xs.append(cursor+w*.5); cursor+=w+gutter
 for (name,angle),x in zip(VIEWS,xs):
  mesh=bpy.data.meshes.new(name+"Mesh"); mesh.from_pydata(cv,[],faces); mesh.update(); obj=bpy.data.objects.new("Pelvis "+name,mesh); bpy.context.collection.objects.link(obj); obj.location=(x,0,0); obj.rotation_euler.z=math.radians(angle); obj.data.materials.append(material)
 scene=bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.device="CPU"; scene.cycles.samples=32; scene.cycles.use_denoising=True; scene.render.resolution_x=1800; scene.render.resolution_y=900; scene.render.resolution_percentage=100; scene.render.image_settings.file_format="PNG"; scene.view_settings.look="AgX - Medium High Contrast"; scene.view_settings.exposure=.35
 world=scene.world or bpy.data.worlds.new("Pelvis World"); scene.world=world; world.use_nodes=True; bg=world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(.42,.45,.49,1); bg.inputs["Strength"].default_value=.8
 # At 2:1 resolution ortho_scale is the vertical span and twice that horizontally.
 # Fit the full strip with modest margins and make the pelvis occupy most of the image.
 scale=max(h*1.18,(total/2.0)*1.04); camd=bpy.data.cameras.new("Camera"); camd.type="ORTHO"; camd.ortho_scale=scale; cam=bpy.data.objects.new("Camera",camd); bpy.context.collection.objects.link(cam); cam.location=(0,-150,0); look(cam,(0,0,0)); scene.camera=cam
 # Broad, frontal studio illumination. The purpose is shape diagnosis, not drama:
 # no region of the clay should disappear into shadow.
 for name,energy,size,loc,target in (("Key",5000,90,(-45,-75,60),(0,0,0)),("Fill",4200,100,(45,-65,35),(0,0,0)),("Top",3200,100,(0,-25,85),(0,0,0)),("Under",2600,90,(0,-35,-55),(0,0,0)),("Back Fill",2200,100,(0,55,35),(0,0,0))):
  ld=bpy.data.lights.new(name,"AREA"); ld.energy=energy; ld.size=size; ob=bpy.data.objects.new(name,ld); bpy.context.collection.objects.link(ob); ob.location=loc; look(ob,target)
 out=Path(a.output); out=out if out.is_absolute() else REPO_ROOT/out; out.parent.mkdir(parents=True,exist_ok=True)
 for mode in a.modes:
  config(material,mode); target=out if mode=="clay" else out.with_name(out.stem+"_"+mode+out.suffix); scene.render.filepath=os.fspath(target); bpy.ops.render.render(write_still=True); print("Pelvis review",mode,"written to",target)
if __name__=="__main__": main()
