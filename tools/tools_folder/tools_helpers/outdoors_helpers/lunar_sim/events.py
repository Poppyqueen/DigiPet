"""
lunar_sim/events.py
---------------------
A generic decay/repair cycle: long quiet stretches, punctuated by a
perceivable event that knocks a value down, followed by a visible
self-repair arc back to nominal. Used for both hull integrity and
viewport clarity -- same mechanism, different tuning + flavor text.

Design intent: nothing here requires player/agent interaction to resolve.
`assist_repair()` is a hook left in place for a future interaction (an EVA
patch job, a maintenance item) to speed up an in-progress repair -- it is
not called by anything yet.
"""

from __future__ import annotations
import random
from enum import Enum


class CycleState(str, Enum):
    NOMINAL = "nominal"       # quiet, nothing notable
    EVENT = "event"           # the damaging event just happened, perceivable for 1 tick
    REPAIRING = "repairing"   # visibly recovering over several ticks


class DecayCycle:
    """
    value: 1.0 = pristine, 0.0 = fully degraded. Never fully hits 0 with
    sane tuning (severity_range should be well under 1.0 per event).
    """

    def __init__(
        self,
        rng: random.Random,
        event_chance: float,
        severity_range: tuple[float, float],
        repair_ticks_range: tuple[int, int],
        event_labels: list[str],
    ):
        self.rng = rng
        self.value = 1.0
        self.state = CycleState.NOMINAL
        self.event_chance = event_chance
        self.severity_range = severity_range
        self.repair_ticks_range = repair_ticks_range
        self.event_labels = event_labels

        self.current_label: str | None = None
        self.repair_ticks_total = 0
        self.repair_ticks_elapsed = 0
        self._repair_per_tick = 0.0

    @property
    def repair_progress(self) -> float:
        """0-1 progress through the current repair, 0 if not repairing."""
        if self.state != CycleState.REPAIRING or self.repair_ticks_total == 0:
            return 0.0
        return min(1.0, self.repair_ticks_elapsed / self.repair_ticks_total)

    @property
    def repair_eta_ticks(self) -> int:
        if self.state != CycleState.REPAIRING:
            return 0
        return max(0, self.repair_ticks_total - self.repair_ticks_elapsed)

    def tick(self) -> None:
        if self.state == CycleState.NOMINAL:
            if self.rng.random() < self.event_chance:
                self._trigger_event()

        elif self.state == CycleState.EVENT:
            # Event is perceivable for exactly one tick, then repair begins.
            self.state = CycleState.REPAIRING
            self.repair_ticks_elapsed = 0

        elif self.state == CycleState.REPAIRING:
            self.repair_ticks_elapsed += 1
            self.value = min(1.0, self.value + self._repair_per_tick)
            if self.value >= 1.0 or self.repair_ticks_elapsed >= self.repair_ticks_total:
                self.value = 1.0
                self.state = CycleState.NOMINAL
                self.current_label = None

    def _trigger_event(self) -> None:
        severity = self.rng.uniform(*self.severity_range)
        self.value = max(0.0, self.value - severity)
        self.current_label = self.rng.choice(self.event_labels)

        self.repair_ticks_total = self.rng.randint(*self.repair_ticks_range)
        # slight overshoot factor so rounding always closes the gap by the ETA
        self._repair_per_tick = (severity / max(1, self.repair_ticks_total)) * 1.1
        self.repair_ticks_elapsed = 0
        self.state = CycleState.EVENT

    def assist_repair(self, amount: float) -> None:
        """Hook for a future interaction to speed along an in-progress
        repair. Not called anywhere yet -- deliberately unused for now."""
        if self.state == CycleState.REPAIRING:
            self.value = min(1.0, self.value + amount)
            if self.value >= 1.0:
                self.value = 1.0
                self.state = CycleState.NOMINAL
                self.current_label = None


HULL_EVENT_LABELS = [
    "a micrometeorite cluster strike",
    "a thermal stress fracture along a seam",
    "a settling shock from the regolith bed below",
]

VIEWPORT_EVENT_LABELS = [
    "a static-charged dust squall crossing the site",
    "ejecta settling from a distant impact",
    "fines kicked up by a passing rover",
]