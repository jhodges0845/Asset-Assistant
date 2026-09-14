# SPDX-License-Identifier: GPL-3.0-or-later
"""Render neutral-Human diagnostic review contact sheets from Blender.

Run from the repository root with Blender 5.2.1 (or a compatible build):

    blender --background --factory-startup \
      --python scripts/render_human_review.py -- \
      --output human_review.png

By default one invocation writes three matched four-view sheets:

- ``human_review.png``: clay render for surface/anatomy reading
- ``human_review_silhouette.png``: flat silhouette for proportion/contour reading
- ``human_review_wireframe.png``: wireframe diagnostic for topology density/flow

Rendering uses Cycles on the CPU with 32 samples and denoising. Default Human
settings are 180 cm, 95 kg, and average body type. Each sheet contains, left to
right: front, 3/4, side, and back views of the same freshly generated Human.
This is intentionally a development-review tool, not add-on runtime code.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from object_core.providers.human import HumanExperimentalProvider  # noqa: E402


VIEW_ROTATIONS_DEGREES = (0.0, -45.0, -90.0, 180.0)
VIEW_NAMES = ("Front", "3/4", "Side", "Back")
REVIEW_MODES = ("clay", "silhouette", "wireframe")


def _parse_args():
    parser = argparse.ArgumentParser(description="Render Human V2 diagnostic review images")
    parser.add_argument("--output", default="human_review.png")
    parser.add_argument("--height-cm", type=float, default=180.0)
    parser.add_argument("--weight-kg", type=float, default=95.0)
    parser.add_argument("--body-type", default="average")
    parser.add_argument("--resolution-x", type=int, default=1800)
    parser.add_argument("--resolution-y", type=int, default=900)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=REVIEW_MODES,
        default=list(REVIEW_MODES),
        help="Diagnostic render modes to write (default: clay silhouette wireframe)",
    )
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def _human_part(args):
    provider = HumanExperimentalProvider()
    mesh = provider.mesh(
        {
            "height_cm": args.height_cm,
            "weight_kg": args.weight_kg,
            "body_type": args.body_type,
        }
    )
    if len(mesh.parts) != 1:
        raise RuntimeError("Human review renderer expects exactly one mesh part")
    return mesh.parts[0]


def _make_mesh_object(name, part):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(part.vertices, [], part.faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def _make_material():
    material = bpy.data.materials.new("Human Review Material")
    material.use_nodes = True
    return material


def _configure_clay_material(material):
    material.node_tree.nodes.clear()
    output = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
    principled = material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = (0.52, 0.55, 0.58, 1.0)
    principled.inputs["Roughness"].default_value = 0.72
    material.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])


def _configure_silhouette_material(material):
    material.node_tree.nodes.clear()
    output = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
    emission = material.node_tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.92, 0.92, 0.92, 1.0)
    emission.inputs["Strength"].default_value = 1.0
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])


def _configure_wireframe_material(material):
    material.node_tree.nodes.clear()
    output = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
    emission = material.node_tree.nodes.new("ShaderNodeEmission")
    wire = material.node_tree.nodes.new("ShaderNodeWireframe")
    wire.use_pixel_size = True
    wire.inputs["Size"].default_value = 1.25
    ramp = material.node_tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.40
    ramp.color_ramp.elements[0].color = (0.055, 0.065, 0.08, 1.0)
    ramp.color_ramp.elements[1].position = 0.60
    ramp.color_ramp.elements[1].color = (0.94, 0.94, 0.94, 1.0)
    material.node_tree.links.new(wire.outputs["Fac"], ramp.inputs["Fac"])
    material.node_tree.links.new(ramp.outputs["Color"], emission.inputs["Color"])
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])


def _configure_material(material, mode):
    if mode == "clay":
        _configure_clay_material(material)
    elif mode == "silhouette":
        _configure_silhouette_material(material)
    elif mode == "wireframe":
        _configure_wireframe_material(material)
    else:
        raise ValueError("unknown Human review mode: {}".format(mode))


def _bounds(vertices):
    minimum = [min(vertex[axis] for vertex in vertices) for axis in range(3)]
    maximum = [max(vertex[axis] for vertex in vertices) for axis in range(3)]
    return minimum, maximum


def _rotated_xy_bounds(vertices, angle_degrees):
    angle = math.radians(angle_degrees)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    xs = []
    ys = []
    for x, y, _z in vertices:
        xs.append(x * cosine - y * sine)
        ys.append(x * sine + y * cosine)
    return (min(xs), max(xs)), (min(ys), max(ys))


def _add_label(text, location, size):
    curve = bpy.data.curves.new(text + "Label", type="FONT")
    curve.body = text
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    obj = bpy.data.objects.new(text + "Label", curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    return obj


def _look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _add_lighting(center_z, scene_width, model_height):
    size = max(model_height, scene_width * 0.35)
    power_scale = (model_height / 1.8) ** 2

    key_data = bpy.data.lights.new("Key", type="AREA")
    key_data.energy = 100.0 * power_scale
    key_data.shape = "RECTANGLE"
    key_data.size = size * 0.70
    key_data.size_y = size * 0.70
    key = bpy.data.objects.new("Key", key_data)
    bpy.context.collection.objects.link(key)
    key.location = (-scene_width * 0.18, -model_height * 0.85, center_z + model_height * 0.25)
    _look_at(key, (0.0, 0.0, center_z))

    fill_data = bpy.data.lights.new("Fill", type="AREA")
    fill_data.energy = 50.0 * power_scale
    fill_data.size = size * 0.55
    fill = bpy.data.objects.new("Fill", fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (scene_width * 0.18, -model_height * 0.65, center_z)
    _look_at(fill, (0.0, 0.0, center_z))


def _validate_camera_frame(camera, review_objects, scene):
    for obj in review_objects:
        points = (vertex.co for vertex in obj.data.vertices) if obj.type == "MESH" else (
            Vector(corner) for corner in obj.bound_box
        )
        for point in points:
            projected = world_to_camera_view(scene, camera, obj.matrix_world @ point)
            if not (
                camera.data.clip_start < projected.z < camera.data.clip_end
                and 0.01 <= projected.x <= 0.99
                and 0.01 <= projected.y <= 0.99
            ):
                raise RuntimeError(
                    "Human review object {} extends outside the camera: {}".format(
                        obj.name, tuple(projected)
                    )
                )


def _configure_scene(args, part):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = args.resolution_x
    scene.render.resolution_y = args.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    world = scene.world or bpy.data.worlds.new("Human Review World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.075, 0.085, 0.10, 1.0)
        background.inputs["Strength"].default_value = 0.65

    minimum, maximum = _bounds(part.vertices)
    model_height = maximum[2] - minimum[2]
    center_z = (minimum[2] + maximum[2]) * 0.5

    rotated_bounds = [_rotated_xy_bounds(part.vertices, angle) for angle in VIEW_ROTATIONS_DEGREES]
    widths = [bounds[0][1] - bounds[0][0] for bounds in rotated_bounds]
    maximum_depth = max(bounds[1][1] - bounds[1][0] for bounds in rotated_bounds)
    gap = max(widths) * 0.28

    centers = []
    cursor = 0.0
    for width in widths:
        centers.append(cursor + width * 0.5)
        cursor += width + gap
    sheet_center = (cursor - gap) * 0.5
    positions = tuple(center - sheet_center for center in centers)
    total_width = cursor - gap

    material = _make_material()
    mesh_objects = []
    for view_name, angle, x in zip(VIEW_NAMES, VIEW_ROTATIONS_DEGREES, positions):
        obj = _make_mesh_object("Human " + view_name, part)
        x_bounds = rotated_bounds[len(mesh_objects)][0]
        obj.location.x = x - (x_bounds[0] + x_bounds[1]) * 0.5
        obj.rotation_euler.z = math.radians(angle)
        obj.data.materials.append(material)
        mesh_objects.append(obj)
        _add_label(view_name, (x, -maximum_depth * 0.60, minimum[2] - model_height * 0.075), model_height * 0.035)

    aspect = args.resolution_x / float(args.resolution_y)
    ortho_scale = max(total_width * 1.12, model_height * 1.22 * aspect)

    camera_data = bpy.data.cameras.new("Review Camera")
    camera_data.type = "ORTHO"
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.ortho_scale = ortho_scale
    camera_data.clip_start = 0.1
    camera_distance = max(model_height * 2.2, maximum_depth * 6.0, 10.0)
    camera_data.clip_end = camera_distance + max(model_height, maximum_depth) * 4.0

    camera = bpy.data.objects.new("Review Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    target_z = center_z - model_height * 0.015
    camera.location = (0.0, -camera_distance, target_z)
    _look_at(camera, (0.0, 0.0, target_z))
    scene.camera = camera

    _add_lighting(center_z, total_width, model_height)
    bpy.context.view_layer.update()
    review_objects = mesh_objects + [obj for obj in scene.objects if obj.type == "FONT"]
    _validate_camera_frame(camera, review_objects, scene)
    return material


def _mode_output(base_output, mode):
    if mode == "clay":
        return base_output
    return base_output.with_name("{}_{}{}".format(base_output.stem, mode, base_output.suffix))


def _render_modes(args, material, output):
    scene = bpy.context.scene
    for mode in args.modes:
        _configure_material(material, mode)
        bpy.context.view_layer.update()
        mode_output = _mode_output(output, mode)
        scene.render.filepath = os.fspath(mode_output)
        bpy.ops.render.render(write_still=True)
        print("Human review {} image written to: {}".format(mode, mode_output))


def main():
    args = _parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = REPO_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    _clear_scene()
    part = _human_part(args)
    material = _configure_scene(args, part)
    _render_modes(args, material, output)


if __name__ == "__main__":
    main()
