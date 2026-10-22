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


def localize_arm_joint_weights(mesh, skeleton, weights, arm_owners):
    """Keep the shoulder collar free of distant elbow deformation.

    Project authored arm vertices along the upper-arm rest segment. Torso
    influence fades by the segment midpoint; forearm influence starts there
    and reaches the shared solver's full value in the distal quarter.
    Removed influence transfers to the upper arm, retaining normalized weights.
    """
    bones = {b.name: b for b in skeleton.bones}
    result = []
    for part, skin in zip(mesh.parts, weights):
        rows = list(skin.vertices)
        for index, side in arm_owners.items():
            upper = 'upper_arm.' + side
            bone = bones[upper]
            axis = tuple(b-a for a,b in zip(bone.head, bone.tail))
            point = part.vertices[index]
            t = sum((p-a)*d for p,a,d in zip(point, bone.head, axis)) / sum(d*d for d in axis)
            row = {w.bone_name:w.weight for w in rows[index]}
            changed = False
            for name, factor in (
                    ('forearm.' + side, max(0., min(1., (t-.5)/.25))),
                    ('torso', 1.-max(0., min(1., (t-.25)/.25)))):
                factor = factor * factor * (3.-2.*factor)
                weight = row.get(name, 0.)
                transfer = weight * (1.-factor)
                if transfer:
                    row[name] = weight-transfer
                    row[upper] = row.get(upper, 0.)+transfer
                    changed = True
            if changed:
                total = sum(row.values())
                rows[index] = tuple(BoneWeight(name, value/total)
                                    for name,value in row.items() if value > 0.)
        result.append(SkinWeights(skin.part_name, tuple(rows)))
    return tuple(result)


def blend_hip_weights(mesh, skeleton, weights, arm_owners):
    """Replace discontinuous nearest-bone hip switches with a continuous field.

    Blend torso to thighs vertically and both thighs across the pelvic midline.
    Smoothly restore the shared solver below the upper thigh and above the pelvis;
    authored arms and distal joint weights remain unchanged.
    """
    bones = {bone.name: bone for bone in skeleton.bones}
    left, right = bones['upper_leg.left'], bones['upper_leg.right']
    hip_z = (left.head[2] + right.head[2]) * .5
    thigh = ((left.head[2]-left.tail[2]) + (right.head[2]-right.tail[2])) * .5
    half_width = abs(left.head[0]-right.head[0]) * .25

    def smooth(t):
        t = max(0., min(1., t))
        return t*t*(3.-2.*t)

    result = []
    for part, skin in zip(mesh.parts, weights):
        rows = []
        for index, (point, original) in enumerate(zip(part.vertices, skin.vertices)):
            x, _, z = point
            blend = (smooth((z-(hip_z-.65*thigh))/(.2*thigh))
                     * (1.-smooth((z-(hip_z+.4*thigh))/(.15*thigh))))
            if index in arm_owners or blend == 0.:
                rows.append(original)
                continue
            leg = 1.-smooth((z-(hip_z-.45*thigh))/(.65*thigh))
            side = smooth((x+half_width)/(2.*half_width))
            target = {'torso': 1.-leg, 'upper_leg.left': leg*side,
                      'upper_leg.right': leg*(1.-side)}
            row = {w.bone_name: w.weight*(1.-blend) for w in original}
            for name, value in target.items():
                row[name] = row.get(name, 0.) + blend*value
            total = sum(row.values())
            rows.append(tuple(BoneWeight(name, value/total)
                              for name,value in row.items() if value > 0.))
        result.append(SkinWeights(skin.part_name, tuple(rows)))
    return tuple(result)


def blend_ankle_weights(mesh, skeleton, weights, leg_owners):
    """Blend the refined heel/instep into the shin without compressing the sole."""
    bones = {bone.name:bone for bone in skeleton.bones}
    def smooth(t):
        t = max(0.,min(1.,t))
        return t*t*(3.-2.*t)
    result = []
    for part,skin in zip(mesh.parts,weights):
        rows = list(skin.vertices)
        for index,side in leg_owners.items():
            foot = bones['foot.'+side]
            shin = bones['lower_leg.'+side]
            length = shin.head[2]-shin.tail[2]
            x,y,z = part.vertices[index]
            blend = 1.-smooth((z-foot.head[2]-.25*length)/(.1*length))
            if blend == 0.: continue
            vertical = smooth((foot.head[2]+.2*length-z)/(.4*length))
            influence = vertical
            row = {w.bone_name:w.weight*(1.-blend) for w in rows[index]}
            for name,value in (('foot.'+side,influence),('lower_leg.'+side,1.-influence)):
                row[name] = row.get(name,0.)+blend*value
            total = sum(row.values())
            rows[index] = tuple(BoneWeight(name,value/total) for name,value in row.items() if value>0.)
        result.append(SkinWeights(skin.part_name,tuple(rows)))
    return tuple(result)
