# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender-independent deforming rig and skin-weight generation for Human 1.0."""

from math import sqrt

from ..models.mesh import ObjectMesh
from ..models.proportions import HumanoidProportions
from ..models.skeleton import Bone, Skeleton
from ..models.skinning import BoneWeight, SkinWeights
from ..proportions.landmarks import generate_landmarks


def generate_deforming_skeleton(proportions: HumanoidProportions) -> Skeleton:
    """Return the Human 1.0 skeleton without legacy rigid-part bindings."""
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")
    points = generate_landmarks(proportions)
    hip = points["hip_center"]
    bones = [
        Bone("root", hip, (hip[0], hip[1], hip[2] + proportions.torso_length_cm * 0.1)),
        Bone("torso", hip, points["shoulder_center"], "root"),
        Bone("neck", points["shoulder_center"], points["chin"], "torso"),
        Bone("head", points["chin"], points["crown"], "neck"),
    ]
    for side in ("left", "right"):
        bones.extend(
            (
                Bone("upper_arm." + side, points["shoulder." + side], points["elbow." + side], "torso"),
                Bone("forearm." + side, points["elbow." + side], points["wrist." + side], "upper_arm." + side),
                Bone("hand." + side, points["wrist." + side], points["fingertips." + side], "forearm." + side),
                Bone("upper_leg." + side, points["hip." + side], points["knee." + side], "root"),
                Bone("lower_leg." + side, points["knee." + side], points["ankle." + side], "upper_leg." + side),
                Bone("foot." + side, points["ankle." + side], points["toe." + side], "lower_leg." + side),
            )
        )
    return Skeleton(tuple(bones))


def _distance(a, b):
    return sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _distance_to_segment(point, start, end):
    axis = tuple(end[i] - start[i] for i in range(3))
    offset = tuple(point[i] - start[i] for i in range(3))
    length_sq = sum(value * value for value in axis)
    amount = sum(offset[i] * axis[i] for i in range(3)) / length_sq
    amount = max(0.0, min(1.0, amount))
    closest = tuple(start[i] + axis[i] * amount for i in range(3))
    return _distance(point, closest)


def _candidate_bones(vertex, bones):
    """Keep skinning local enough to prevent left/right limb cross-influence."""
    x = vertex[0]
    side = "left" if x >= 0 else "right"
    return tuple(
        bone for bone in bones
        if not (bone.name.endswith(".left") or bone.name.endswith(".right"))
        or bone.name.endswith("." + side)
    )


def _human_hip_bridge_names(vertex, nearest, candidates):
    """Bridge torso and same-side upper leg near the non-deforming root."""
    by_name = {bone.name: bone for bone in candidates}
    side = "left" if vertex[0] >= 0 else "right"
    upper_leg_name = "upper_leg." + side
    torso = by_name.get("torso")
    upper_leg = by_name.get(upper_leg_name)
    if torso is None or upper_leg is None:
        return set()

    bridge_radius = _distance(torso.head, upper_leg.head) * 1.5
    if nearest.name == "torso" and _distance(vertex, torso.head) <= bridge_radius:
        return {"torso", upper_leg_name}
    if nearest.name == upper_leg_name and _distance(vertex, upper_leg.head) <= bridge_radius:
        return {"torso", upper_leg_name}
    return set()


def _local_joint_bones(vertex, bones, max_influences):
    """Return the nearest deform bone and its local Human joint neighbors."""
    candidates = _candidate_bones(vertex, bones)
    ranked = sorted(
        ((_distance_to_segment(vertex, bone.head, bone.tail), bone) for bone in candidates),
        key=lambda item: (item[0], item[1].name),
    )
    nearest = ranked[0][1]

    hip_bridge_names = _human_hip_bridge_names(vertex, nearest, candidates)
    if hip_bridge_names:
        local = [(distance, bone) for distance, bone in ranked if bone.name in hip_bridge_names]
        return local[:max_influences]

    connected_names = {nearest.name}
    if nearest.parent:
        connected_names.add(nearest.parent)
    connected_names.update(bone.name for bone in candidates if bone.parent == nearest.name)
    local = [(distance, bone) for distance, bone in ranked if bone.name in connected_names]
    return local[:max_influences]


def _uses_soft_joint_transition(ranked):
    """Use gentler falloff across Human joints that visibly bend or compress."""
    names = {bone.name for _distance_value, bone in ranked}
    if {"torso", "neck"} <= names:
        return True
    for side in ("left", "right"):
        pairs = (
            ("torso", "upper_arm." + side),
            ("torso", "upper_leg." + side),
            ("upper_arm." + side, "forearm." + side),
            ("forearm." + side, "hand." + side),
            ("upper_leg." + side, "lower_leg." + side),
            ("lower_leg." + side, "foot." + side),
        )
        if any(set(pair) <= names for pair in pairs):
            return True
    return False


def _weights_for_vertex(vertex, bones, max_influences=4):
    ranked = _local_joint_bones(vertex, bones, max_influences)
    # Major Human joints looked hinge-like with inverse-square falloff. Keep the
    # same strictly local bone neighborhoods, but use a gentler inverse-linear
    # blend where supported topology is intended to share deformation.
    if _uses_soft_joint_transition(ranked):
        epsilon = 2e-2
        power = 1.0
    else:
        epsilon = 1e-3
        power = 2.0
    raw = [(bone.name, 1.0 / ((distance + epsilon) ** power)) for distance, bone in ranked]
    total = sum(value for _, value in raw)
    normalized = [(name, value / total) for name, value in raw]
    correction = 1.0 - sum(value for _, value in normalized)
    name, value = normalized[0]
    normalized[0] = (name, value + correction)
    return tuple(BoneWeight(name, value) for name, value in normalized if value > 0.0)


def generate_skin_weights(mesh: ObjectMesh, skeleton: Skeleton, *, max_influences=4):
    """Return deterministic normalized weights for each vertex of each mesh part."""
    if not isinstance(mesh, ObjectMesh):
        raise TypeError("mesh must be ObjectMesh")
    if not isinstance(skeleton, Skeleton):
        raise TypeError("skeleton must be Skeleton")
    if isinstance(max_influences, bool) or not isinstance(max_influences, int):
        raise TypeError("max_influences must be an integer")
    if max_influences < 1:
        raise ValueError("max_influences must be at least 1")
    deform_bones = tuple(bone for bone in skeleton.bones if bone.name != "root")
    if not deform_bones:
        raise ValueError("skeleton must contain deform bones")
    return tuple(
        SkinWeights(
            part.name,
            tuple(_weights_for_vertex(vertex, deform_bones, max_influences) for vertex in part.vertices),
        )
        for part in mesh.parts
    )
