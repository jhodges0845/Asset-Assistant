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


def localize_upper_body_weights(mesh, skeleton, weights, arm_owners):
    """Fade torso-child influence below its attachment on non-arm vertices.

    The shared nearest-bone solver includes children of the long torso bone.
    Distance falloff alone therefore assigns neck/arm weights down to the hips.
    Transfer that remote influence to the torso, preserving the total and the
    existing shoulder blend. Authored arms retain their chain weights unchanged.
    """
    bones = {bone.name: bone for bone in skeleton.bones}
    torso = bones['torso']
    blend_height = (torso.tail[2] - torso.head[2]) * .25
    neck_top = bones['neck'].head[2]
    lower_torso_top = (torso.head[2] + torso.tail[2]) * .5
    result = []
    for part, skin in zip(mesh.parts, weights):
        # Preserve the original weights on both sides of each authored arm join.
        # Starting the fade at the bone head would modify torso-side collar
        # vertices while leaving their arm-owned neighbors unchanged.
        join_heights = {}
        for face in part.faces:
            for first, second in zip(face, face[1:] + face[:1]):
                a, b = arm_owners.get(first), arm_owners.get(second)
                if (a is None) != (b is None):
                    side, body_index = (a, second) if a is not None else (b, first)
                    z = part.vertices[body_index][2]
                    join_heights[side] = min(join_heights.get(side, z), z)
        bands = {'neck': (neck_top - blend_height, neck_top)}
        for side in ('left', 'right'):
            top = join_heights[side]
            # Extreme semantic edits can lower a join; retain a nonzero band.
            top = max(top, lower_torso_top + blend_height * .1)
            bands['upper_arm.' + side] = (lower_torso_top, top)
        vertices = []
        for index, (point, influences) in enumerate(zip(part.vertices, skin.vertices)):
            if index in arm_owners:
                vertices.append(influences)
                continue
            adjusted = {}
            transferred = 0.0
            for influence in influences:
                factor = 1.0
                if influence.bone_name in bands:
                    bottom, top = bands[influence.bone_name]
                    t = max(0.0, min(1.0, (point[2] - bottom) / (top - bottom)))
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
