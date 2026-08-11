"""
lunar_sim/types.py
-------------------
Plain data schema shared between the simulator and the renderer.
No behavior here — mirrors the discipline of sky_sim/types.py.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class DomePhase(str, Enum):
    LUNAR_DAY = "lunar_day"
    LUNAR_NIGHT = "lunar_night"
    TERMINATOR_RISING = "terminator_rising"    # sun climbing through the horizon
    TERMINATOR_SETTING = "terminator_setting"  # sun sinking through the horizon


class FlareIntensity(str, Enum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class SunResult:
    altitude: float          # degrees, site-local
    azimuth: float           # degrees, site-local
    above_horizon: bool
    phase: DomePhase


@dataclass
class EarthResult:
    visible: bool             # False entirely for far-side dome sites
    altitude: float
    azimuth: float
    illuminated_fraction: float   # 0-1, real geometry via skyfield
    libration_lon_deg: float      # signed drift, current
    libration_lat_deg: float


@dataclass
class SpaceWeather:
    flare: FlareIntensity
    flare_ticks_remaining: int
    radiation_dose_rate_uSv_h: float   # ambient, modulated by flare state


class CycleState(str, Enum):
    NOMINAL = "nominal"
    EVENT = "event"
    REPAIRING = "repairing"


@dataclass
class DomeStatus:
    viewport_haze: float               # 0-1, current (1 - clarity cycle value)
    viewport_state: CycleState
    viewport_event_label: str | None
    viewport_repair_eta_ticks: int

    structural_integrity: float        # 0-1, current
    hull_state: CycleState
    hull_event_label: str | None
    hull_repair_eta_ticks: int

    micrometeorite_pings_today: int


@dataclass
class LunarSnapshot:
    timestamp_tick: int
    sun: SunResult
    earth: EarthResult
    space_weather: SpaceWeather
    dome: DomeStatus
    stars_visible: int
    site_lat: float
    site_lon: float