# SPDX-License-Identifier: GPL-3.0-or-later
"""Provider implementations kept separate from the shared registry."""

from .avian import AVIAN_PARAMETERS, AVIAN_SEMANTIC_TARGETS, AvianProvider
from .base import Parameter
from .box import BoxProvider
from .human import HUMAN_PARAMETERS, HUMAN_SEMANTIC_TARGETS, HumanProvider, HumanoidProvider
from .quadruped import QUADRUPED_PARAMETERS, QUADRUPED_SEMANTIC_TARGETS, QuadrupedProvider
from .semantic import SemanticTarget

__all__ = [
    "Parameter",
    "SemanticTarget",
    "AVIAN_PARAMETERS",
    "AVIAN_SEMANTIC_TARGETS",
    "AvianProvider",
    "BoxProvider",
    "QUADRUPED_PARAMETERS",
    "QUADRUPED_SEMANTIC_TARGETS",
    "QuadrupedProvider",
    "HUMAN_PARAMETERS",
    "HUMAN_SEMANTIC_TARGETS",
    "HumanoidProvider",
    "HumanProvider",
]
