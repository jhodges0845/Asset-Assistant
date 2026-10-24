# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify renamed NLA clip arrangements in fresh Blender processes."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "blender"))


def verify(checkpoint):
    from blender_adapter.animation import action_curves
    from blender_adapter.animation_records import animation_record
    expected = json.loads(Path(str(checkpoint) + ".json").read_text())
    actions = [action for action in bpy.data.actions
               if action.get("asset_assistant_generated")]
    assert len(actions) == 1
    action = actions[0]
    record = animation_record(action)
    assert record.animation_id == expected["animation_id"]
    assert record.export_name == expected["export_name"]
    assert record.provider_key == expected["provider"]
    actual = [list(key.co) for curve in action_curves(action, action.slots[0])
              for key in curve.keyframe_points]
    assert actual == expected["keys"]
    rigs = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    assert len(rigs) == 1
    track = rigs[0].animation_data.nla_tracks[0]
    assert track.name == "Artist arrangement"
    strip = track.strips[0]
    assert strip.action == action
    assert [strip.frame_start, strip.frame_end, strip.repeat, strip.influence] == expected["strip"]
    print("NLA_REOPEN_OK: " + expected["provider"])


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args:
        verify(Path(args[0]))
        return
    from test_animation_tuning import (BlenderAnimationTuningTests,
        CanineAnimationTuningTests, AvianAnimationTuningTests)
    with TemporaryDirectory(prefix="asset-assistant-nla-") as directory:
        for case_type in (BlenderAnimationTuningTests, CanineAnimationTuningTests, AvianAnimationTuningTests):
            case = case_type()
            checkpoint = Path(directory) / (case.provider_key + ".blend")
            case.setUp()
            try:
                case.test_nla_rename_preserves_arrangement_and_preview_blocks_regeneration(checkpoint)
            finally:
                case.tearDown()
            subprocess.run([bpy.app.binary_path, "--background", "--factory-startup",
                            str(checkpoint), "--python-exit-code", "1", "--python",
                            str(Path(__file__).resolve()), "--", str(checkpoint)],
                           check=True, timeout=180)
    print("All three NLA fresh-process checks passed")


if __name__ == "__main__":
    main()
