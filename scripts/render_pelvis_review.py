# SPDX-License-Identifier: GPL-3.0-or-later
"""Render a volumetric A-Z geometry stress-test scene for the visual-testing branch.

This intentionally reuses the pelvis review script entry point and output naming
so the existing visual-testing automation can keep running unchanged.

This version deforms one coherent extruded letter mesh through its depth. The
front, middle, and back can shift, scale, bulge, and twist independently while
remaining one connected surface.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

MODES = ("clay", "silhouette", "wireframe")
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ANGULAR = set("AEFHKILMNTVWXYZ")
ROUND = set("BCDGOPQSU")


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="pelvis_review.png")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--columns", type=int, default=7)
    parser.add_argument("--letter-size", type=float, default=2.75)
    parser.add_argument("--spacing-x", type=float, default=5.0)
    parser.add_argument("--spacing-z", type=float, default=5.0)
    parser.add_argument("--depth", type=float, default=1.6)
    parser.add_argument("--depth-cuts", type=int, default=7)

    parser.add_argument("--width", type=float, default=None, help=argparse.SUPPRESS)
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
        bpy.data.curves,
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def apply_modifier(obj, name):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=name)


def make_material():
    material = bpy.data.materials.new("Volumetric Letter Review")
    material.use_nodes = True
    return material


def configure_material(material, mode):
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")

    if mode == "clay":
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        shader.inputs["Base Color"].default_value = (0.62, 0.65, 0.69, 1.0)
        shader.inputs["Roughness"].default_value = 0.74
        shader.inputs["Metallic"].default_value = 0.0
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        return

    if mode == "silhouette":
        shader = nodes.new("ShaderNodeEmission")
        shader.inputs["Color"].default_value = (0.97, 0.97, 0.97, 1.0)
        shader.inputs["Strength"].default_value = 1.0
        links.new(shader.outputs["Emission"], output.inputs["Surface"])
        return

    wire = nodes.new("ShaderNodeWireframe")
    if hasattr(wire, "use_pixel_size"):
        wire.use_pixel_size = True
    size_input = wire.inputs.get("Size")
    if size_input is not None:
        size_input.default_value = 1.05

    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    mix.inputs[1].default_value = (0.08, 0.09, 0.11, 1.0)
    mix.inputs[2].default_value = (0.92, 0.94, 0.97, 1.0)
    links.new(wire.outputs["Fac"], mix.inputs[0])

    shader = nodes.new("ShaderNodeEmission")
    links.new(mix.outputs["Color"], shader.inputs["Color"])
    links.new(shader.outputs["Emission"], output.inputs["Surface"])


def configure_world(mode):
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("Volumetric Letters World")
    scene.world = world
    world.use_nodes = True

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")

    if mode == "clay":
        background.inputs["Color"].default_value = (0.07, 0.085, 0.105, 1.0)
        background.inputs["Strength"].default_value = 0.34
    else:
        background.inputs["Color"].default_value = (0.01, 0.012, 0.016, 1.0)
        background.inputs["Strength"].default_value = 0.06

    links.new(background.outputs["Background"], output.inputs["Surface"])


def family_for(letter):
    if letter in ROUND:
        return "round"
    if letter in ANGULAR:
        return "angular"
    return "mixed"


def style_for(letter):
    idx = ord(letter) - ord("A")
    family = family_for(letter)
    direction = -1.0 if idx % 2 else 1.0
    return {
        "family": family,
        "direction": direction,
        "sway_x": 0.22 + 0.035 * (idx % 4),
        "sway_y": 0.14 + 0.03 * ((idx + 1) % 4),
        "twist": math.radians(10.0 + 2.0 * (idx % 5)),
        "bulge_x": 0.12 + 0.025 * (idx % 3),
        "bulge_y": 0.10 + 0.02 * ((idx + 2) % 3),
        "front_x": 0.94 + 0.04 * (idx % 3),
        "back_x": 1.06 - 0.03 * ((idx + 1) % 3),
        "front_y": 1.04 - 0.03 * (idx % 3),
        "back_y": 0.95 + 0.035 * ((idx + 2) % 3),
    }


def subdivide_depth_edges(mesh, cuts):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    depth_edges = [
        edge for edge in bm.edges
        if abs(edge.verts[0].co.z - edge.verts[1].co.z) > 1.0e-5
    ]
    if depth_edges and cuts > 0:
        bmesh.ops.subdivide_edges(
            bm,
            edges=depth_edges,
            cuts=cuts,
            use_grid_fill=False,
        )
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def deform_through_depth(obj, letter):
    verts = obj.data.vertices
    if not verts:
        return

    min_z = min(v.co.z for v in verts)
    max_z = max(v.co.z for v in verts)
    depth = max(max_z - min_z, 1.0e-6)

    min_x = min(v.co.x for v in verts)
    max_x = max(v.co.x for v in verts)
    min_y = min(v.co.y for v in verts)
    max_y = max(v.co.y for v in verts)
    cx = (min_x + max_x) * 0.5
    cy = (min_y + max_y) * 0.5
    width = max(max_x - min_x, 1.0e-6)
    height = max(max_y - min_y, 1.0e-6)

    style = style_for(letter)
    direction = style["direction"]

    for vert in verts:
        t = (vert.co.z - min_z) / depth
        centered = t - 0.5
        mid = math.sin(math.pi * t)
        wave = math.sin(math.pi * (1.35 * t + 0.12 * direction))

        sx = (1.0 - t) * style["front_x"] + t * style["back_x"]
        sy = (1.0 - t) * style["front_y"] + t * style["back_y"]
        sx *= 1.0 + style["bulge_x"] * mid
        sy *= 1.0 + style["bulge_y"] * mid

        if style["family"] == "angular":
            sy *= 1.0 - 0.035 * mid
        elif style["family"] == "round":
            sx *= 1.0 + 0.055 * mid
            sy *= 1.0 + 0.04 * mid

        x = (vert.co.x - cx) * sx
        y = (vert.co.y - cy) * sy

        angle = style["twist"] * math.sin(math.pi * centered) * direction
        ca = math.cos(angle)
        sa = math.sin(angle)
        xr = x * ca - y * sa
        yr = x * sa + y * ca

        shift_x = width * style["sway_x"] * wave * direction
        shift_y = height * style["sway_y"] * math.cos(math.pi * (1.1 * t + 0.2))

        vert.co.x = cx + xr + shift_x
        vert.co.y = cy + yr + shift_y


def make_letter(letter, location, size, depth, depth_cuts, material):
    family = family_for(letter)
    bpy.ops.object.text_add(location=(0.0, 0.0, 0.0))
    obj = bpy.context.object
    curve = obj.data
    curve.body = letter
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    curve.extrude = depth * 0.5
    curve.resolution_u = 12
    curve.bevel_depth = 0.055 if family == "angular" else 0.075
    curve.bevel_resolution = 2 if family == "angular" else 3

    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.name = f"Letter {letter} multidirectional"

    subdivide_depth_edges(obj.data, max(1, int(depth_cuts)))
    deform_through_depth(obj, letter)

    # Glyph plane -> global X/Z; extrusion/deformation depth -> global Y.
    obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    obj.location = location
    obj.data.materials.append(material)
    obj["source_letter"] = letter
    obj["shape_family"] = family

    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def build_letters(material, columns, size, spacing_x, spacing_z, depth, depth_cuts):
    columns = max(1, min(int(columns), 7))
    rows = math.ceil(len(LETTERS) / columns)
    objects = []

    for index, letter in enumerate(LETTERS):
        row = index // columns
        column = index % columns
        count_in_row = min(columns, len(LETTERS) - row * columns)
        x = (column - (count_in_row - 1) * 0.5) * spacing_x
        z = ((rows - 1) * 0.5 - row) * spacing_z

        objects.append(
            make_letter(
                letter,
                (x, 0.0, z),
                size,
                depth,
                depth_cuts,
                material,
            )
        )

    return objects, rows


def add_area_light(name, location, energy, size, target=(0.0, 0.0, 0.0)):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def add_lights():
    add_area_light("Key", (-18.0, -20.0, 18.0), 1550.0, 9.0)
    add_area_light("Fill", (18.0, -14.0, 8.0), 950.0, 11.0)
    add_area_light("Rim", (0.0, 10.0, 16.0), 1300.0, 8.0)


def configure_camera(columns, rows, size, spacing_x, spacing_z):
    visible_width = max(size * 2.0, (columns - 1) * spacing_x + size * 2.0)
    visible_height = max(size * 2.0, (rows - 1) * spacing_z + size * 2.0)

    camera_data = bpy.data.cameras.new("Volumetric Letters Camera")
    camera = bpy.data.objects.new("Volumetric Letters Camera", camera_data)
    bpy.context.collection.objects.link(camera)

    # Strong three-quarter view so depth deformation is obvious.\n    camera.location = (19.0, -38.0, 12.0)\n    look_at(camera, (0.0, 0.2, 0.0))
    camera_data.type = "ORTHO"

    aspect = 1800.0 / 900.0
    camera_data.ortho_scale = max(visible_height * 1.18, visible_width / aspect * 1.12)
    bpy.context.scene.camera = camera


def configure_scene(columns, rows, size, spacing_x, spacing_z):
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
    scene.view_settings.exposure = 0.2

    configure_camera(columns, rows, size, spacing_x, spacing_z)
    add_lights()


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
    objects, rows = build_letters(
        material,
        options.columns,
        options.letter_size,
        options.spacing_x,
        options.spacing_z,
        options.depth,
        options.depth_cuts,
    )

    configure_scene(
        options.columns,
        rows,
        options.letter_size,
        options.spacing_x,
        options.spacing_z,
    )

    base = Path(options.output).resolve()
    base.parent.mkdir(parents=True, exist_ok=True)

    for mode in options.modes:
        render_mode(material, mode, output_for_mode(base, mode))

    print(
        "Volumetric alphabet review complete: "
        f"{len(objects)} letters, {rows} rows, modes={','.join(options.modes)}"
    )


if __name__ == "__main__":
    main()
