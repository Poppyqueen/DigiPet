"""
sky_sim/cloud_sim.py
--------------------
Three-layer cloud simulation driven by Open-Meteo weather data.

Layers:
  low   — stratus / fog    (0–3 km)    fully opaque, large patches
  mid   — altostratus      (3–8 km)    semi-opaque, medium patches
  high  — cirrus           (8+ km)     thin/wispy, dims but rarely fully blocks

Each layer is an infinite simplex noise field sampled via a moving window.
Wind advects the window; a slow morph_time parameter evolves cloud shapes.

Two clocks:
  weather_update()  — called when Open-Meteo refreshes (every ~15 min)
                      sets *targets*, not immediate values
  tick()            — called every N minutes by the simulator
                      lerps current state toward targets, advances offsets
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Tuple

import numpy as np
from opensimplex import OpenSimplex
import random
# TODO: REMOVE ALL DEBUG LATER
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Noise spatial scale per layer — controls patch size on sky dome
# Higher = finer / smaller patches
LOW_NOISE_SCALE   = 1.8    # large chunky stratus
MID_NOISE_SCALE   = 2.8    # medium altostratus blobs
HIGH_NOISE_SCALE  = 4.5    # fine fibrous cirrus streaks

# Max opacity contribution per layer
LOW_MAX_OPACITY   = 1.00   # stratus can fully block
MID_MAX_OPACITY   = 0.80   # altostratus mostly blocks
HIGH_MAX_OPACITY  = 0.35   # cirrus just dims

# How fast simulated values chase weather targets (fraction per minute)
LERP_RATE_COVER   = 0.04   # cloud cover changes slowly
LERP_RATE_WIND    = 0.06   # wind direction changes a bit faster

# How fast cloud shapes morph (noise time axis, arbitrary units / minute)
MORPH_RATE        = 0.2# 0.0475 # 0.2 # 0.003

# Smoothstep edge width for cloud boundary (in noise units)
CLOUD_EDGE_WIDTH  = 0.15

# km/h → sky-dome units per minute (empirically tuned)
WIND_SCALE        =  0.007# 0.0008


# ---------------------------------------------------------------------------
# Vector2 helper
# ---------------------------------------------------------------------------

@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def lerp_toward(self, target: "Vec2", t: float) -> "Vec2":
        return Vec2(
            self.x + (target.x - self.x) * t,
            self.y + (target.y - self.y) * t,
        )


def _wind_vector(speed_kmh: float, direction_deg: float) -> Vec2:
    """Convert meteorological wind (speed + FROM direction) to Vec2."""
    # Meteorological: direction is where wind comes FROM
    # We want where it's going TO for advection
    rad = math.radians(direction_deg + 180.0)
    return Vec2(
        x=math.cos(rad) * speed_kmh * WIND_SCALE,
        y=math.sin(rad) * speed_kmh * WIND_SCALE,
    )


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# Single noise layer
# ---------------------------------------------------------------------------

class _NoiseLayer:
    """
    One cloud layer. Infinite simplex noise field sampled via moving window.
    """

    def __init__(self, seed: int, spatial_scale: float, max_opacity: float):
        self._noise       = OpenSimplex(seed=seed)
        self._scale       = spatial_scale
        self._max_opacity = max_opacity

        # Simulation state
        self.current_cover: float = 0.0    # 0.0–1.0
        self.target_cover:  float = 0.0
        self.offset:        Vec2  = Vec2()
        self.morph_time:    float = 0.0

    def tick(self, delta_min: float, wind: Vec2, morph_delta: float,
             lerp_rate: float) -> None:
        self.current_cover += (self.target_cover - self.current_cover) * lerp_rate * delta_min
        self.current_cover  = max(0.0, min(1.0, self.current_cover))
        self.offset          = self.offset + wind * delta_min
        self.morph_time     += morph_delta

    def opacity_at(self, sky_x: float, sky_y: float) -> float:
        """
        Sample opacity at a sky-dome position.
        sky_x, sky_y are Cartesian projections of (az, alt) — see _sky_to_xy.
        Returns 0.0 (transparent) to max_opacity (full block).
        """
        if self.current_cover <= 0.001:
            return 0.0

        nx = (sky_x + self.offset.x) * self._scale
        ny = (sky_y + self.offset.y) * self._scale
        nt = self.morph_time

        # 2D + time simplex noise, remapped 0→1
        raw = (self._noise.noise3(nx, ny, nt) + 1.0) * 0.5

        # coverage sets the threshold
        # smoothstep gives soft cloud edges instead of hard cutoff
        cover = self.current_cover
        edge0 = cover - CLOUD_EDGE_WIDTH
        edge1 = cover + CLOUD_EDGE_WIDTH
        presence = _smoothstep(edge1, edge0, raw)   # inverted: raw > cover → cloud

        return presence * self._max_opacity
    
    def set_aware_int(self) -> None: # not sure if this makes sense, replaces snap to target and empty init.
        self.current_cover =  self.target_cover - random.uniform(0.005,0.05) # this could add or substract, it is not doing that rn 
    
    def snap_to_target(self) -> None:  # We added this to snap to the target at startup, this was so we don't start with empty clouds in a place that already has clouds, but it might have broken the cat and mouse game it had, and now the simulation instead of chasing the state, is hallucinating a future and trying to correct afterwards- I think maybe instead of snapping directly, we select a random range of clouds and weather data to start to revert back to the slow morhping into its state
        """Instantly fast-forwards the current simulation state to the targets."""
        self.current_cover = self.target_cover


# ---------------------------------------------------------------------------
# Public cloud simulation
# ---------------------------------------------------------------------------

class CloudSimulation:
    """
    Three-layer cloud simulation.

    Initialized with clouds. Call weather_update() with a WeatherSnapshot
    to set targets, then tick() to advance the simulation.
    """

    def __init__(self, seed: int = 42):
        self._low  = _NoiseLayer(seed=seed,       spatial_scale=LOW_NOISE_SCALE,  max_opacity=LOW_MAX_OPACITY)
        self._mid  = _NoiseLayer(seed=seed + 111, spatial_scale=MID_NOISE_SCALE,  max_opacity=MID_MAX_OPACITY)
        self._high = _NoiseLayer(seed=seed + 222, spatial_scale=HIGH_NOISE_SCALE, max_opacity=HIGH_MAX_OPACITY)

        # Wind vectors — low and high layers move at different speeds
        self._wind_low:  Vec2 = Vec2()
        self._wind_high: Vec2 = Vec2()
        self._target_wind_low:  Vec2 = Vec2()
        self._target_wind_high: Vec2 = Vec2()

        self._tick_count: int = 0

        self._prev_telemetry = None # DEBUG UTILITY

    # ------------------------------------------------------------------
    # Weather clock
    # ------------------------------------------------------------------

    def weather_update(self, weather) -> None:
        """
        Receive new weather data (WeatherSnapshot).
        Updates targets only — simulation interpolates toward them on tick().
        """
        self._low.target_cover  = weather.cloud_cover_low  / 100.0
        self._mid.target_cover  = weather.cloud_cover_mid  / 100.0
        self._high.target_cover = weather.cloud_cover_high / 100.0

        self._target_wind_low  = _wind_vector(weather.wind_speed_10m,  weather.wind_direction_10m)
        self._target_wind_high = _wind_vector(weather.wind_speed_120m, weather.wind_direction_10m)

    # ------------------------------------------------------------------
    # Simulation clock
    # ------------------------------------------------------------------

    def tick(self, delta_minutes: float = 1.0) -> None:
        """Advance simulation by delta_minutes. Typically 1–10 minutes."""


        lr = LERP_RATE_COVER
        wr = LERP_RATE_WIND
        morph = MORPH_RATE * delta_minutes

        # Interpolate wind vectors
        self._wind_low  = self._wind_low.lerp_toward(self._target_wind_low,  wr * delta_minutes)
        self._wind_high = self._wind_high.lerp_toward(self._target_wind_high, wr * delta_minutes)

        # Tick each layer
        self._low.tick(delta_minutes,  self._wind_low,  morph, lr)
        self._mid.tick(delta_minutes,  self._wind_low * 0.6, morph * 0.8, lr)
        self._high.tick(delta_minutes, self._wind_high, morph * 0.5, lr)

        self._tick_count += 1


    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def opacity_at(self, azimuth_deg: float, altitude_deg: float) -> float:
        """
        Combined opacity at a sky position. 0.0 = transparent, 1.0 = fully blocked.
        Uses multiply-transparencies model for physically correct layer combination.
        """
        x, y = _sky_to_xy(azimuth_deg, altitude_deg)

        low  = self._low.opacity_at(x, y)
        mid  = self._mid.opacity_at(x, y)
        high = self._high.opacity_at(x, y)

        # Each layer independently blocks a fraction of remaining light
        return 1.0 - (1.0 - low) * (1.0 - mid) * (1.0 - high)

    def simulated_cloud_coverage(self, samples: int = 256) -> float:
        """
        Estimate actual sky coverage by sampling the dome.
        Returns 0.0–1.0.
        """
        blocked = 0
        rng = np.random.default_rng(seed=0)

        # Uniform hemisphere sampling
        azimuths  = rng.uniform(0,  360, samples)
        altitudes = rng.uniform(0,  90,  samples)

        for az, alt in zip(azimuths, altitudes):
            if self.opacity_at(az, alt) > 0.5:
                blocked += 1

        return blocked / samples
    
    def inits(self): 
        self._low.set_aware_int()
        self._mid.set_aware_int()
        self._high.set_aware_int()
        self._wind_low = self._target_wind_low
        self._wind_high = self._target_wind_high        


    def snap_to_targets(self) -> None:
        """Instantly apply target weather states (useful for initialization)."""
        self._low.snap_to_target()
        self._mid.snap_to_target()
        self._high.snap_to_target()
        self._wind_low = self._target_wind_low
        self._wind_high = self._target_wind_high
        
    @property
    def tick_count(self) -> int:
        return self._tick_count


# ---------------------------------------------------------------------------
# Sky dome coordinate helpers
# ---------------------------------------------------------------------------

def _sky_to_xy(azimuth_deg: float, altitude_deg: float) -> Tuple[float, float]:
    """
    Project sky dome position to 2D Cartesian coordinates for noise sampling.
    Uses equal-area-ish projection: distance from zenith proportional to
    (90 - altitude), so horizon is at radius 1.0 and zenith is at 0,0.
    """
    alt_rad = math.radians(altitude_deg)
    az_rad  = math.radians(azimuth_deg)

    # Distance from zenith (0 at top, 1 at horizon)
    r = 1.0 - (alt_rad / (math.pi / 2.0))

    x = r * math.cos(az_rad)
    y = r * math.sin(az_rad)
    return x, y