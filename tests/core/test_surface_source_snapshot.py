import tempfile
import unittest
from pathlib import Path
from scripts.surface_source_snapshot import capture_source, verify_source


class SourceSnapshotTests(unittest.TestCase):
    def test_snapshot_preserves_source_and_detects_modification(self):
        root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as folder:
            snapshot=capture_source(root,folder,root/'presets/human/maxine.json')
            verify_source(snapshot)
            self.assertTrue((snapshot/'object_core/geometry/surface_pelvis.py').is_file())
            target=snapshot/'object_core/geometry/surface_human.py'
            target.write_bytes(target.read_bytes()+b'\n# changed\n')
            with self.assertRaisesRegex(ValueError,'Snapshot source changed'):
                verify_source(snapshot)
