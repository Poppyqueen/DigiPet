"""
sky_sim/atmosphere.py
---------------------
Derives atmosphere quality scores and per-star magnitude losses
from Open-Meteo weather data.

All "magnitude loss" values follow the astronomical convention:
higher magnitude = fainter. A loss of +1.0 means a star appears
one magnitude fainter than it would in vacuum.
"""

from __future__ import annotations
import math
from .types import WeatherSnapshot, AtmosphereScores, BortleClass


# ---------------------------------------------------------------------------
# Transparency — haze, humidity, aerosols, visibility
# ---------------------------------------------------------------------------

def visibility_to_magnitude_loss(vis_meters: float) -> float:
    """
    Global transparency loss from haze / aerosols.
    Applies uniformly across the sky (not patchy like clouds).
    """
    if vis_meters >= 50_000:  return 0.00   # pristine
    if vis_meters >= 30_000:  return 0.10   # barely noticeable
    if vis_meters >= 20_000:  return 0.25   # slightly hazy
    if vis_meters >= 10_000:  return 0.55   # hazy
    if vis_meters >= 5_000:   return 1.00   # quite hazy
    if vis_meters >= 2_000:   return 1.80   # dense haze / mist
    return 2.50                              # near fog


def humidity_to_magnitude_loss(humidity_pct: float) -> float:
    """
    Humidity scatter adds to sky glow in light-polluted areas.
    Minimal effect in dark skies; significant in cities.
    """
    if humidity_pct < 40:   return 0.00
    if humidity_pct < 60:   return 0.05
    if humidity_pct < 75:   return 0.15
    if humidity_pct < 85:   return 0.30
    if humidity_pct < 92:   return 0.50
    return 0.75


def transparency_score(vis_meters: float, humidity_pct: float,
                        dew_spread: float) -> float:
    """
    Overall transparency 0.0–1.0. Higher = clearer air.
    """
    vis_loss = visibility_to_magnitude_loss(vis_meters)
    # Normalise vis_loss (0–2.5 range) to 0–1 penalty
    vis_penalty = min(1.0, vis_loss / 2.5)

    hum_penalty = min(1.0, humidity_pct / 100.0) * 0.3

    # Dew spread: < 2°C means moisture condensing → bad transparency
    dew_penalty = max(0.0, 1.0 - dew_spread / 8.0) * 0.2

    return max(0.0, 1.0 - vis_penalty * 0.6 - hum_penalty - dew_penalty)


# ---------------------------------------------------------------------------
# Seeing — atmospheric stability / turbulence
# ---------------------------------------------------------------------------

def seeing_score(cape_jkg: float, wind_speed_120m: float) -> float:
    """
    Seeing quality 0.0–1.0. Higher = more stable atmosphere.
    CAPE: high means unstable / convective.
    Upper wind: high means turbulent layers.
    """
    # CAPE penalty — above 1000 J/kg atmosphere is quite unstable
    if cape_jkg <= 100:    cape_penalty = 0.00
    elif cape_jkg <= 300:  cape_penalty = 0.10
    elif cape_jkg <= 600:  cape_penalty = 0.25
    elif cape_jkg <= 1000: cape_penalty = 0.45
    elif cape_jkg <= 2000: cape_penalty = 0.65
    else:                  cape_penalty = 0.85

    # Upper wind penalty — fast high-altitude wind = poor seeing
    if wind_speed_120m <= 15:    wind_penalty = 0.00
    elif wind_speed_120m <= 30:  wind_penalty = 0.10
    elif wind_speed_120m <= 50:  wind_penalty = 0.25
    elif wind_speed_120m <= 80:  wind_penalty = 0.45
    else:                        wind_penalty = 0.65

    return max(0.0, 1.0 - cape_penalty * 0.6 - wind_penalty * 0.4)


# ---------------------------------------------------------------------------
# Fog risk
# ---------------------------------------------------------------------------

def fog_risk_score(dew_spread: float, humidity_pct: float) -> float:
    """
    Probability of fog / dew degrading conditions. 0.0–1.0.
    """
    spread_risk = max(0.0, 1.0 - dew_spread / 5.0)
    hum_risk    = max(0.0, (humidity_pct - 70.0) / 30.0)
    return min(1.0, spread_risk * 0.7 + hum_risk * 0.3)


# ---------------------------------------------------------------------------
# Atmospheric extinction — geometry of the atmosphere
# ---------------------------------------------------------------------------

def atmospheric_extinction(altitude_deg: float) -> float:
    """
    Extra magnitude loss purely from the angle through the atmosphere.
    At zenith (90°): ~0.2 mag. At 10°: ~1.5 mag. Below 5°: unreliable.
    Uses standard astronomical formula based on airmass.
    """
    if altitude_deg <= 0:
        return 99.0   # below horizon — effectively infinite

    alt_rad  = math.radians(max(altitude_deg, 1.0))
    # Pickering's airmass formula — good down to ~5° altitude
    airmass  = 1.0 / (math.sin(alt_rad) + 0.50572 * (altitude_deg + 6.07995) ** -1.6364)
    airmass  = min(airmass, 40.0)   # cap at horizon

    # Extinction coefficient k ≈ 0.20 mag/airmass for typical clear night
    k = 0.20
    return k * airmass


# ---------------------------------------------------------------------------
# Moon sky brightness impact
# ---------------------------------------------------------------------------

def moon_magnitude_loss(illumination: float, altitude_deg: float) -> float:
    """
    How many magnitudes the moon washes out the sky.
    Full moon near zenith: ~2.5 mag loss. Crescent low: negligible.
    """
    if altitude_deg <= 0:
        return 0.0   # moon below horizon — no effect

    # Scale by altitude (moon low on horizon affects sky less)
    altitude_factor = min(1.0, altitude_deg / 45.0)

    # Full moon = 2.5 mag loss, scales roughly linearly with illumination
    return illumination * 2.5 * altitude_factor


# ---------------------------------------------------------------------------
# Cloud opacity → magnitude loss
# ---------------------------------------------------------------------------

def cloud_opacity_to_magnitude_loss(opacity: float) -> float:
    """
    Convert cloud opacity (0–1) to magnitude loss for a star behind it.
    opacity 0.0 → 0.0 mag loss
    opacity 0.5 → ~1.5 mag loss
    opacity 1.0 → effectively infinite (star invisible)
    """
    if opacity <= 0.001:
        return 0.0
    if opacity >= 0.999:
        return 99.0   # fully blocked

    # Transmission = 1 - opacity
    # Magnitude loss = -2.5 * log10(transmission)
    transmission = 1.0 - opacity
    return -2.5 * math.log10(max(transmission, 1e-6))


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

def score_atmosphere(weather: WeatherSnapshot,
                     bortle: BortleClass,
                     moon_illumination: float,
                     moon_altitude: float,
                     light_pollution_mag_loss: float) -> AtmosphereScores:
    """
    Derive all atmosphere scores from weather + location data.
    """
    vis_loss  = visibility_to_magnitude_loss(weather.visibility_m)
    moon_loss = moon_magnitude_loss(moon_illumination, moon_altitude)

    return AtmosphereScores(
        transparency=transparency_score(
            weather.visibility_m,
            weather.humidity,
            weather.dew_point_spread,
        ),
        seeing=seeing_score(weather.cape, weather.wind_speed_120m),
        fog_risk=fog_risk_score(weather.dew_point_spread, weather.humidity),

        # add sun here? make sure it is location aware and correctly implemented

        visibility_mag_loss=vis_loss,
        light_pollution_mag_loss=light_pollution_mag_loss,
        moon_mag_loss=moon_loss,
    )