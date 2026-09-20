# SPDX-License-Identifier: GPL-3.0-or-later
"""Build representative Human V2 poses for repeatable visual deformation review.

Open this script in Blender's Scripting workspace and choose Run Script, or run:

    blender --python scripts/inspect_human_deformation.py

The scene contains a neutral reference plus seven deliberately obvious joint
poses. Each posed case is checked against both its neutral evaluated mesh and
its posed bone direction so the inspection harness rejects ineffective twists.
"""

import math
import sys
from pathlib import Path

import bpy


def _script_path():
    text = getattr(bpy.context.space_data, "text", None)
    if text is not None and text.filepath:
        return Path(bpy.path.abspath(text.filepath)).resolve()
    return Path(bpy.path.abspath(__file__)).resolve()


def _find_repo_root(start):
    for candidate in (start.parent, *start.parents):
        if (candidate / "object_core").is_dir() and (candidate / "blender_adapter").is_dir():
            return candidate
    raise RuntimeError(
        "Could not locate the Asset Assistant repository root from "
        + str(start)
        + ". Open scripts/inspect_human_deformation.py from the repository checkout before running it."
    )


def _ensure_repo_on_path():
    repo_root = _find_repo_root(_script_path())
    repo_root_text = str(repo_root)
    if repo_root_text not in sys.path:
        sys.path.insert(0, repo_root_text)


_ensure_repo_on_path()

from blender_adapter.adapter import create_asset
from object_core.objects import get_provider


# Use non-axial local rotations for the shoulder, wrist, and neck so these
# cases show an anatomical bend rather than merely twisting around the bone.
POSES = (
    ("Shoulder", "upper_arm.left", "Z", 1.05),
    ("Elbow", "forearm.left", "Z", 1.20),
    ("Wrist", "hand.left", "Z", 1.05),
    ("Hip", "upper_leg.left", "X", 0.95),
    ("Knee", "lower_leg.left", "X", 1.20),
    ("Ankle", "foot.left", "X", 1.05),
    ("Neck", "neck", "X", 0.85),
)


def _clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _human(name):
    provider = get_provider("human_experimental")
    values = {"height_cm": 180, "weight_kg": 95, "body_type": "average"}
    mesh = provider.mesh(values)
    skeleton = provider.skeleton(values)
    weights = provider.skin_weights(mesh, values)
    root = create_asset(mesh, name=name, skeleton=skeleton, skin_weights=weights)
    obj = next(child for child in root.children if child.type == "MESH")
    armature = next(child for child in root.children if child.type == "ARMATURE")
    return root, obj, armature


def _evaluated_local_points(obj):
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(graph)
    return [vertex.co.copy() for vertex in evaluated.data.vertices]


def _label(name, location):
    bpy.ops.object.text_add(location=location)
    label = bpy.context.object
    label.name = name + "_Label"
    label.data.body = name
    label.data.align_x = "CENTER"
    label.data.size = 0.12
    label.rotation_euler.x = math.radians(90.0)


def _apply_and_verify_pose(name, obj, armature, bone_name, axis, angle):
    bpy.context.view_layer.update()
    before = _evaluated_local_points(obj)

    pose_bone = armature.pose.bones[bone_name]
    neutral_tail = pose_bone.tail.copy()
    pose_bone.rotation_mode = "XYZ"
    setattr(pose_bone.rotation_euler, axis.lower(), angle)
    bpy.context.view_layer.update()

    after = _evaluated_local_points(obj)
    max_displacement = max((posed - neutral).length for neutral, posed in zip(before, after))
    tail_displacement = (pose_bone.tail - neutral_tail).length

    if max_displacement <= 1e-3:
        raise RuntimeError(
            name + " inspection pose did not deform the evaluated mesh "
            + "(max displacement {:.6f} m)".format(max_displacement)
        )
    if tail_displacement <= 1e-3:
        raise RuntimeError(
            name + " inspection pose only twists around the bone axis instead of showing a bend "
            + "(bone-tail displacement {:.6f} m)".format(tail_displacement)
        )
    print(
        "{} pose verified: max mesh displacement {:.4f} m; bone-tail displacement {:.4f} m".format(
            name, max_displacement, tail_displacement
        )
    )


def main():
    _clear_scene()
    cases = (("Neutral", None, None, 0.0),) + POSES

    columns = 4
    column_spacing = 1.4
    row_spacing = 2.4
    x_offset = -column_spacing * (columns - 1) / 2.0
    y_offset = row_spacing / 2.0

    for index, (name, bone_name, axis, angle) in enumerate(cases):
        row, column = divmod(index, columns)
        x = x_offset + column * column_spacing
        y = y_offset - row * row_spacing
        root, obj, armature = _human("Human_" + name)
        root.location.x = x
        root.location.y = y
        _label(name, (x, y - 0.42, 1.95))

        if bone_name is not None:
            _apply_and_verify_pose(name, obj, armature, bone_name, axis, angle)

    bpy.context.view_layer.update()
    print("Human deformation inspection verified: Neutral + " + ", ".join(name for name, *_ in POSES))


if __name__ == "__main__":
    main()
