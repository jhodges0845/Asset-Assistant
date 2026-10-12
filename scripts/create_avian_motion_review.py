# SPDX-License-Identifier: GPL-3.0-or-later
"""Save three-cycle Avian Walk review scenes; --stills writes four phase sheets.

Use in a fresh Blender background process with -- --output review.blend.
Shares the canine review layout and real adapter action workflow.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.create_canine_motion_review import main

if __name__ == '__main__':
    main('avian')
