# SPDX-License-Identifier: GPL-3.0-or-later
"""Render an A-Z geometry stress-test scene for the visual-testing branch.

This intentionally reuses the pelvis review script entry point and output naming
so the existing visual-testing automation can keep running unchanged.  The scene
contains one extruded mesh for each uppercase letter A-Z.  Natural glyph
geometry gives us a compact test bed for straight runs, diagonals, acute corners,
bowls, counters, S-curves, junctions, and mixed sharp/rounded transitions.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

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
    parser.add_argument("--letter-size", type=float, default=3.0)
    parser.add_argument("--spacing-x", type=float, default=4.6)
    parser.add_argument("--spacing-z", type=float, default=4.2)
    parser.add_argument("--extrude", type=float, default=0.42)

    # Backward-compatible no-op options from the pelvis renderer. The external
    # visual-test runner can keep its existing command line while we repurpose
    # this script for the alphabet experiment.
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


def make_material():
    material = bpy.data.materials.new("Alphabet Geometry Review")
    material.use_nodes = True
    return material


def configure_material(material, mode):
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")

    if mode == "clay":
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        shader.inputs["Base Color"].default_value = (0.56, 0.59, 0.64, 1.0)
        shader.inputs["Roughness"].default_value = 0.68
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
        size_input.default_value = 1.15

    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    mix.inputs[1].default_value = (0.055, 0.065, 0.08, 1.0)
    mix.inputs[2].default_value = (0.92, 0.94, 0.97, 1.0)
    links.new(wire.outputs["Fac"], mix.inputs[0])

    shader = nodes.new("ShaderNodeEmission")
    links.new(mix.outputs["Color"], shader.inputs["Color"])
    shader.inputs["Strength"].default_value = 1.0
    links.new(shader.outputs["Emission"], output.inputs["Surface"])


def configure_world(mode):
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("Alphabet Review World")
    scene.world = world
    world.use_nodes = True

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")

    if mode == "clay":
        background.inputs["Color"].default_value = (0.075, 0.09, 0.115, 1.0)
        background.inputs["Strength"].default_value = 0.34
    else:
        background.inputs["Color"].default_value = (0.008, 0.010, 0.014, 1.0)
        background.inputs["Strength"].default_value = 0.05

    links.new(background.outputs["Background"], output.inputs["Surface"])


def bevel_for(letter):
    if letter in ROUND:
        return 0.11, 5, "round"
    if letter in ANGULAR:
        return 0.035, 1, "sharp"
    return 0.07, 3, "mixed"


def add_letter(letter, location, size, extrude, material):
    bpy.ops.object.text_add(location=location, rotation=(math.radians(90.0), 0.0, 0.0))
    obj = bpy.context.object
    obj.name = f"Letter {letter}"

    curve = obj.data
    curve.body = letter
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    curve.extrude = extrude

    bevel_depth, bevel_resolution, family = bevel_for(letter)
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = bevel_resolution
    curve.resolution_u = 12
    obj["shape_family"] = family
    obj["source_letter"] = letter

    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.name = f"Letter {letter} [{family}]"
    obj.data.materials.append(material)

    # Keep the front/back glyph faces crisp while the authored bevel geometry
    # itself supplies the rounded transition where requested.
    for polygon in obj.data.polygons:
        polygon.use_smooth = False

    return obj


def build_alphabet(material, columns, size, spacing_x, spacing_z, extrude):
    columns = max(1, min(int(columns), 13))
    rows = math.ceil(len(LETTERS) / columns)

    objects = []
    for index, letter in enumerate(LETTERS):
        row = index // columns
        column = index % columns
        count_in_row = min(columns, len(LETTERS) - row * columns)

        x = (column - (count_in_row - 1) * 0.5) * spacing_x
        z = ((rows - 1) * 0.5 - row) * spacing_z
        y = 0.0

        obj = add_letter(letter, (x, y, z), size, extrude, material)
        objects.append(obj)

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
    add_area_light("Key", (-15.0, -18.0, 16.0), 1450.0, 8.0)
    add_area_light("Fill", (15.0, -12.0, 7.0), 900.0, 10.0)
    add_area_light("Rim", (0.0, 7.0, 13.0), 1250.0, 7.0)


def configure_camera(columns, rows, size, spacing_x, spacing_z):
    visible_width = max(size * 1.8, (columns - 1) * spacing_x + size * 1.7)
    visible_height = max(size * 1.8, (rows - 1) * spacing_z + size * 1.8)

    camera_data = bpy.data.cameras.new("Alphabet Review Camera")
    camera = bpy.data.objects.new("Alphabet Review Camera", camera_data)
    bpy.context.collection.objects.link(camera)

    camera.location = (3.6, -42.0, 5.2)
    look_at(camera, (0.0, 0.0, 0.0))
    camera_data.type = "ORTHO"

    aspect = 1800.0 / 900.0
    camera_data.ortho_scale = max(visible_height * 1.16, visible_width / aspect * 1.12)
    bpy.context.scene.camera = camera


def configure_scene(columns, rows, size, spacing_x, spacing_z):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.15

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

    # Lighting helps the clay pass reveal bevel depth. Emission-based diagnostic
    # passes ignore these lights naturally.
    scene = bpy.context.scene
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {mode}: {output}")


def main():
    options = args()
    clear_scene()

    material = make_material()
    objects, rows = build_alphabet(
        material,
        options.columns,
        options.letter_size,
        options.spacing_x,
        options.spacing_z,
        options.extrude,
    )
    configure_scene(options.columns, rows, options.letter_size, options.spacing_x, options.spacing_z)

    base = Path(options.output).resolve()
    base.parent.mkdir(parents=True, exist_ok=True)

    for mode in options.modes:
        render_mode(material, mode, output_for_mode(base, mode))

    print(
        "Alphabet geometry review complete: "
        f"{len(objects)} letters, {rows} rows, modes={','.join(options.modes)}"
    )


if __name__ == "__main__":
    main()
