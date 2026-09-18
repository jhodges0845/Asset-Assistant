# SPDX-License-Identifier: GPL-3.0-or-later
"""Render a volumetric A-Z geometry stress-test scene for the visual-testing branch.

This intentionally reuses the pelvis review script entry point and output naming
so the existing visual-testing automation can keep running unchanged.

Unlike the previous flat-text extrusion study, this one builds each letter from
multiple depth slices. Those slices are shifted, scaled, and rotated differently
through space, then voxel-unified into a single volume.
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
    parser.add_argument("--letter-size", type=float, default=2.75)
    parser.add_argument("--spacing-x", type=float, default=5.0)
    parser.add_argument("--spacing-z", type=float, default=5.0)
    parser.add_argument("--depth", type=float, default=1.6)
    parser.add_argument("--slices", type=int, default=6)
    parser.add_argument("--voxel", type=float, default=0.09)

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


def letter_style(letter):
    idx = ord(letter) - ord("A")
    family = "mixed"
    if letter in ANGULAR:
        family = "angular"
    elif letter in ROUND:
        family = "round"

    return {
        "family": family,
        "x_amp": 0.12 + 0.02 * (idx % 4),
        "z_amp": 0.10 + 0.025 * (idx % 3),
        "rot_amp": math.radians(3.0 + (idx % 5) * 1.2),
        "front_scale_x": 1.0 + 0.06 * ((idx % 3) - 1),
        "back_scale_x": 1.0 - 0.05 * ((idx % 4) - 1.5) / 1.5,
        "front_scale_z": 1.0 + 0.05 * (((idx + 1) % 3) - 1),
        "back_scale_z": 1.0 - 0.04 * (((idx + 2) % 4) - 1.5) / 1.5,
    }


def make_slice(letter, center, size):
    bpy.ops.object.text_add(location=center, rotation=(math.radians(90.0), 0.0, 0.0))
    obj = bpy.context.object
    curve = obj.data
    curve.body = letter
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    curve.resolution_u = 12
    curve.fill_mode = "BOTH"
    bpy.ops.object.convert(target="MESH")
    return bpy.context.object


def sculpt_slice(obj, letter, t, base_x, base_z):
    style = letter_style(letter)
    wave = math.sin(t * math.pi)
    twist = math.sin((t - 0.5) * math.pi)
    sway_x = style["x_amp"] * base_x * math.sin(t * math.pi * 1.15)
    sway_z = style["z_amp"] * base_z * math.cos(t * math.pi * 1.35)
    bulge = 1.0 + 0.18 * wave

    scale_x = (1.0 - t) * style["front_scale_x"] + t * style["back_scale_x"]
    scale_z = (1.0 - t) * style["front_scale_z"] + t * style["back_scale_z"]

    if style["family"] == "angular":
        scale_x *= 1.0 + 0.05 * wave
        scale_z *= 1.0 - 0.03 * wave
    elif style["family"] == "round":
        scale_x *= bulge
        scale_z *= bulge

    obj.location.x += sway_x
    obj.location.z += sway_z
    obj.rotation_euler.y = style["rot_amp"] * twist
    obj.scale = (scale_x, 1.0, scale_z)


def make_letter_volume(letter, location, size, depth, slices, voxel, material):
    slices = max(3, int(slices))
    step = depth / (slices - 1)
    created = []
    base_x = size * 0.45
    base_z = size * 0.45

    for i in range(slices):
        t = i / (slices - 1)
        y = location[1] - depth * 0.5 + i * step
        obj = make_slice(letter, (location[0], y, location[2]), size)
        sculpt_slice(obj, letter, t, base_x, base_z)
        created.append(obj)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in created:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = created[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = f"Letter {letter} volume"

    remesh = obj.modifiers.new("Voxel unify", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = voxel
    remesh.use_smooth_shade = True
    apply_modifier(obj, remesh.name)

    smooth = obj.modifiers.new("Smooth", "SMOOTH")
    smooth.factor = 0.35
    smooth.iterations = 6
    apply_modifier(obj, smooth.name)

    subdiv = obj.modifiers.new("Subsurf", "SUBSURF")
    subdiv.levels = 1
    subdiv.render_levels = 1

    obj.data.materials.clear()
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True

    obj["source_letter"] = letter
    obj["shape_family"] = letter_style(letter)["family"]
    return obj


def build_letters(material, columns, size, spacing_x, spacing_z, depth, slices, voxel):
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
            make_letter_volume(
                letter,
                (x, 0.0, z),
                size,
                depth,
                slices,
                voxel,
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

    camera.location = (4.0, -46.0, 6.0)
    look_at(camera, (0.0, 0.2, 0.0))
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
        options.slices,
        options.voxel,
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
