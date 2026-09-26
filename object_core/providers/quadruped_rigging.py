# SPDX-License-Identifier: GPL-3.0-or-later
"""Quadruped rig and skin-weight generation."""

from math import sqrt

from ..models import Bone, BoneWeight, Skeleton, SkinWeights
from .quadruped_anatomy import QuadrupedFrontRecipe


def generate_quadruped_skeleton(dimensions):
    """Build a deterministic quadruped skeleton from validated dimensions."""
    return _build_quadruped_skeleton(dimensions, QuadrupedFrontRecipe().resolve(dimensions))


def _build_quadruped_skeleton(dimensions, anatomy):
    """Consume the same proof landmarks as surface construction."""
    landmarks = {landmark.name: landmark.position for landmark in anatomy.landmarks}
    length = dimensions["body_length_cm"]
    shoulder = dimensions["shoulder_height_cm"]
    width = dimensions["body_width_cm"]
    head_length = dimensions["head_length_cm"]
    tail_length = dimensions["tail_length_cm"]

    torso_height = shoulder * 0.42
    torso_z = shoulder - torso_height * 0.48
    back_z = torso_z + torso_height * 0.18
    fore_y = length * 0.32
    hind_y = -length * 0.32
    leg_height = shoulder - torso_height * 0.45
    knee_z = leg_height * 0.48
    side_x = width * 0.34
    head_y = length * 0.5 + head_length * 0.28
    neck_y = length * 0.5
    tail_segment = max(tail_length / 3, 2.0)
    tail_base_y = -length * 0.5

    bones = [
        Bone("root", landmarks["root.base"], landmarks["root.tip"]),
        Bone("spine", landmarks["spine.hind"], landmarks["spine.fore"], "root"),
        Bone("neck", (0, fore_y, back_z), (0, neck_y, shoulder), "spine"),
        Bone("head", (0, neck_y, shoulder),
             (0, head_y + head_length * 0.35, shoulder + torso_height * 0.08), "neck"),
    ]

    for side, x in (("left", -side_x), ("right", side_x)):
        upper, elbow, ground = (x, fore_y, shoulder), (x, fore_y, knee_z), (x, fore_y, 0)
        if side == "left":
            upper = landmarks["shoulder.front.left"]
            elbow = landmarks["elbow.front.left"]
            ground = landmarks["ground.front.left"]
        bones.extend((
            Bone("fore_upper." + side, upper, elbow, "spine"),
            Bone("fore_lower." + side, elbow, ground, "fore_upper." + side),
            Bone("hind_upper." + side, (x, hind_y, shoulder * 0.86), (x, hind_y, knee_z), "spine"),
            Bone("hind_lower." + side, (x, hind_y, knee_z), (x, hind_y, 0), "hind_upper." + side),
        ))

    parent = "spine"
    start_y = tail_base_y
    start_z = back_z
    for index in range(3):
        end_y = start_y - tail_segment * 0.75
        end_z = start_z + torso_height * 0.12
        name = "tail.%d" % (index + 1)
        bones.append(Bone(name, (0, start_y, start_z), (0, end_y, end_z), parent))
        parent = name
        start_y, start_z = end_y, end_z

    return Skeleton(tuple(bones))


def _distance_to_segment(point, start, end):
    axis = tuple(end[i] - start[i] for i in range(3))
    offset = tuple(point[i] - start[i] for i in range(3))
    length_sq = sum(value * value for value in axis)
    amount = sum(offset[i] * axis[i] for i in range(3)) / length_sq
    amount = max(0.0, min(1.0, amount))
    closest = tuple(start[i] + axis[i] * amount for i in range(3))
    return sqrt(sum((point[i] - closest[i]) ** 2 for i in range(3)))


def _candidate_bones(vertex, bones):
    """Prevent a vertex from being influenced by the opposite-side limb."""
    side = "left" if vertex[0] <= 0 else "right"
    return tuple(
        bone for bone in bones
        if not (bone.name.endswith(".left") or bone.name.endswith(".right"))
        or bone.name.endswith("." + side)
    )


def _weights_for_vertex(vertex, bones, max_influences=4):
    candidates = _candidate_bones(vertex, bones)
    ranked = sorted(
        ((_distance_to_segment(vertex, bone.head, bone.tail), bone) for bone in candidates),
        key=lambda item: (item[0], item[1].name),
    )
    nearest = ranked[0][1]
    local_names = {nearest.name}
    if nearest.parent:
        local_names.add(nearest.parent)
    local_names.update(bone.name for bone in candidates if bone.parent == nearest.name)
    local = [(distance, bone) for distance, bone in ranked if bone.name in local_names][:max_influences]
    raw = [(bone.name, 1.0 / ((distance + 1e-3) ** 2)) for distance, bone in local]
    total = sum(value for _name, value in raw)
    normalized = [(name, value / total) for name, value in raw]
    correction = 1.0 - sum(value for _name, value in normalized)
    normalized[0] = (normalized[0][0], normalized[0][1] + correction)
    return tuple(BoneWeight(name, value) for name, value in normalized if value > 0)


def generate_quadruped_skin_weights(mesh, skeleton, *, max_influences=4):
    """Return normalized local weights for a connected quadruped surface."""
    deform_bones = tuple(bone for bone in skeleton.bones if bone.name != "root")
    if not deform_bones:
        raise ValueError("Quadruped skeleton must contain deform bones")
    return tuple(
        SkinWeights(
            part.name,
            tuple(_weights_for_vertex(vertex, deform_bones, max_influences) for vertex in part.vertices),
        )
        for part in mesh.parts
    )
