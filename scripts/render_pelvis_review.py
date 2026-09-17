# SPDX-License-Identifier: GPL-3.0-or-later
"""Render an Astra-style overlapping-mass pelvis experiment.

This is deliberately a visual-test-only construction.  It does not change the
portable Human V2 pelvis generator in object_core.  The experiment asks one
specific question: does shaping the pelvis from overlapping analytic masses,
then voxel-unifying them, produce a more convincing neutral hip/crotch surface
than asking the current patch surface to solve the whole form directly?
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

VIEWS = (("Front", 180.0), ("3/4", 135.0), ("Side", 90.0), ("Back", 0.0))
MODES = ("clay", "silhouette", "wireframe")


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="pelvis_review.png")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--width", type=float, default=34.0)
    parser.add_argument("--depth", type=float, default=24.0)
    parser.add_argument("--height", type=float, default=20.0)
    parser.add_argument("--hip-fullness", type=float, default=1.0)
    parser.add_argument("--glute-projection", type=float, default=1.0)
    parser.add_argument("--crotch-width", type=float, default=7.0)
    parser.add_argument("--thigh-spacing", type=float, default=4.0)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def look(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def make_material():
    material = bpy.data.materials.new("Pelvis Review")
    material.use_nodes = True
    return material


def configure_material(material, mode):
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")

    if mode == "clay":
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        shader.inputs["Base Color"].default_value = (0.66, 0.68, 0.71, 1.0)
        shader.inputs["Roughness"].default_value = 0.8
        shader.inputs["Metallic"].default_value = 0.0
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        return

    if mode == "silhouette":
        shader = nodes.new("ShaderNodeEmission")
        shader.inputs["Color"].default_value = (0.95, 0.95, 0.95, 1.0)
        shader.inputs["Strength"].default_value = 1.0
        links.new(shader.outputs["Emission"], output.inputs["Surface"])
        return

    # Render the actual voxel-unified surface edges without constructing a
    # separate curve object for every dense remesh edge.
    wire = nodes.new("ShaderNodeWireframe")
    if hasattr(wire, "use_pixel_size"):
        wire.use_pixel_size = True
    size_input = wire.inputs.get("Size")
    if size_input is not None:
        size_input.default_value = 1.0
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    mix.inputs[1].default_value = (0.88, 0.89, 0.87, 1.0)
    mix.inputs[2].default_value = (0.025, 0.03, 0.04, 1.0)
    links.new(wire.outputs["Fac"], mix.inputs[0])
    shader = nodes.new("ShaderNodeEmission")
    links.new(mix.outputs["Color"], shader.inputs["Color"])
    links.new(shader.outputs["Emission"], output.inputs["Surface"])


def add_loft(name, rows, segments=48):
    """Create a capped elliptical loft from (x, y, z, rx, ry) rows."""
    vertices = []
    faces = []
    for x, y, z, rx, ry in rows:
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            vertices.append((x + rx * math.cos(angle), y + ry * math.sin(angle), z))

    for row in range(len(rows) - 1):
        for index in range(segments):
            a = row * segments + index
            b = row * segments + (index + 1) % segments
            faces.append((a, b, b + segments, a + segments))

    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple((len(rows) - 1) * segments + index for index in range(segments)))

    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def add_ellipsoid(name, location, scale):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def apply_modifier(obj, modifier):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def build_astra_pelvis(width, depth, height, hip_fullness, glute_projection, crotch_width, thigh_spacing):
    """Build the lower torso, glutes, and proximal thighs as overlapping masses.

    Ratios are adapted from the Maxine study rather than copied as fixed meters.
    Posterior is -Y here to match the existing pelvis-review camera convention.
    """
    half_w = width * 0.5
    half_d = depth * 0.5
    hip = max(0.65, hip_fullness)
    glute = max(0.55, glute_projection)
    crotch = max(0.5, crotch_width)
    spacing = max(0.0, thigh_spacing)

    # Astra's useful pelvis pattern is the width profile, not the absolute
    # coordinates: a narrow central root expands rapidly into the hip bowl,
    # reaches its broadest point above the thigh origins, then tapers into the
    # waist.  The slight -Y bias carries the lower torso into the rear masses.
    torso_rows = (
        (0.0, -depth * 0.035, -height * 0.54, max(crotch * 0.95, half_w * 0.20), half_d * 0.58),
        (0.0, -depth * 0.040, -height * 0.24, half_w * 0.84 * hip, half_d * 0.84),
        (0.0, -depth * 0.035, height * 0.12, half_w * 1.00 * hip, half_d * 0.95),
        (0.0, -depth * 0.015, height * 0.48, half_w * 0.86, half_d * 0.79),
        (0.0, 0.0, height * 0.68, half_w * 0.70, half_d * 0.68),
    )
    parts = [add_loft("Astra lower torso", torso_rows)]

    # Explicit glute volumes are intentionally established before remeshing.
    # Smoothing is not responsible for inventing posterior anatomy.
    glute_x = half_w * 0.50
    glute_y = -half_d * (0.60 + 0.10 * (glute - 1.0))
    glute_z = -height * 0.02
    glute_scale = (
        half_w * 0.58 * hip,
        half_d * 0.66 * glute,
        height * 0.56,
    )
    parts.append(add_ellipsoid("Astra glute L", (-glute_x, glute_y, glute_z), glute_scale))
    parts.append(add_ellipsoid("Astra glute R", (glute_x, glute_y, glute_z), glute_scale))

    # The proximal thighs rise high into the pelvis and overlap it substantially.
    # Their inner edges stay close to center while lateral width is carried by
    # the hip/trochanter region instead of a wide crotch bridge.
    thigh_center = max(crotch * 0.50 + spacing * 0.30, half_w * 0.30)
    for side, label in ((-1.0, "L"), (1.0, "R")):
        rows = (
            (side * thigh_center, -depth * 0.015, -height * 0.04, half_w * 0.52, half_d * 0.76),
            (side * (thigh_center + width * 0.025), -depth * 0.005, -height * 0.33, half_w * 0.47, half_d * 0.66),
            (side * (thigh_center + width * 0.075), 0.0, -height * 0.70, half_w * 0.38, half_d * 0.54),
            (side * (thigh_center + width * 0.095), 0.0, -height * 0.94, half_w * 0.34, half_d * 0.49),
        )
        parts.append(add_loft("Astra proximal thigh " + label, rows))

    # Match the useful ordering in the Maxine experiment: soften each analytic
    # source before union, then fuse at a fine voxel size and only lightly relax
    # the already-established anatomy afterward.
    for source in parts:
        rounding = source.modifiers.new("Round construction form", "SUBSURF")
        rounding.levels = 2
        rounding.render_levels = 2
        apply_modifier(source, rounding)

    bpy.ops.object.select_all(action="DESELECT")
    for source in parts:
        source.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = "Astra mass-union pelvis experiment"

    remesh = body.modifiers.new("Unify anatomy - fine voxels", "REMESH")
    remesh.mode = "VOXEL"
    # With the review defaults expressed at roughly centimetre scale this is
    # about a 3 mm union, matching the successful Maxine study closely.
    remesh.voxel_size = max(0.12, min(width, depth, height) * 0.015)
    remesh.use_smooth_shade = True
    apply_modifier(body, remesh)

    smooth = body.modifiers.new("Relax anatomical intersections", "SMOOTH")
    smooth.factor = 0.72
    smooth.iterations = 5
    apply_modifier(body, smooth)

    finish = body.modifiers.new("Surface finish", "SUBSURF")
    finish.levels = 1
    finish.render_levels = 1
    for polygon in body.data.polygons:
        polygon.use_smooth = True
    return body


def arrange_views(body, material):
    verts = [tuple(vertex.co) for vertex in body.data.vertices]
    min_z = min(vertex[2] for vertex in verts)
    max_z = max(vertex[2] for vertex in verts)
    center_z = (min_z + max_z) * 0.5
    centered = tuple((x, y, z - center_z) for x, y, z in verts)
    height = max_z - min_z

    widths = []
    centers = []
    for _, angle in VIEWS:
        radians = math.radians(angle)
        ca = math.cos(radians)
        sa = math.sin(radians)
        projected_x = [x * ca - y * sa for x, y, _ in centered]
        widths.append(max(projected_x) - min(projected_x))
        centers.append((max(projected_x) + min(projected_x)) * 0.5)

    gutter = max(2.5, max(widths) * 0.09)
    total = sum(widths) + gutter * 3
    cursor = -total * 0.5
    xs = []
    for view_width, center in zip(widths, centers):
        xs.append(cursor + view_width * 0.5 - center)
        cursor += view_width + gutter

    body.location = (xs[0], 0.0, -center_z)
    body.rotation_euler.z = math.radians(VIEWS[0][1])
    body.data.materials.clear()
    body.data.materials.append(material)
    body.name = "Pelvis " + VIEWS[0][0]
    objects = [body]

    for (name, angle), x in zip(VIEWS[1:], xs[1:]):
        obj = body.copy()
        obj.data = body.data
        obj.name = "Pelvis " + name
        bpy.context.collection.objects.link(obj)
        obj.location = (x, 0.0, -center_z)
        obj.rotation_euler.z = math.radians(angle)
        objects.append(obj)

    return objects, total, height


def configure_scene(total_width, body_height):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 500
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.35

    world = scene.world or bpy.data.worlds.new("Pelvis World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    ambient = nodes.new("ShaderNodeBackground")
    ambient.inputs["Color"].default_value = (0.42, 0.45, 0.49, 1.0)
    ambient.inputs["Strength"].default_value = 0.25
    camera_bg = nodes.new("ShaderNodeBackground")
    camera_bg.inputs["Color"].default_value = (0.045, 0.055, 0.07, 1.0)
    light_path = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(light_path.outputs["Is Camera Ray"], mix.inputs[0])
    links.new(ambient.outputs[0], mix.inputs[1])
    links.new(camera_bg.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])

    camera_data = bpy.data.cameras.new("Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 1.0
    frame = camera_data.view_frame(scene=scene)
    frame_width = max(v.x for v in frame) - min(v.x for v in frame)
    frame_height = max(v.y for v in frame) - min(v.y for v in frame)
    camera_data.ortho_scale = max(total_width * 1.08 / frame_width, body_height * 1.18 / frame_height)
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (0.0, -180.0, 0.0)
    look(camera, (0.0, 0.0, 0.0))
    scene.camera = camera

    for name, energy, size, location in (
        ("Key", 40000, 90, (-45, -75, 60)),
        ("Fill", 12000, 100, (45, -65, 35)),
        ("Top", 16000, 100, (0, -25, 85)),
        ("Under", 6400, 90, (0, -35, -55)),
        ("Back Fill", 12800, 100, (0, 55, 35)),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        bpy.context.collection.objects.link(light)
        light.location = location
        look(light, (0.0, 0.0, 0.0))

    return scene, camera


def assert_views_fit(scene, camera, objects):
    from bpy_extras.object_utils import world_to_camera_view

    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            for vertex in mesh.vertices:
                projected = world_to_camera_view(scene, camera, evaluated.matrix_world @ vertex.co)
                if not (0.0 < projected.x < 1.0 and 0.0 < projected.y < 1.0 and projected.z > 0.0):
                    raise RuntimeError("Pelvis diagnostic view falls outside camera: " + obj.name)
        finally:
            evaluated.to_mesh_clear()


def main():
    options = args()
    clear()
    body = build_astra_pelvis(
        options.width,
        options.depth,
        options.height,
        options.hip_fullness,
        options.glute_projection,
        options.crotch_width,
        options.thigh_spacing,
    )
    material = make_material()
    objects, total_width, body_height = arrange_views(body, material)
    scene, camera = configure_scene(total_width, body_height)
    assert_views_fit(scene, camera, objects)

    output = Path(options.output)
    output = output if output.is_absolute() else REPO_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    for mode in options.modes:
        scene.cycles.use_denoising = mode == "clay"
        configure_material(material, mode)
        target = output if mode == "clay" else output.with_name(output.stem + "_" + mode + output.suffix)
        scene.render.filepath = os.fspath(target)
        bpy.ops.render.render(write_still=True)
        print("Astra pelvis mass-union review", mode, "written to", target)


if __name__ == "__main__":
    main()
