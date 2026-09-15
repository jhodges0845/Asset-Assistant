# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the standalone Human V2 neutral-pelvis prototype.

Usage:
  blender --background --factory-startup --python scripts/render_pelvis_review.py -- --output pelvis_review.png
"""
from __future__ import annotations
import argparse, math, os, sys
from pathlib import Path
import bpy
from mathutils import Vector

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path: sys.path.insert(0, str(REPO_ROOT))
from object_core.geometry.neutral_pelvis import NeutralPelvisShape, generate_neutral_pelvis

VIEWS=(("Front",0.0),("3/4",-45.0),("Side",-90.0),("Back",180.0))
MODES=("clay","silhouette","wireframe")

def args():
    p=argparse.ArgumentParser(); p.add_argument("--output",default="pelvis_review.png"); p.add_argument("--modes",nargs="+",choices=MODES,default=list(MODES));
    p.add_argument("--width",type=float,default=34.0); p.add_argument("--depth",type=float,default=24.0); p.add_argument("--height",type=float,default=20.0)
    p.add_argument("--hip-fullness",type=float,default=1.0); p.add_argument("--glute-projection",type=float,default=1.0); p.add_argument("--crotch-width",type=float,default=7.0); p.add_argument("--thigh-spacing",type=float,default=4.0)
    av=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []; return p.parse_args(av)

def clear(): bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
def look(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
def mat():
    m=bpy.data.materials.new("Pelvis Review"); m.use_nodes=True; return m
def config(m,mode):
    n=m.node_tree.nodes; n.clear(); out=n.new("ShaderNodeOutputMaterial")
    if mode=="clay":
        sh=n.new("ShaderNodeBsdfPrincipled")
        sh.inputs["Base Color"].default_value=(.72,.74,.77,1)
        sh.inputs["Roughness"].default_value=.72
        m.node_tree.links.new(sh.outputs["BSDF"],out.inputs["Surface"])
    elif mode=="silhouette": sh=n.new("ShaderNodeEmission"); sh.inputs["Color"].default_value=(.95,.95,.95,1); sh.inputs["Strength"].default_value=1.0; m.node_tree.links.new(sh.outputs["Emission"],out.inputs["Surface"])
    else:
        sh=n.new("ShaderNodeEmission"); wire=n.new("ShaderNodeWireframe"); wire.use_pixel_size=True; wire.inputs["Size"].default_value=1.25; ramp=n.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position=.40; ramp.color_ramp.elements[0].color=(.055,.065,.08,1); ramp.color_ramp.elements[1].position=.60; ramp.color_ramp.elements[1].color=(.94,.94,.94,1); m.node_tree.links.new(wire.outputs["Fac"],ramp.inputs["Fac"]); m.node_tree.links.new(ramp.outputs["Color"],sh.inputs["Color"]); m.node_tree.links.new(sh.outputs["Emission"],out.inputs["Surface"])
def main():
    a=args(); clear(); shape=NeutralPelvisShape(width=a.width,depth=a.depth,height=a.height,hip_fullness=a.hip_fullness,glute_projection=a.glute_projection,crotch_width=a.crotch_width,thigh_spacing=a.thigh_spacing); verts,faces,_=generate_neutral_pelvis(shape); material=mat()

    min_x=min(v[0] for v in verts); max_x=max(v[0] for v in verts)
    min_y=min(v[1] for v in verts); max_y=max(v[1] for v in verts)
    min_z=min(v[2] for v in verts); max_z=max(v[2] for v in verts)
    mesh_center=Vector(((min_x+max_x)*.5,(min_y+max_y)*.5,(min_z+max_z)*.5))
    centered_verts=tuple((x-mesh_center.x,y-mesh_center.y,z-mesh_center.z) for x,y,z in verts)
    mesh_height=max_z-min_z

    # Compute the exact projected width for every diagnostic angle.  Using a
    # circular radius here made each slot much wider than the pelvis actually is,
    # which pushed the outer views beyond the camera frame.
    projected_widths=[]
    for _,angle in VIEWS:
        r=math.radians(angle); ca=math.cos(r); sa=math.sin(r)
        projected_x=[x*ca-y*sa for x,y,_ in centered_verts]
        projected_widths.append(max(projected_x)-min(projected_x))
    max_view_width=max(projected_widths)
    gutter=max(4.0,max_view_width*.16)
    spacing=max_view_width+gutter
    xs=(-1.5*spacing,-.5*spacing,.5*spacing,1.5*spacing)

    for (name,angle),x in zip(VIEWS,xs):
        mesh=bpy.data.meshes.new(name+"Mesh"); mesh.from_pydata(centered_verts,[],faces); mesh.update(); obj=bpy.data.objects.new("Pelvis "+name,mesh); bpy.context.collection.objects.link(obj)
        obj.location=(x,0,0); obj.rotation_mode="XYZ"; obj.rotation_euler.z=math.radians(angle); obj.data.materials.append(material)

    scene=bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.device="CPU"; scene.cycles.samples=48; scene.cycles.use_denoising=True; scene.render.resolution_x=1800; scene.render.resolution_y=900; scene.render.resolution_percentage=100; scene.render.image_settings.file_format="PNG"
    scene.view_settings.look="AgX - Medium High Contrast"
    world=scene.world or bpy.data.worlds.new("Pelvis World"); scene.world=world; world.use_nodes=True; bg=world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(.12,.14,.17,1); bg.inputs["Strength"].default_value=.55

    # Camera ortho_scale is the vertical span. At 2:1 resolution the horizontal
    # span is twice that value. Fit all four views from their actual projected
    # widths, with enough margin to inspect the outer silhouettes clearly.
    left_edge=xs[0]-projected_widths[0]*.5
    right_edge=xs[-1]+projected_widths[-1]*.5
    layout_width=right_edge-left_edge
    required_vertical=mesh_height*1.45
    required_horizontal=(layout_width/2.0)*1.12
    ortho_scale=max(required_vertical,required_horizontal)
    camd=bpy.data.cameras.new("Camera"); camd.type="ORTHO"; camd.ortho_scale=ortho_scale; cam=bpy.data.objects.new("Camera",camd); bpy.context.collection.objects.link(cam); cam.location=(0,-150,0); look(cam,(0,0,0)); scene.camera=cam

    # Bright neutral three-point lighting: diagnostic clay should reveal planes
    # and concavity without losing the underside/groin in near-black shadow.
    keyd=bpy.data.lights.new("Key","AREA"); keyd.energy=1800; keyd.size=70; key=bpy.data.objects.new("Key",keyd); bpy.context.collection.objects.link(key); key.location=(-55,-70,65); look(key,(0,0,0))
    filld=bpy.data.lights.new("Fill","AREA"); filld.energy=1250; filld.size=80; fill=bpy.data.objects.new("Fill",filld); bpy.context.collection.objects.link(fill); fill.location=(55,-55,25); look(fill,(0,0,0))
    rimd=bpy.data.lights.new("Rim","AREA"); rimd.energy=900; rimd.size=60; rim=bpy.data.objects.new("Rim",rimd); bpy.context.collection.objects.link(rim); rim.location=(0,45,55); look(rim,(0,0,0))
    underd=bpy.data.lights.new("Under Fill","AREA"); underd.energy=700; underd.size=65; under=bpy.data.objects.new("Under Fill",underd); bpy.context.collection.objects.link(under); under.location=(0,-35,-45); look(under,(0,0,-3))

    out=Path(a.output); out=out if out.is_absolute() else REPO_ROOT/out; out.parent.mkdir(parents=True,exist_ok=True)
    for mode in a.modes:
        config(material,mode); target=out if mode=="clay" else out.with_name(out.stem+"_"+mode+out.suffix); scene.render.filepath=os.fspath(target); bpy.ops.render.render(write_still=True); print("Pelvis review",mode,"written to",target)
if __name__=="__main__": main()
