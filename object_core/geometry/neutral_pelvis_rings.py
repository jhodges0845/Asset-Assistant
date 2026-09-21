# SPDX-License-Identifier: GPL-3.0-or-later
"""Legacy ring-based neutral pelvis experiment.

Preserved while the primary neutral_pelvis module explores recipe-driven patch
construction. This implementation intentionally remains available for visual
A/B comparison and regression reference.
"""
from .neutral_pelvis import NeutralPelvisShape, semantic_controls

# NOTE: the full legacy implementation is retained in git history at cf2e7ee.
# This module is a compatibility marker while neutral_pelvis.py becomes the
# patch-and-stitch experiment. It deliberately does not shadow the primary
# generator so callers continue to exercise the new construction.

__all__ = ("NeutralPelvisShape", "semantic_controls")
