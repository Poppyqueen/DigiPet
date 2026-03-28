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

class VisibilityState(str, Enum):
    VISIBLE      = "visible"       # passes all checks
    CLOUDED      = "clouded"       # cloud opacity blocks it
    BELOW_LIMIT  = "below_limit"   # too faint given conditions

@dataclass
class StarResult:
    name:                str
    magnitude:           float
    azimuth:             float
    altitude:            float
    effective_magnitude: float
    constellation:       Optional[str] = None
    visibility:          VisibilityState = VisibilityState.BELOW_LIMIT
    cloud_opacity:       float = 0.0    # raw opacity, useful for clustering


@dataclass
class PlanetResult:
    name:               str
    magnitude:          float
    azimuth:            float
    altitude:           float
    effective_magnitude: float
    visibility:         VisibilityState = VisibilityState.BELOW_LIMIT
    cloud_opacity:      float = 0.0
    angular_diameter:   Optional[float] = None


@dataclass
class MoonResult:
    phase_angle:        float        # degrees 0–360 (elongation Sun–Moon from Earth)
    illumination:       float        # 0.0–1.0  (fraction of disc illuminated)
    days_from_new:      float        # 0–29.53  (position in synodic month)
    waxing:             bool         # True = growing, False = shrinking
    azimuth:            float
    altitude:           float
    above_horizon:      bool
    magnitude_impact:   float        # how many magnitudes it washes out sky


class TwilightPhase(str, Enum):
    """Named phases of the solar day, from the observer's perspective."""
    DAY               = "day"               # sun > +18°
    CIVIL_TWILIGHT    = "civil_twilight"    # 0° to +18°  — horizon glow, no stars
    NAUTICAL_TWILIGHT = "nautical_twilight" # -6° to 0°   — sea-horizon lit
    ASTRO_TWILIGHT    = "astro_twilight"    # -18° to -6° — faint sky glow
    NIGHT             = "night"             # sun < -18°  — full astronomical dark


@dataclass
class SunResult:
    """
    The Sun's position and its sky-brightness contribution.
    Always computed, regardless of whether the Sun is above the horizon.
    This is the authoritative day/night signal for the whole simulation.
    """
    azimuth:            float          # degrees 0–360
    altitude:           float          # degrees (negative = below horizon)
    above_horizon:      bool
    twilight_phase:     TwilightPhase
    magnitude_impact:   float          # mag loss imposed on the limiting magnitude



# Eclipse

class EclipseType(str, Enum):
    NONE    = "none"
    SOLAR   = "solar"
    LUNAR   = "lunar"

class EclipsePhase(str, Enum):
    NONE        = "none"
    PENUMBRAL   = "penumbral"   # lunar only — barely perceptible
    PARTIAL     = "partial"
    ANNULAR     = "annular"     # solar only — ring of fire
    TOTAL       = "total"
    HYBRID      = "hybrid"      # solar only — annular+total along path

@dataclass
class EclipseResult:
    eclipse_type:       EclipseType
    phase:              EclipsePhase
    magnitude:          float        # 0 = no eclipse, 1.0 = totality begins, >1 = deep total
    obscuration:        float        # 0.0–1.0, fraction of solar/lunar disc covered
    separation_deg:     float        # angular separation Sun–Moon in degrees
    umbral_depth:       float        # signed: >0 = in umbra, 0–1 penumbral, <0 = outside
    visible_from_here:  bool         # True if above horizon at observer's location
    saros_series:       Optional[int]   # Saros cycle number if known
    gamma:              Optional[float] # closest approach to shadow axis (solar eclipses)
    note:               str          # human-readable summary for the astronomer
    

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
    visibility_mag_loss:      float
    #light_pollution_mag_loss: float
    moon_mag_loss:            float
    sun_mag_loss:             float   # twilight / daytime sky brightness loss
    sun_altitude:             float   # degrees; negative = below horizon

    @property
    def overall_quality(self) -> float:
        # Sun washes out the sky entirely when above astronomical twilight
        if self.sun_altitude > -18.0:
            return 0.0
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
    sun:                SunResult
    bortle_class:       BortleClass
    limiting_magnitude: float        # effective — after all losses

    # Objects
    stars:                list[StarResult]   # all above horizon, classified
    stars_above_horizon:  int                # len(stars) — no recomputation needed
    planets:              list[PlanetResult]

    # Simulation state
    simulation_tick:    int          # how many ticks have elapsed
    cloud_coverage_simulated: float  # 0–1, actual simulated sky coverage

    eclipse: EclipseResult

    # Narrative
    condition:          SkyConditionNarrative

    @property
    def stars_visible(self) -> list[StarResult]:
        return [s for s in self.stars if s.visibility == VisibilityState.VISIBLE]

    @property
    def stars_clouded(self) -> list[StarResult]:
        return [s for s in self.stars if s.visibility == VisibilityState.CLOUDED]

    @property
    def stars_below_limit(self) -> list[StarResult]:
        return [s for s in self.stars if s.visibility == VisibilityState.BELOW_LIMIT]

    @property
    def total_stars_visible(self) -> int:
        return sum(1 for s in self.stars if s.visibility == VisibilityState.VISIBLE)