# SPDX-License-Identifier: GPL-3.0-or-later
"""Import-stash provenance must not authorize unrelated or edited arrangements."""
import unittest
import bpy
from blender_adapter.gltf_import_stash import record_import_stashes, has_unchanged_import_stash


class ImportStashTests(unittest.TestCase):
    def setUp(self):
        self.obj = bpy.data.objects.new('Stash owner', None)
        self.action = bpy.data.actions.new('Stashed action')
        self.track = self.obj.animation_data_create().nla_tracks.new()
        self.strip = self.track.strips.new('clip', 1, self.action)
        self.track.mute = self.track.lock = True

    def tearDown(self):
        bpy.data.objects.remove(self.obj)
        bpy.data.actions.remove(self.action)

    def test_names_and_flags_alone_are_not_provenance(self):
        self.assertFalse(has_unchanged_import_stash(self.obj))
        record_import_stashes((self.obj,), ())
        self.assertFalse(has_unchanged_import_stash(self.obj))

    def test_replacement_action_and_added_track_invalidate_record(self):
        record_import_stashes((self.obj,), (self.action,))
        self.assertTrue(has_unchanged_import_stash(self.obj))
        copy = self.action.copy()
        try:
            self.strip.action = copy
            self.assertFalse(has_unchanged_import_stash(self.obj))
            self.strip.action = self.action
        finally:
            bpy.data.actions.remove(copy)
        extra = self.obj.animation_data.nla_tracks.new()
        self.assertFalse(has_unchanged_import_stash(self.obj))
        self.obj.animation_data.nla_tracks.remove(extra)
        self.assertTrue(has_unchanged_import_stash(self.obj))

    def test_record_survives_fresh_blender_process(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        import subprocess
        record_import_stashes((self.obj,), (self.action,))
        with TemporaryDirectory() as directory:
            checkpoint = Path(directory) / 'stash.blend'
            bpy.data.libraries.write(str(checkpoint), {self.obj})
            source_root = str(Path(__file__).resolve().parents[2])
            expression = (
                'import sys, bpy; sys.path.insert(0, ' + repr(source_root) + '); '
                'from blender_adapter.gltf_import_stash import has_unchanged_import_stash; '
                'obj = bpy.data.objects[' + repr(self.obj.name) + ']; '
                'assert has_unchanged_import_stash(obj); '
                'obj.animation_data.nla_tracks[0].mute = False; '
                'assert not has_unchanged_import_stash(obj); '
                'print("GLTF_STASH_REOPEN_OK")'
            )
            result = subprocess.run([bpy.app.binary_path, '--background', str(checkpoint),
                                     '--python-exit-code', '1', '--python-expr', expression],
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn('GLTF_STASH_REOPEN_OK', result.stdout)
