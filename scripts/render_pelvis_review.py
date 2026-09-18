# SPDX-License-Identifier: GPL-3.0-or-later
"""Three-sphere procedural geometry comparison for visual testing.

This keeps the legacy pelvis-review script path and output names so the existing
visual-testing automation can run unchanged.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

MODES = ("clay", "silhouette", "wireframe")


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="pelvis_review.png")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--radius", type=float, default=1.6)

    # Legacy automation compatibility.
    parser.add_argument("--width", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--depth", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--height", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--hip-fullness", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--glute-projection", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--crotch-width", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--thigh-spacing", type=float, default=None, help=argparse.SUPPRESS)

    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.curves,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def make_material():
    material = bpy.data.materials.new("Sphere Geometry Study")
    material.use_nodes = True
    return material


def configure_material(material, mode):
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")

    if mode == "clay":
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        shader.inputs["Base Color"].default_value = (0.62, 0.65, 0.70, 1.0)
        shader.inputs["Roughness"].default_value = 0.72
        shader.inputs["Metallic"].default_value = 0.0
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        return

    if mode == "silhouette":
        shader = nodes.new("ShaderNodeEmission")
        shader.inputs["Color"].default_value = (0.98, 0.98, 0.98, 1.0)
        shader.inputs["Strength"].default_value = 1.0
        links.new(shader.outputs["Emission"], output.inputs["Surface"])
        return

    wire = nodes.new("ShaderNodeWireframe")
    if hasattr(wire, "use_pixel_size"):
        wire.use_pixel_size = True
    if wire.inputs.get("Size") is not None:
        wire.inputs["Size"].default_value = 1.0

    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    mix.inputs[1].default_value = (0.055, 0.065, 0.08, 1.0)
    mix.inputs[2].default_value = (0.95, 0.96, 0.98, 1.0)
    links.new(wire.outputs["Fac"], mix.inputs[0])

    shader = nodes.new("ShaderNodeEmission")
    shader.inputs["Strength"].default_value = 1.0
    links.new(mix.outputs["Color"], shader.inputs["Color"])
    links.new(shader.outputs["Emission"], output.inputs["Surface"])


def configure_world(mode):
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("Sphere Study World")
    scene.world = world
    world.use_nodes = True

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    if mode == "clay":
        background.inputs["Color"].default_value = (0.065, 0.078, 0.10, 1.0)
        background.inputs["Strength"].default_value = 0.30
    else:
        background.inputs["Color"].default_value = (0.008, 0.010, 0.014, 1.0)
        background.inputs["Strength"].default_value = 0.05
    links.new(background.outputs["Background"], output.inputs["Surface"])


def add_uv_sphere(name, location, radius, segments, rings, material, smooth):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=radius,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = smooth
    return obj


def add_icosphere(name, location, radius, subdivisions, material):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions,
        radius=radius,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def add_label(text, location, size, material):
    bpy.ops.object.text_add(
        location=location,
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = f"Label {text}"
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.012
    obj.data.materials.append(material)
    return obj


def build_geometry(material, radius):
    spacing = radius * 3.45

    low = add_uv_sphere(
        "01 Low Poly Smooth",
        (-spacing, 0.0, radius * 0.75),
        radius,
        segments=8,
        rings=4,
        material=material,
        smooth=True,
    )
    low["method"] = "UV sphere: 8 segments, 4 rings, smooth shading"

    # 32 angular steps give a circular sagitta error of:
    # 1 - cos(pi / 32) ~= 0.004815 = 0.4815% of radius.
    # 16 latitude rings keep the meridional sampling safely below 1% as well.
    high = add_uv_sphere(
        "02 High Resolution Under 1 Percent Error",
        (0.0, 0.0, radius * 0.75),
        radius,
        segments=32,
        rings=16,
        material=material,
        smooth=True,
    )
    high["method"] = "UV sphere: 32 segments, 16 rings, geometric chord error < 1% radius"

    ico = add_icosphere(
        "03 Triangle Subdivision Icosphere",
        (spacing, 0.0, radius * 0.75),
        radius,
        subdivisions=2,
        material=material,
    )
    ico["method"] = "Icosphere: subdivided triangular topology"

    label_z = -radius * 1.25
    add_label("LOW POLY + SMOOTH", (-spacing, -0.15, label_z), radius * 0.20, material)
    add_label("< 1% ERROR UV SPHERE", (0.0, -0.15, label_z), radius * 0.18, material)
    add_label("SUBDIVIDED TRIANGLES", (spacing, -0.15, label_z), radius * 0.18, material)

    return [low, high, ico], spacing


def add_area_light(name, location, energy, size, target):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)


def add_lights(radius, spacing):
    target = (0.0, 0.0, radius * 0.7)
    add_area_light(
        "Key",
        (-spacing * 0.55, -radius * 5.2, radius * 4.5),
        1450.0,
        radius * 3.0,
        target,
    )
    add_area_light(
        "Fill",
        (spacing * 0.75, -radius * 4.0, radius * 2.2),
        850.0,
        radius * 3.5,
        target,
    )
    add_area_light(
        "Rim",
        (0.0, radius * 4.0, radius * 4.8),
        1200.0,
        radius * 2.8,
        target,
    )


def configure_camera(radius, spacing):
    camera_data = bpy.data.cameras.new("Sphere Study Camera")
    camera = bpy.data.objects.new("Sphere Study Camera", camera_data)
    bpy.context.collection.objects.link(camera)

    # Orthographic view keeps all three spheres the same apparent size and
    # removes perspective as a variable in the comparison.
    camera_data.type = "ORTHO"
    # Blender orthographic scale controls the camera width here. The three\n    # sphere centers span 6.9 radii, and their silhouettes add another 2 radii.\n    # Use a little over 10 radii so all three fit with clear side margins.\n    camera_data.ortho_scale = radius * 10.2\n    camera.location = (0.0, -radius * 11.0, radius * 3.0)
    look_at(camera, (0.0, 0.0, radius * 0.55))
    bpy.context.scene.camera = camera


def configure_scene(radius, spacing):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True

    scene.render.resolution_x = 1800
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.15

    configure_camera(radius, spacing)
    add_lights(radius, spacing)


def output_for_mode(base, mode):
    base = Path(base)
    if mode == "clay":
        return base
    return base.with_name(f"{base.stem}_{mode}{base.suffix}")


def render_mode(material, mode, output):
    configure_material(material, mode)
    configure_world(mode)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {mode}: {output}")


def main():
    options = args()
    clear_scene()

    material = make_material()
    spheres, spacing = build_geometry(material, options.radius)
    configure_scene(options.radius, spacing)

    base = Path(options.output).resolve()
    base.parent.mkdir(parents=True, exist_ok=True)

    for mode in options.modes:
        render_mode(material, mode, output_for_mode(base, mode))

    print(
        "Sphere geometry study complete: "
        f"{len(spheres)} spheres, modes={','.join(options.modes)}"
    )


if __name__ == "__main__":
    main()
