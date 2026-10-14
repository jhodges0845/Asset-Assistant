# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from object_core.objects import get_provider
from object_core.providers.avian_animation import (
    generate_avian_flight,
    generate_avian_idle,
    generate_avian_walk,
)


class AvianAnimationTests(unittest.TestCase):
    def test_provider_exposes_idle_walk_and_flight_without_run(self):
        provider = get_provider("avian")
        self.assertTrue(provider.supports_idle)
        self.assertTrue(provider.supports_locomotion)
        self.assertTrue(provider.supports_flight)
        self.assertFalse(provider.supports_run)
        self.assertEqual(provider.locomotion_label, "Walk")
        self.assertTrue(callable(provider.flight))

    def test_idle_is_closed_and_moves_head_tail_with_folded_wings(self):
        clip = generate_avian_idle(4.0, 1.0)
        self.assertEqual(clip, generate_avian_idle(4.0, 1.0))
        by_bone = {track.bone: track for track in clip.tracks}
        self.assertTrue({"neck", "head", "wing.upper.left", "wing.upper.right",
                         "tail.1", "tail.2"}.issubset(by_bone))
        for track in clip.tracks:
            self.assertAlmostEqual(track.keys[0][1], track.keys[-1][1])

    def test_walk_is_closed_and_alternates_leg_chains(self):
        clip = generate_avian_walk(1.2, 1.0)
        by_bone = {track.bone: track for track in clip.tracks}
        self.assertEqual(set(by_bone), {"leg.upper.left", "leg.upper.right",
                         "leg.lower.left", "leg.lower.right", "foot.left", "foot.right",
                         "wing.upper.left", "wing.upper.right", "wing.lower.left", "wing.lower.right"})
        for name in ('leg.upper', 'leg.lower', 'foot'):
            left, right = by_bone[name+'.left'], by_bone[name+'.right']
            for i in range(128):
                self.assertAlmostEqual(left.keys[i][1], right.keys[(i+64)%128][1], places=5)
        for track in clip.tracks:
            self.assertEqual(track.keys[0][1], track.keys[-1][1])
        self.assertLess(clip.translations[0].keys[0][1][2], 0)
        for resting in (generate_avian_idle(), generate_avian_flight()):
            self.assertTrue(all(offset == (0.,0.,0.) for _,offset in resting.translations[0].keys))

    def test_walk_matches_weighted_contact_targets_for_both_shapes_and_strengths(self):
        from object_core.animation.weighted_contact import LimbSurface
        from object_core.providers.avian_gait import contact_schedule
        from scripts.anatomy_baseline import SAMPLES
        provider = get_provider('avian')
        defaults = {p.key:p.default for p in provider.parameters}
        for values in (defaults, SAMPLES['avian']):
            mesh, anatomy = provider.mesh(values), provider.anatomy(values)
            bones = {b.name:b for b in provider.skeleton(values).bones}
            weights = provider.skin_weights(mesh,values)[0]
            regions = {r.name:r for r in anatomy.regions}
            for strength in (.1,1.,2.):
                clip = provider.locomotion(1.2,strength,values=values)
                tracks = {t.bone:t for t in clip.tracks}
                schedules = contact_schedule(1.2,strength,values['body_height_cm'],provider.skeleton(values))
                for chain in anatomy.chains:
                    if chain.name not in schedules:
                        continue
                    surface = LimbSurface(mesh,weights,regions[chain.name],
                        tuple(bones[n] for n in chain.bones),-clip.translations[0].keys[0][1][2])
                    for i in range(128):
                        surface.crouch = -clip.translations[0].keys[i][1][2]
                        target = schedules[chain.name].target(i/128)
                        y,z = surface.measure(tuple(tracks[n].keys[i][1] for n in chain.bones[:2]))
                        self.assertAlmostEqual(y,surface.neutral_y+target.forward_cm,places=5)
                        self.assertAlmostEqual(z,target.lift_cm+.02,places=5)

    def test_long_low_stride_is_reachable_without_changing_reference_shape_steps(self):
        from scripts.avian_review_samples import review_values
        from object_core.providers.avian_gait import contact_schedule
        provider = get_provider('avian')
        for name in ('default','contrasting','long-low'):
            values = review_values(name)
            for strength in (1.,2.):
                requested = values['body_height_cm']*.08*strength
                schedules = contact_schedule(1.2,strength,values['body_height_cm'],provider.skeleton(values))
                stride = schedules['leg.left'].stride_cm
                self.assertGreater(stride,0)
                self.assertEqual(stride,schedules['leg.right'].stride_cm)
                if name == 'long-low' and strength == 2.:
                    self.assertLess(stride,requested)
                else:
                    self.assertEqual(stride,requested)
                self.assertTrue(provider.locomotion(1.2,strength,values=values).tracks)

    def test_walk_body_response_is_closed_bounded_and_synchronized_to_support(self):
        from object_core.providers.avian_gait import body_crouch, contact_schedule
        for strength in (.1,1.,2.):
            clip = generate_avian_walk(1.2,strength)
            root = clip.translations[0]
            self.assertEqual(root.keys[0][1],root.keys[-1][1])
            self.assertTrue(all(offset[:2] == (0.,0.) for _,offset in root.keys))
            depth = [-offset[2] for _,offset in root.keys]
            self.assertGreater(max(depth)-min(depth), .01*20*min(strength,1.))
            self.assertLessEqual(max(depth),.04*20*min(strength,1.))
            schedules = contact_schedule(1.2,strength,20)
            self.assertTrue(all(s.target(.075).in_stance for s in schedules.values()))
            self.assertEqual(sum(s.target(.325).in_stance for s in schedules.values()),1)
            self.assertGreater(body_crouch(20,strength,.075),body_crouch(20,strength,.325))
            for phase in (.0,.075,.325,.9):
                self.assertAlmostEqual(body_crouch(20,strength,phase),body_crouch(20,strength,phase+.5))

    def test_fold_tracks_are_local_normalized_and_independent_of_step_strength(self):
        from dataclasses import asdict
        from object_core.animation.idle import BoneLocalRotationTrack
        def wings(clip):
            return tuple(t for t in clip.tracks if t.bone.startswith('wing.'))
        expected = wings(generate_avian_idle(1.2,.1))
        for clip in (generate_avian_idle(1.2,2.), generate_avian_walk(1.2,.1), generate_avian_walk(1.2,2.)):
            self.assertEqual(wings(clip),expected)
        self.assertEqual(len(expected),4)
        for track in expected:
            self.assertIsInstance(track,BoneLocalRotationTrack)
            self.assertEqual(asdict(track)['space'],'BONE_LOCAL')
            self.assertAlmostEqual(sum(v*v for v in track.axis),1.)
            self.assertEqual(track.keys[0][1],track.keys[-1][1])

    def test_flight_is_closed_symmetric_and_uses_both_wing_segments(self):
        clip = generate_avian_flight(0.9, 1.0)
        stronger = generate_avian_flight(0.9, 2.0)
        self.assertEqual(clip, generate_avian_flight(0.9, 1.0))
        by_bone = {track.bone: track for track in clip.tracks}
        self.assertTrue({"wing.upper.left", "wing.upper.right",
                         "wing.lower.left", "wing.lower.right",
                         "spine", "neck", "tail.1", "tail.2"}.issubset(by_bone))
        left = by_bone["wing.upper.left"]
        right = by_bone["wing.upper.right"]
        self.assertAlmostEqual(left.keys[0][1], -right.keys[0][1])
        self.assertAlmostEqual(left.keys[0][1], left.keys[-1][1])
        for base, doubled in zip(clip.tracks, stronger.tracks):
            self.assertEqual(len(base.keys), 17)
            self.assertTrue(all(a[0] < b[0] for a, b in zip(base.keys, base.keys[1:])))
            self.assertAlmostEqual(doubled.keys[0][1], 2 * base.keys[0][1])

    def test_animation_validation_rejects_shared_control_outliers(self):
        for generator, bad_durations in ((generate_avian_idle, (0.5, 21.0)),
                                         (generate_avian_walk, (0.4, 4.1)),
                                         (generate_avian_flight, (0.4, 4.1))):
            for duration in bad_durations:
                with self.subTest(generator=generator.__name__, duration=duration):
                    with self.assertRaises(ValueError):
                        generator(duration=duration)
            for strength in (0.0, 2.1, float("nan"), True):
                with self.subTest(generator=generator.__name__, strength=strength):
                    with self.assertRaises((TypeError, ValueError)):
                        generator(strength=strength)


if __name__ == "__main__":
    unittest.main()
