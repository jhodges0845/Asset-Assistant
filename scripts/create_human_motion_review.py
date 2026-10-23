# SPDX-License-Identifier: GPL-3.0-or-later
"""Create a four-view Human scene with three cycles of actual editable motion."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.create_canine_motion_review import main
if __name__ == '__main__':
    main('human')
