# SPDX-License-Identifier: GPL-3.0-or-later
"""Human rest rig and attachment-local weight constraints."""
from ..models.skeleton import Bone, Skeleton
from ..models.skinning import BoneWeight, SkinWeights


def surface_skeleton(anatomy):
    points = {landmark.name: landmark.position for landmark in anatomy.landmarks}
    bones = []
    for chain in anatomy.chains:
        parent = chain.parent_bone
        for index, name in enumerate(chain.bones):
            bones.append(Bone(name, points[chain.landmarks[index]],
                              points[chain.landmarks[index + 1]], parent))
            parent = name
    return Skeleton(tuple(bones))


def localize_upper_body_weights(mesh, skeleton, weights, arm_indices):
    """Fade torso-child influence below its attachment on non-arm vertices.

    The shared nearest-bone solver includes children of the long torso bone.
    Distance falloff alone therefore assigns neck/arm weights down to the hips.
    Transfer that remote influence to the torso, preserving the total and the
    existing shoulder blend. Authored arms retain their chain weights unchanged.
    """
    bones = {bone.name: bone for bone in skeleton.bones}
    torso = bones['torso']
    blend_height = (torso.tail[2] - torso.head[2]) * .25
    attachments = {name: bones[name].head[2]
                   for name in ('neck', 'upper_arm.left', 'upper_arm.right')}
    result = []
    for part, skin in zip(mesh.parts, weights):
        vertices = []
        for index, (point, influences) in enumerate(zip(part.vertices, skin.vertices)):
            if index in arm_indices:
                vertices.append(influences)
                continue
            adjusted = {}
            transferred = 0.0
            for influence in influences:
                factor = 1.0
                if influence.bone_name in attachments:
                    t = max(0.0, min(1.0, (point[2] - attachments[influence.bone_name]
                                          + blend_height) / blend_height))
                    factor = t * t * (3.0 - 2.0 * t)
                retained = influence.weight * factor
                transferred += influence.weight - retained
                if retained > 0:
                    adjusted[influence.bone_name] = retained
            if transferred == 0:
                vertices.append(influences)
                continue
            adjusted['torso'] = adjusted.get('torso', 0.0) + transferred
            total = sum(adjusted.values())
            vertices.append(tuple(BoneWeight(name, value / total) for name, value in adjusted.items()))
        result.append(SkinWeights(skin.part_name, tuple(vertices)))
    return tuple(result)
