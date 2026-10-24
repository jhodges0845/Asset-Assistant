# SPDX-License-Identifier: GPL-3.0-or-later
"""Run class-based integration tests and function-based UI tests inside Blender.

Install pytest==8.4.2 into artifacts/test-dependencies before running.
Optional pytest arguments follow Blender's -- separator.
"""
from pathlib import Path
import os
import sys
import bpy

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
dependencies = Path(os.environ.get('ASSET_ASSISTANT_TEST_DEPS', root / 'artifacts/test-dependencies'))
if dependencies.is_dir():
    sys.path.insert(0, str(dependencies))
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
import pytest

args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
result = pytest.main(args or [str(root / 'tests/blender'), '-v'])
if result != 0:
    raise RuntimeError('Blender test suite failed (pytest exit %s)' % result)
