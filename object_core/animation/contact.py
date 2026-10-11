# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable stance/swing targets, independent of skeletons and host evaluation.

Forward is a scalar coordinate chosen by the caller, not a world axis. These
in-place targets are relative to a neutral contact point. Reference root travel
at stride / duration cancels stance motion. They neither generate root motion
nor guarantee that a posed surface is grounded.
"""
from dataclasses import dataclass
from math import isfinite


def _number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(name + ' must be a number')
    if not isfinite(value):
        raise ValueError(name + ' must be finite')


@dataclass(frozen=True)
class ContactTarget:
    in_stance: bool
    forward_cm: float
    lift_cm: float


@dataclass(frozen=True)
class ContactCycle:
    """A foot schedule with reference travel in cm and duration in seconds.

    Local phase zero is touchdown. Stance includes touchdown, excludes liftoff.
    Stride is reference root travel per cycle; stance excursion is stride times
    duty_factor. touchdown_phase offsets the event within the shared cycle.
    """
    duration: float
    stride_cm: float
    duty_factor: float
    swing_height_cm: float
    touchdown_phase: float = 0.0

    def __post_init__(self):
        for name in ('duration', 'stride_cm', 'duty_factor', 'swing_height_cm',
                     'touchdown_phase'):
            _number(name, getattr(self, name))
        if self.duration <= 0 or self.stride_cm < 0 or self.swing_height_cm < 0:
            raise ValueError('Duration must be positive; travel and lift nonnegative')
        if not 0 < self.duty_factor < 1:
            raise ValueError('Duty factor must be strictly between zero and one')
        if not 0 <= self.touchdown_phase < 1:
            raise ValueError('Touchdown phase must be in [0, 1)')

    @property
    def reference_speed_cm_s(self):
        return self.stride_cm / self.duration

    def target(self, phase):
        """Evaluate a finite cycle phase, including negative/wrapped phases.

        Cubic Hermite swing matches stance velocity at both ends; quartic lift
        has zero endpoint velocity. Small fore/aft swing overshoot is intentional.
        This provides continuous position and velocity, not acceleration.
        """
        _number('phase', phase)
        local = (phase - self.touchdown_phase) % 1.0
        duty = self.duty_factor
        if local < duty:
            return ContactTarget(True, self.stride_cm * (duty / 2 - local), 0.0)
        swing = 1 - duty
        u = (local - duty) / swing
        blend = u * u * (3 - 2 * u)
        tangent = u * (1 - u) * (1 - 2 * u)
        forward = self.stride_cm * (-duty / 2 + duty * blend - swing * tangent)
        return ContactTarget(False, forward, self.swing_height_cm * 16 * u*u * (1-u)*(1-u))
