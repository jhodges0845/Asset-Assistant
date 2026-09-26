# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable anatomy metadata; providers and constructors own body plans."""
from .contracts import (
    AnatomyConnection, AnatomyRecipe, AnatomyRegion, JointChain,
    Landmark, ResolvedAnatomy,
)

__all__ = (
    'AnatomyConnection', 'AnatomyRecipe', 'AnatomyRegion', 'JointChain',
    'Landmark', 'ResolvedAnatomy',
)
