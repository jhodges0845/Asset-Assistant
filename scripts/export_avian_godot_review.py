# SPDX-License-Identifier: GPL-3.0-or-later
"""Export Avian clips through the shared Godot pose-oracle workflow.

The review harness retains its historical canine.glb fixture filename.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_canine_godot_review import main
if __name__ == '__main__': main('avian')
