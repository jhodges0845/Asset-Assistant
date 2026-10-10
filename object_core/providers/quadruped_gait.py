# SPDX-License-Identifier: GPL-3.0-or-later
"""Contact-driven canine joint rotations against the canonical weighted surface."""
from dataclasses import dataclass
from functools import lru_cache
from math import cos, sin, pi

from ..animation.contact import ContactCycle
from ..animation.idle import IdleClip, RotationTrack, TranslationTrack
from ..animation.walk import WalkClip
from ..animation.run import RunClip


@dataclass(frozen=True)
class ContactIdleClip(IdleClip):
    translations: tuple


@dataclass(frozen=True)
class ContactWalkClip(WalkClip):
    translations: tuple


@dataclass(frozen=True)
class ContactRunClip(RunClip):
    translations: tuple


def contact_schedule(duration, strength, height, running=False):
    # Deliberate four-beat walk; the run is a diagonal trot with flight intervals.
    phases = ((0, .5, .75, .25) if not running else (0, .5, .5, 0))
    names = ('leg.front.left', 'leg.front.right', 'leg.hind.left', 'leg.hind.right')
    return {name: ContactCycle(duration, height * (.30 if running else .20) * strength,
                              .4 if running else .65, height * (.10 if running else .06) * strength,
                              phase) for name, phase in zip(names, phases)}


def _body_crouch(height, strength, running, phase):
    """Bounded stylized compression, in centimeters below the neutral root.

    Walk has a small pulse between each footfall. Trot compresses mid-stance
    and rises in flight. This is authored body response, not a dynamics model.
    """
    beats, center, amplitude = (2, .2, .014) if running else (4, .125, .006)
    compression = .5 + .5 * cos(2 * pi * beats * ((phase % 1.) - center))
    return height * strength * (.07 + amplitude * compression)


def _swing_paw_pitch(schedule, phase, strength):
    """Hind-paw curl in flight, with zero pitch and slope at both contacts."""
    local = (phase - schedule.touchdown_phase) % 1.
    if local <= schedule.duty_factor:
        return 0.
    u = (local - schedule.duty_factor) / (1. - schedule.duty_factor)
    return .12 * strength * sin(pi * u) ** 2


class _LimbSurface:
    """Exact planar linear-blend skinning for this limb's contact solve."""
    def __init__(self, mesh, weights, region, bones, crouch):
        self.heads = tuple(b.head[1:] for b in bones)
        self.crouch = crouch
        self.paw_pitch = 0.
        names = {b.name: i for i, b in enumerate(bones)}
        vertices = mesh.parts[0].vertices
        indices = tuple(region.vertex_indices)
        # Include every authored limb vertex, so the contact envelope cannot
        # overlook a higher rest vertex that rotates below the neutral sole.
        self.rows = tuple(tuple((names.get(w.bone_name, -1), w.weight,
                                vertices[i][1] * w.weight, vertices[i][2] * w.weight)
                               for w in weights.vertices[i]) for i in indices)
        sole = tuple(i for i in indices if 0 <= vertices[i][2] <= .1)
        if not sole:
            raise ValueError('Contact gait requires a grounded neutral sole')
        self.neutral_y = sum(vertices[i][1] for i in sole) / len(sole)
        sums = [[0., 0., 0.] for _ in range(len(bones) + 1)]
        for i in sole:
            for w in weights.vertices[i]:
                row = sums[names.get(w.bone_name, -1)]
                row[0] += w.weight / len(sole)
                row[1] += w.weight * vertices[i][1] / len(sole)
                row[2] += w.weight * vertices[i][2] / len(sole)
        self.centroid = tuple(sums)

    def transforms(self, angles):
        angles = tuple(angles) + ((self.paw_pitch-sum(angles),) if len(self.heads) == 3 else ())
        transforms = []
        c, s, ty, tz, total = 1., 0., 0., -self.crouch, 0.
        for (hy, hz), angle in zip(self.heads, angles):
            py, pz = c*hy - s*hz + ty, s*hy + c*hz + tz
            total += angle
            c, s = cos(total), sin(total)
            ty, tz = py - c*hy + s*hz, pz - s*hy - c*hz
            transforms.append((c, s, ty, tz))
        transforms.append((1., 0., 0., -self.crouch))
        return transforms

    def measure(self, angles):
        transforms = self.transforms(angles)
        y = sum(c*wy - s*wz + ty*w for (w, wy, wz), (c, s, ty, tz)
                in zip(self.centroid, transforms))
        lowest = min(sum(transforms[i][1]*wy + transforms[i][0]*wz + transforms[i][3]*w
                         for i, w, wy, wz in row) for row in self.rows)
        return y, lowest

    def solve(self, target_y, target_z, seed):
        angles = list(seed)
        for _ in range(45):
            y, z = self.measure(angles)
            ey, ez = target_y-y, target_z-z
            if max(abs(ey), abs(ez)) < 1e-6:
                return tuple(angles)
            eps = 1e-5
            ya, za = self.measure((angles[0]+eps, angles[1]))
            yb, zb = self.measure((angles[0], angles[1]+eps))
            a, b, c, d = (ya-y)/eps, (yb-y)/eps, (za-z)/eps, (zb-z)/eps
            det = a*d-b*c
            if abs(det) < 1e-9:
                break
            da, db = (d*ey-b*ez)/det, (a*ez-c*ey)/det
            scale = min(1., .15 / max(abs(da), abs(db), 1e-12))
            angles[0] += da*scale
            angles[1] += db*scale
            if max(abs(v) for v in angles) > 2.6:
                break
        raise ValueError('Canine contact target is unreachable with the current limb proportions')


@lru_cache(maxsize=24)
def generate_contact_clip(duration, strength, running, parameters, recipe_identity):
    from .quadruped import QuadrupedProvider, _construction
    from .quadruped_rigging import _build_quadruped_skeleton, generate_quadruped_skin_weights
    provider = QuadrupedProvider()
    mesh, anatomy = _construction(provider.dimensions(dict(parameters)))
    if (anatomy.recipe_id, anatomy.recipe_version) != recipe_identity:
        raise ValueError('Contact gait recipe identity does not match the construction')
    skeleton = _build_quadruped_skeleton(anatomy)
    weights = generate_quadruped_skin_weights(mesh, skeleton, anatomy=anatomy)[0]
    height = dict(parameters)['shoulder_height_cm']
    crouch = _body_crouch(height, strength, running, 0.)
    schedules = contact_schedule(duration, strength, height, running)
    bones = {b.name: b for b in skeleton.bones}
    regions = {r.name: r for r in anatomy.regions}
    tracks = []
    # Dense samples limit quaternion interpolation's deviation from solved
    # surface targets. A 0.02 cm clearance margin covers measured interpolation.
    samples = 128
    for chain in anatomy.chains:
        if chain.name not in schedules:
            continue
        surface = _LimbSurface(mesh, weights, regions[chain.name],
                               tuple(bones[n] for n in chain.bones), crouch)
        schedule = schedules[chain.name]
        seed = (-.3, .6) if '.front.' in chain.name else (.2, -.4)
        keys = [[] for _ in chain.bones]
        for i in range(samples):
            surface.crouch = _body_crouch(height, strength, running, i / samples)
            surface.paw_pitch = _swing_paw_pitch(schedule, i / samples, strength) if len(chain.bones) == 3 else 0.
            target = schedule.target(i / samples)
            seed = surface.solve(surface.neutral_y + target.forward_cm, target.lift_cm + .02, seed)
            angles = seed + ((surface.paw_pitch-sum(seed),) if len(chain.bones) == 3 else ())
            for row, angle in zip(keys, angles):
                row.append((duration * i / samples, angle))
        for name, row in zip(chain.bones, keys):
            row.append((duration, row[0][1]))
            tracks.append(RotationTrack(name, (1., 0., 0.), tuple(row)))
    from .quadruped_animation import _closed_wave
    for name, degrees, phase in (('neck', 2., pi), ('tail.1', 7., pi),
                                 ('tail.2', 10., 1.5*pi), ('tail.3', 12., 0.)):
        wave = _closed_wave(duration, degrees, strength, phase=phase)
        wave = wave[:-1] + ((duration, wave[0][1]),)
        tracks.append(RotationTrack(name, (1., 0., 0.) if name == 'neck' else (0., 0., 1.), wave))
    root_keys = tuple((duration * i / samples,
                       (0., 0., -_body_crouch(height, strength, running, i / samples)))
                      for i in range(samples))
    translation = TranslationTrack('root', root_keys + ((duration, root_keys[0][1]),))
    return (ContactRunClip if running else ContactWalkClip)(duration, tuple(tracks), (translation,))
