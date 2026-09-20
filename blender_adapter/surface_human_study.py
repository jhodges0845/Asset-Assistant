# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender presentation for the opt-in mathematical Human provider."""
from array import array
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def _camera(scene,name,position,target,scale):
    data=bpy.data.cameras.new(name);data.type='ORTHO';data.ortho_scale=scale
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=position;_aim(obj,target);return obj


def _configure(scene,w,h):
    scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=8;scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    shading=scene.display.shading;shading.light='STUDIO';shading.studiolight_rotate_z=.5
    shading.color_type='MATERIAL';shading.show_shadows=True;shading.show_cavity=True
    shading.cavity_type='BOTH';shading.curvature_ridge_factor=1.2;shading.curvature_valley_factor=1.1
    shading.background_type='WORLD';shading.background_color=(.035,.042,.05)
    scene.world=bpy.data.worlds.new(scene.name+' world');scene.world.color=(.035,.042,.05);scene.world.use_nodes=True
    background=scene.world.node_tree.nodes.get('Background');background.inputs['Color'].default_value=(.12,.14,.17,1);background.inputs['Strength'].default_value=.5
    for name,position,power,size in [('Key',(-3,4,4),600,4),('Fill',(3,3,2),350,3),('Rim',(0,-3,3),500,3)]:
        data=bpy.data.lights.new(scene.name+name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        light=bpy.data.objects.new(scene.name+name,data);scene.collection.objects.link(light);light.location=position;_aim(light,(0,0,1))
    scene.view_settings.view_transform='Standard'


def validate_control_surface(part):
    """Shared intersection gate for plugin creation and standalone studies."""
    data=bpy.data.meshes.new('Surface validation temporary')
    try:
        data.from_pydata([tuple(c*.01 for c in v) for v in part.vertices],[],part.faces)
        data.update();data.calc_loop_triangles()
        triangles=[tuple(t.vertices) for t in data.loop_triangles]
        tree=BVHTree.FromPolygons([v.co for v in data.vertices],triangles,all_triangles=True)
        collisions=sum(a<b and not set(triangles[a]).intersection(triangles[b]) for a,b in tree.overlap(tree))
        if collisions:raise ValueError('Self-intersecting control surface: %s triangle pairs' % collisions)
        return collisions
    finally:
        bpy.data.meshes.remove(data)


def save_surface_study(mesh,report,output,render=True):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene
    # Script wrapper enforces background mode; this never clears an artist's scene.
    scene.name='Character';_configure(scene,800,1000)
    for obj in list(scene.objects):
        if obj.type!='LIGHT':bpy.data.objects.remove(obj,do_unlink=True)
    material=bpy.data.materials.new('Neutral anatomical clay');material.diffuse_color=(.57,.43,.34,1);material.use_nodes=True
    shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.42,.32,.25,1);shader.inputs['Roughness'].default_value=.6
    part=mesh.parts[0];data=bpy.data.meshes.new('Mathematical anatomical surface')
    data.from_pydata([tuple(c*.01 for c in v) for v in part.vertices],[],part.faces);data.update()
    report['base_triangle_self_intersections']=validate_control_surface(part)
    report['not_checked']=[x for x in report['not_checked'] if x!='self_intersections']+['subdivision_self_intersections']
    body=bpy.data.objects.new('Human surface - generated study',data);scene.collection.objects.link(body);data.materials.append(material)
    for face in data.polygons:face.use_smooth=True
    modifier=body.modifiers.new('Surface display subdivision','SUBSURF');modifier.levels=2;modifier.render_levels=2
    body['generator']=report['generator'];body['geometry_sha256']=report['geometry_sha256'];body['ownership']='generated';body['quality_status']=report['quality_status']
    h=report['parameters']['height_cm']*.01
    for name,pos in [('Front',(0,4,h*.5)),('Side',(4,0,h*.5)),('Back',(0,-4,h*.5)),('Three quarter',(2.7,4,h*.55))]:
        cam=_camera(scene,name,pos,(0,0,h*.5),h*1.14)
        if name=='Three quarter':scene.camera=cam
    # Separate review scene references the same mesh, with no duplicate character
    # instances left in the editable Character scene.
    review=bpy.data.scenes.new('Four view review');_configure(review,1600,1000)
    for x,angle,name in [(1.2,0,'Front'),(.4,-math.pi/4,'Three quarter'),(-.4,-math.pi/2,'Side'),(-1.2,math.pi,'Back')]:
        copy=body.copy();copy.data=data;copy.name=name+' review';copy.location.x=x;copy.rotation_euler.z=angle;review.collection.objects.link(copy)
    review.camera=_camera(review,'Review camera',(0,5,h*.5),(0,0,h*.5),3.45)
    bpy.data.texts.new('GENERATION_REPORT.json').write(json.dumps(report,indent=2))
    bpy.data.texts.new('READ ME').write('Mathematical Human study. Pure procedural source: object_core/geometry/surface_human.py.\nRun scripts/build_surface_human.py with presets/human/maxine.json.\nNo external meshes or voxel union. Shape controls are constrained by the preset schema.\nExperimental geometry: not yet animation-ready or reference-approved.\nReport records checks and exclusions; inspect all four views before accepting.\n')
    bpy.context.view_layer.objects.active=body;body.select_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_location=Vector((0,0,h*.5));area.spaces.active.region_3d.view_distance=h*1.5
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'character.blend'))
    (output/'generation_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (output/'resolved_preset.json').write_text(json.dumps({'schema_version':1,'generator':report['generator'],'parameters':report['parameters']},indent=2),encoding='utf8')
    if render:
        scene.render.filepath=str(output/'character.png');bpy.ops.render.render(write_still=True,scene=scene.name)
        review.render.filepath=str(output/'review.png');bpy.ops.render.render(write_still=True,scene=review.name)
        checks={}
        for name in ('character.png','review.png'):
            image=bpy.data.images.load(str(output/name),check_existing=False)
            pixels=array('f',[0.0])*len(image.pixels);image.pixels.foreach_get(pixels)
            step=max(4,(len(pixels)//4096//4)*4)
            samples=pixels[::step]
            contrast=max(samples)-min(samples)
            checks[name]={'width':image.size[0],'height':image.size[1],'sampled_red_range':contrast}
            bpy.data.images.remove(image)
            if contrast<.005:raise RuntimeError('Blank or uniform preview: '+name)
        (output/'render_report.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
    return output/'character.blend'
