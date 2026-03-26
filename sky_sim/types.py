"""
sky_sim/types.py
----------------
All dataclasses and enums used across the simulation.
No logic here — just shapes of data.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BortleClass(int, Enum):
    PRISTINE          = 1   # limiting mag ~7.0
    TRULY_DARK        = 2   # limiting mag ~6.8
    RURAL             = 3   # limiting mag ~6.5
    RURAL_SUBURBAN    = 4   # limiting mag ~6.0
    SUBURBAN          = 5   # limiting mag ~5.5
    BRIGHT_SUBURBAN   = 6   # limiting mag ~5.0
    SUBURBAN_URBAN    = 7   # limiting mag ~4.5
    CITY              = 8   # limiting mag ~4.0
    INNER_CITY        = 9   # limiting mag ~3.0


class DarkAdaptation(str, Enum):
    NONE     = "none"       # just stepped outside, ~30% sensitivity
    PARTIAL  = "partial"    # ~10 minutes outside
    FULL     = "full"       # 20-30+ minutes, maximum sensitivity


class SkyConditionNarrative(str, Enum):
    CLEAR            = "clear"
    MOSTLY_CLEAR     = "mostly_clear"
    PARTLY_CLOUDY    = "partly_cloudy"
    MOSTLY_CLOUDY    = "mostly_cloudy"
    OVERCAST         = "overcast"
    FOG              = "fog"
    PRECIPITATION    = "precipitation"
    THUNDERSTORM     = "thunderstorm"


# ---------------------------------------------------------------------------
# Weather input — what we pull from OpenMeteo
# ---------------------------------------------------------------------------

@dataclass
class WeatherSnapshot:
    """Structured weather data consumed by the simulation."""
    cloud_cover_total:  float        # 0–100 %
    cloud_cover_low:    float        # 0–100 %  stratus / fog layer
    cloud_cover_mid:    float        # 0–100 %  altostratus layer
    cloud_cover_high:   float        # 0–100 %  cirrus layer
    visibility_m:       float        # meters — pre-computed transparency
    humidity:           float        # 0–100 %
    dew_point:          float        # °C
    temperature:        float        # °C apparent
    precipitation:      float        # mm — preceding interval
    wind_speed_10m:     float        # km/h — low cloud advection
    wind_direction_10m: float        # degrees
    wind_speed_120m:    float        # km/h — high cloud advection
    cape:               float        # J/kg — atmospheric instability
    weather_code:       int          # WMO code
    is_day:             bool

    @property
    def dew_point_spread(self) -> float:
        """Small spread (< 2°C) means fog/dew forming."""
        return self.temperature - self.dew_point

    @property
    def condition_narrative(self) -> SkyConditionNarrative:
        wc = self.weather_code
        if wc >= 95:   return SkyConditionNarrative.THUNDERSTORM
        if wc >= 61:   return SkyConditionNarrative.PRECIPITATION
        if wc >= 51:   return SkyConditionNarrative.PRECIPITATION
        if wc in (45, 48): return SkyConditionNarrative.FOG
        if wc == 3:    return SkyConditionNarrative.OVERCAST
        if wc == 2:    return SkyConditionNarrative.PARTLY_CLOUDY
        if wc == 1:    return SkyConditionNarrative.MOSTLY_CLEAR
        if wc == 0:    return SkyConditionNarrative.CLEAR
        # fallback: derive from cloud cover total
        c = self.cloud_cover_total
        if c >= 90:    return SkyConditionNarrative.OVERCAST
        if c >= 70:    return SkyConditionNarrative.MOSTLY_CLOUDY
        if c >= 40:    return SkyConditionNarrative.PARTLY_CLOUDY
        if c >= 10:    return SkyConditionNarrative.MOSTLY_CLEAR
        return SkyConditionNarrative.CLEAR


# ---------------------------------------------------------------------------
# Individual celestial objects
# ---------------------------------------------------------------------------

@dataclass
class StarResult:
    name:               str
    magnitude:          float
    azimuth:            float        # degrees
    altitude:           float        # degrees above horizon
    effective_magnitude: float       # after all losses applied
    visible:            bool
    obscured_by_cloud:  bool = False
    constellation:      Optional[str] = None


@dataclass
class PlanetResult:
    name:               str
    magnitude:          float
    azimuth:            float
    altitude:           float
    effective_magnitude: float
    visible:            bool
    obscured_by_cloud:  bool = False
    angular_diameter:   Optional[float] = None  # arcseconds


@dataclass
class MoonResult:
    phase_angle:        float        # degrees 0–360
    phase_name:         str          # "waxing crescent" etc.
    illumination:       float        # 0.0–1.0
    azimuth:            float
    altitude:           float
    above_horizon:      bool
    magnitude_impact:   float        # how many magnitudes it washes out sky


# ---------------------------------------------------------------------------
# Atmosphere derived scores
# ---------------------------------------------------------------------------

@dataclass
class AtmosphereScores:
    """Derived quality scores from weather data. All 0.0–1.0, higher = better."""
    transparency:       float   # how clear the air is (haze, aerosols, humidity)
    seeing:             float   # atmospheric stability (CAPE, upper winds)
    fog_risk:           float   # probability of fog forming (dew point spread)

    # Raw magnitude losses applied globally (not from clouds)
    visibility_mag_loss:    float
    light_pollution_mag_loss: float
    moon_mag_loss:          float

    @property
    def overall_quality(self) -> float:
        return (self.transparency * 0.5 + self.seeing * 0.3 +
                (1.0 - self.fog_risk) * 0.2)


# ---------------------------------------------------------------------------
# Full snapshot — the main API return object
# ---------------------------------------------------------------------------

@dataclass
class SkySnapshot:
    """
    The complete state of the simulated sky at one moment in time.
    This is what snapshot() returns. Everything else is derived from this.
    """
    # Identity
    latitude:           float
    longitude:          float
    local_time:         str          # ISO8601 local time string
    timezone:           str

    # Conditions
    weather:            WeatherSnapshot
    atmosphere:         AtmosphereScores
    moon:               MoonResult
    bortle_class:       BortleClass
    limiting_magnitude: float        # effective — after all losses

    # Objects
    stars_visible:      list[StarResult]
    stars_obscured:     list[StarResult]
    planets:            list[PlanetResult]

    # Simulation state
    simulation_tick:    int          # how many ticks have elapsed
    cloud_coverage_simulated: float  # 0–1, actual simulated sky coverage

    # Narrative
    condition:          SkyConditionNarrative

    @property
    def total_stars_visible(self) -> int:
        return len(self.stars_visible)

    @property
    def planets_visible(self) -> list[PlanetResult]:
        return [p for p in self.planets if p.visible]