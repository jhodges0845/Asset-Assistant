# SPDX-License-Identifier: GPL-3.0-or-later
"""Human weighted surface and clip switching survive the actual GLB path."""
from tests.blender import test_canine_glb_playback as playback


class HumanGLBPlaybackTests(playback.CanineGLBPlaybackTests):
    provider_key = "human"
    run_duration = .72

    def test_idle_resets_root_after_each_contact_clip(self):
        import bpy
        from blender_adapter.animation import add_idle, add_locomotion, add_run, activate_generated_action
        provider = playback.get_provider('human')
        values = {p.key:p.default for p in provider.parameters}
        mesh = provider.mesh(values)
        root = playback.create_character(mesh, scene=self.scene,
            skeleton=provider.skeleton(values), skin_weights=provider.skin_weights(mesh,values))
        root['object_type'] = 'human'
        for key,value in values.items(): root[key] = value
        add_idle(root,self.scene)
        add_locomotion(root,self.scene)
        add_run(root,self.scene)
        rig = next(o for o in root.children if o.type=='ARMATURE')
        for label in ('Walk','Run'):
            activate_generated_action(root,label)
            self.scene.frame_set(37)
            bpy.context.view_layer.update()
            self.assertGreater(rig.pose.bones['root'].location.length,.01)
            activate_generated_action(root,'Idle')
            self.scene.frame_set(37)
            bpy.context.view_layer.update()
            self.assertLess(rig.pose.bones['root'].location.length,1e-8)
