# SPDX-License-Identifier: GPL-3.0-or-later
"""Export Human clips through the shared Godot pose/skin reference workflow."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.export_canine_godot_review import main
if __name__ == '__main__':
    main('human')
