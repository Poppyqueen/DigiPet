"""
lunar_sim/ephemeris.py
-----------------------
Two tiers of physics, kept explicitly separate:

1. REAL, skyfield-backed geometry (Sun-Earth-Moon vectors, illumination
   fraction, synodic timing). Sourced from de421.bsp — same ephemeris
   family the Earth astro provider already relies on.

2. MODELED, labeled-approximation geometry (lunar libration, site-local
   look angles). These use real published mean amplitudes/periods for
   libration, then project to the dome's local horizon with standard
   great-circle bearing/distance trig, treating the Moon as a sphere.
   This is not IAU_MOON-kernel precision, but it is not fabricated either:
   the amplitudes and periods are the same ones used in amateur/observational
   lunar almanacs.
"""

from __future__ import annotations
import math
from datetime import datetime, timezone
from pathlib import Path

from skyfield.api import Loader
from skyfield import almanac

_SYNODIC_MONTH_DAYS = 29.530589       # true synodic period
_ANOMALISTIC_MONTH_DAYS = 27.554550   # libration in longitude period
_DRACONIC_MONTH_DAYS = 27.212221      # libration in latitude period

_LIBRATION_LON_AMPLITUDE_DEG = 7.9
_LIBRATION_LAT_AMPLITUDE_DEG = 6.9

# Reference epoch: a known new moon (2000-01-06 18:14 UTC), used purely as
# a phase-zero anchor for the sinusoidal approximations above.
_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)

# Shared cache convention: outdoors_helpers/local_data, one level up from
# this package, so lunar_sim and sky_sim (siblings under outdoors_helpers)
# both resolve to the SAME folder and share the one downloaded de421.bsp
# instead of each keeping a private copy. skyfield's Loader checks this
# folder first and only hits the network if the file isn't there yet.
_PARENT = Path(__file__).parent            # .../outdoors_helpers/lunar_sim
_DATA_DIR = _PARENT.parent / "local_data"  # .../outdoors_helpers/local_data

_loader = None
_eph = None
_ts = None


def _ephemeris():
    """Lazily load de421 via skyfield's own Loader (handles cache-or-fetch)."""
    global _loader, _eph, _ts
    if _eph is None:
        _loader = Loader(_DATA_DIR)
        _ts = _loader.timescale()
        _eph = _loader("de421.bsp")
    return _eph, _ts


def _days_since_epoch(dt: datetime) -> float:
    return (dt - _EPOCH).total_seconds() / 86400.0


def libration_offset(dt: datetime) -> tuple[float, float]:
    """Returns (lon_deg, lat_deg) optical libration offset from the mean
    sub-Earth point, using published mean amplitudes/periods."""
    d = _days_since_epoch(dt)
    lon = _LIBRATION_LON_AMPLITUDE_DEG * math.sin(2 * math.pi * d / _ANOMALISTIC_MONTH_DAYS)
    lat = _LIBRATION_LAT_AMPLITUDE_DEG * math.sin(2 * math.pi * d / _DRACONIC_MONTH_DAYS)
    return lon, lat


def subsolar_point(dt: datetime) -> tuple[float, float]:
    """Mean selenographic (lat, lon) of the point directly under the Sun.
    Longitude sweeps a full 360 deg per synodic month; latitude wobbles with
    the Moon's small axial tilt to the ecliptic (~1.54 deg), modeled as a
    sinusoid on the draconic period for the same reason as latitude libration."""
    d = _days_since_epoch(dt)
    lon = ((d / _SYNODIC_MONTH_DAYS) * 360.0) % 360.0
    if lon > 180.0:
        lon -= 360.0
    lat = 1.54 * math.sin(2 * math.pi * d / _DRACONIC_MONTH_DAYS)
    return lat, lon


def earth_illuminated_fraction(dt: datetime) -> float:
    """Real geometry: Earth's illuminated fraction as seen from the Moon is
    the complement of the Moon's illuminated fraction as seen from Earth —
    when the Moon is full over Earth, Earth is new over the Moon."""
    eph, ts = _ephemeris()
    t = ts.from_datetime(dt)
    moon_lit_fraction = almanac.fraction_illuminated(eph, "moon", t)
    return 1.0 - moon_lit_fraction


def _great_circle_look_angle(site_lat, site_lon, point_lat, point_lon):
    """Standard bearing/distance spherical trig — altitude/azimuth of
    `point` as seen from `site`, both given as selenographic lat/lon."""
    lat1, lon1 = math.radians(site_lat), math.radians(site_lon)
    lat2, lon2 = math.radians(point_lat), math.radians(point_lon)
    dlon = lon2 - lon1

    cos_c = math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(dlon)
    cos_c = max(-1.0, min(1.0, cos_c))
    separation = math.degrees(math.acos(cos_c))
    altitude = 90.0 - separation

    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    azimuth = math.degrees(math.atan2(y, x)) % 360.0

    return altitude, azimuth


def sun_look_angle(site_lat: float, site_lon: float, dt: datetime) -> tuple[float, float]:
    sub_lat, sub_lon = subsolar_point(dt)
    return _great_circle_look_angle(site_lat, site_lon, sub_lat, sub_lon)


def earth_look_angle(site_lat: float, site_lon: float, dt: datetime) -> tuple[float, float, bool]:
    """Returns (altitude, azimuth, visible). visible=False means the site is
    far-side-only for this libration state — Earth never crests the horizon."""
    lib_lon, lib_lat = libration_offset(dt)
    sub_earth_lat, sub_earth_lon = lib_lat, lib_lon   # mean sub-Earth point is (0,0) + libration
    altitude, azimuth = _great_circle_look_angle(site_lat, site_lon, sub_earth_lat, sub_earth_lon)
    return altitude, azimuth, altitude > -1.0   # small tolerance at the grazing limb