# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from object_core.providers.human_gait import contact_schedule
from object_core.objects import get_provider

class HumanContactTests(unittest.TestCase):
    def test_walk_support_and_run_flight_schedules(self):
        for running in (False,True):
            schedules=contact_schedule(1.,1.,180,running)
            counts=[sum(c.target(i/128).in_stance for c in schedules.values()) for i in range(128)]
            self.assertEqual(min(counts),0 if running else 1)
            self.assertEqual(max(counts),1 if running else 2)

    def test_parameter_aware_motion_is_closed_and_keeps_knees_backward(self):
        p=get_provider('human')
        for name,duration in (('locomotion',1.2),('run',.72)):
            clip=getattr(p,name)(duration,1.)
            for track in clip.tracks:
                self.assertEqual(track.keys[0][1],track.keys[-1][1])
                if track.bone.startswith('lower_leg.'):
                    self.assertTrue(all(angle<0 for _,angle in track.keys))
            self.assertEqual(clip.translations[0].keys[0][1],clip.translations[0].keys[-1][1])

    def test_idle_explicitly_resets_contact_root_translation(self):
        clip = get_provider('human').idle(4., 1.)
        self.assertEqual([(t.bone,t.keys) for t in clip.translations],
                         [('root',((0.,(0.,0.,0.)),(4.,(0.,0.,0.))))])
