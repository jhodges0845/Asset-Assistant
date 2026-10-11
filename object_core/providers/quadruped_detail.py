# SPDX-License-Identifier: GPL-3.0-or-later
"""Construction-only facial relief on the connected authored head surface.

Features use bounded, smooth displacements rather than separate floating meshes.
They inherit the existing head/muzzle region ownership and semantic transforms.
"""
from math import exp, sqrt


def shape_canine_face(vertices, anatomy):
    points = {p.name: p.position for p in anatomy.landmarks}
    sections = {s.landmark: s for s in anatomy.body_sections}
    regions = {r.name: set(r.vertex_indices) for r in anatomy.regions}
    owned = regions['head'] - regions['ear.left'] - regions['ear.right']
    head, muzzle, tip = (points[n] for n in ('head.center', 'muzzle.base', 'muzzle.tip'))
    size = tip[1] - head[1]
    depth = sections['head.center'].depth_cm
    width = sections['head.center'].width_cm
    eye_y, eye_z = head[1] + size * .19, head[2] - depth * .065
    result = list(vertices)
    front = max(vertices[i][1] for i in owned)
    for i in owned:
        x, y, z = vertices[i]
        # Lateral relief has no effect on the midline, ears or neck attachment.
        lateral = min(1., abs(x) / max(width * .22, 1e-9)) ** 2
        radius = sqrt(((y-eye_y)/(size*.15))**2 + ((z-eye_z)/(depth*.085))**2)
        # A recessed orbit, raised eyelid rim and small convex central eye.
        eye = (-.030 * exp(-(radius/.95)**4)
               + .012 * exp(-((radius-.95)/.25)**2)
               + .067 * exp(-(radius/.55)**2)) * min(width, depth)
        # Closed mouth: an inset lip line with a slightly raised lower lip.
        along = (y - muzzle[1]) / max(front-muzzle[1], 1e-9)
        mouth_fade = max(0., 1.-((along-.42)/.65)**2)**2
        mouth_z = muzzle[2] - sections['muzzle.base'].depth_cm * .13
        dz = (z-mouth_z) / max(depth*.027, 1e-9)
        lip = depth * mouth_fade * (-.028*exp(-dz*dz) + .011*exp(-((dz+1.8)/1.1)**2))
        offset = (eye + lip) * lateral
        # Preserve lateral ordering and avoid a crease crossing the midline.
        nx = x + (1 if x >= 0 else -1) * max(-abs(x)*.15, offset)
        # Rounded nose leather and paired nostril recesses on the end of snout.
        nose = exp(-((front-y)/(size*.085))**2)
        nose_z = tip[2] + sections['muzzle.tip'].depth_cm*.08
        nose_width = sections['muzzle.tip'].width_cm
        bulb = exp(-((z-nose_z)/(depth*.18))**4)
        nostril = exp(-((abs(x)-nose_width*.27)/(nose_width*.12))**2
                      -((z-nose_z)/(depth*.045))**2)
        ny = y + size * nose * (.035*bulb - .025*nostril)
        result[i] = (nx, ny, z)
    return tuple(result)


def shape_canine_paw_detail(vertices, anatomy):
    """Shallow sole-pad borders and four dorsal claw tips, kept limb-owned.

    Pad grooves only lift the underside; exact ground vertices stay fixed.
    Claws are restrained connected relief, not separate articulated digits.
    """
    points = {p.name: p.position for p in anatomy.landmarks}
    result = list(vertices)
    for region in anatomy.regions:
        if not region.name.startswith('leg.'):
            continue
        suffix = region.name[4:]
        cx, _, ground = points['ground.' + suffix]
        upper = points[('ankle.' if suffix.startswith('front.') else 'hock.') + suffix][2]
        height = min(anatomy.paw_profile.height_cm, upper-ground)
        low = [i for i in region.vertex_indices if vertices[i][2] < ground+height]
        radius = max(abs(vertices[i][0]-cx) for i in low)
        rear = min(vertices[i][1] for i in low)
        length = max(vertices[i][1] for i in low)-rear
        for i in low:
            x, y, z = vertices[i]
            u, f, t = (x-cx)/radius, (y-rear)/length, (z-ground)/height
            # An outlined central pad and four digital pads on the underside.
            central = sqrt((u/.56)**2 + ((f-.35)/.25)**2)
            groove = exp(-((central-1.)/.12)**2)
            claw = 0.
            for center in (-.72, -.24, .24, .72):
                digital = sqrt(((u-center)/.18)**2 + ((f-.77)/.15)**2)
                groove = max(groove, exp(-((digital-1.)/.13)**2))
                claw += exp(-((u-center)/.105)**2)
            sole = max(0., 1.-t/.24)**2 * t/(t+.012)
            nz = z + height*.10*groove*sole
            forward = max(0., min(1., (f-.72)/.28))
            ny = y + length*.10*claw*forward**2 * 16*t*t*(1-t)**2
            result[i] = (x, ny, nz)
    return tuple(result)
