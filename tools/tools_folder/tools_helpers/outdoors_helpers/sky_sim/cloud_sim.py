"""
sky_sim/cloud_sim.py
--------------------
Three-layer cloud simulation driven by Open-Meteo weather data.

Layers:
  low   — stratus / fog    (0–3 km)    fully opaque, large patches
  mid   — altostratus      (3–8 km)    semi-opaque, medium patches
  high  — cirrus           (8+ km)     thin/wispy, dims but rarely fully blocks

Each layer uses a distinct noise strategy matched to the morphological structure
of its cloud type:

  low   — domain-warped simplex: turbulent, folded, cauliflower-like edges
           (cumulus convective towers, ragged stratus boundaries)
  mid   — cellular/Worley blend: organized puff structure, mackerel-sky spacing
           (altocumulus streets, altostratus with broken texture)
  high  — anisotropic simplex: fibrous streaks aligned to wind direction
           (cirrus uncinus, cirrostratus veil)

 values
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Noise spatial scale per layer — controls patch size on sky dome
LOW_NOISE_SCALE   = 2.5
MID_NOISE_SCALE   = 2.5
HIGH_NOISE_SCALE  = 2.5

# Max opacity contribution per layer (transmittance ceiling)
LOW_MAX_OPACITY   = 1.00
MID_MAX_OPACITY   = 0.80
HIGH_MAX_OPACITY  = 0.40

# Opacity bias — amplifies the noise field before thresholding.
# > 1.0 = interior pixels feel denser (more blocking per unit of cloud body)
# < 1.0 = interior pixels stay thin throughout (genuinely wispy)
LOW_OPACITY_BIAS   = 1.8   # stratus: dense, heavy interior
MID_OPACITY_BIAS   = 1.6   # altostratus: moderately dense
HIGH_OPACITY_BIAS  = 0.8   # cirrus: thin and translucent throughout

# Edge sharpness — multiplier on edge_width per layer.
# < 1.0 = narrower transition zone (crisper boundary)
# > 1.0 = wider transition zone (softer, more diffuse boundary)
LOW_EDGE_SHARPNESS   = 0.35   # stratus: hard-edged patches
MID_EDGE_SHARPNESS   = 0.95   # altostratus: neutral
HIGH_EDGE_SHARPNESS  = 1.45   # cirrus: wide, feathered edges

# How fast simulated values chase weather targets (fraction per minute)
LERP_RATE_COVER   = 0.04
LERP_RATE_WIND    = 0.06

# How fast cloud shapes morph (noise time axis, arbitrary units / minute)
MORPH_RATE        = 0.02375 # 0.2 # 0.0475

# Smoothstep edge width for cloud boundary (in noise units)
CLOUD_EDGE_WIDTH  = 0.15

# km/h → sky-dome units per minute
WIND_SCALE        = 0.007

# ---------------------------------------------------------------------------
# Layer-specific noise parameters
# ---------------------------------------------------------------------------

# LOW — domain warp strength: how much the warp field displaces sample coords.
# Higher = more turbulent, folded edges (more cumulus-like).
# Lower  = smoother, more stratus-like.
LOW_WARP_STRENGTH = 0.55

# LOW — warp field frequency relative to primary field.
# Lower = large-scale folds; higher = small chaotic wrinkles.
LOW_WARP_FREQUENCY = 0.45

# MID — blend between cellular (Worley) and simplex character.
# 0.0 = pure simplex (no cell structure)
# 1.0 = pure cellular (sharp Voronoi-like puffs)
MID_CELLULAR_BLEND = 0.55

# MID — number of jitter cells per unit of sky-dome space.
# Higher = more, smaller puffs (finer altocumulus).
MID_CELL_DENSITY  = 3.5

# MID — jitter amount: 0 = regular grid, 1 = fully random cell centres.
# Values around 0.85–0.95 give the natural irregular-but-periodic spacing.
MID_CELL_JITTER   = 0.90

# HIGH — anisotropy ratio: how much coords are stretched along the wind axis.
# 1.0 = isotropic (normal simplex blobs); 6.0 = strongly fibrous streaks.
HIGH_ANISOTROPY   = 6.0

# HIGH — cross-wind warp strength: adds gentle waviness to cirrus streaks.
# 0.0 = perfectly straight fibres; 0.3 = natural wispy curls.
HIGH_CROSS_WARP   = 0.22


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

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalized(self) -> "Vec2":
        l = self.length()
        if l < 1e-9:
            return Vec2(1.0, 0.0)
        return Vec2(self.x / l, self.y / l)

    def perpendicular(self) -> "Vec2":
        """90° CCW rotation."""
        return Vec2(-self.y, self.x)


def _wind_vector(speed_kmh: float, direction_deg: float) -> Vec2:
    """Convert meteorological wind (speed + FROM direction) to Vec2."""
    rad = math.radians(direction_deg + 180.0)
    return Vec2(
        x=math.cos(rad) * speed_kmh * WIND_SCALE,
        y=math.sin(rad) * speed_kmh * WIND_SCALE,
    )


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# Cellular (Worley) distance helper
# ---------------------------------------------------------------------------

def _worley_f1(x: float, y: float, density: float, jitter: float,
               rng_seed: int = 0) -> float:
    """
    Returns the distance to the nearest jittered grid cell centre,
    normalised to approximately [0, 1].

    This is F1 Worley noise — the closest-point distance. It produces
    the dark-centre / bright-edge Voronoi pattern that maps well to
    organised cloud puffs when inverted (1 - f1).

    density  — cells per unit; higher = more, smaller puffs
    jitter   — 0 = regular grid, 1 = fully random centres
    """
    scale = density
    sx = x * scale
    sy = y * scale

    ix = math.floor(sx)
    iy = math.floor(sy)

    min_dist_sq = 1e9

    # Search 3×3 neighbourhood of grid cells
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            cx = ix + dx
            cy = iy + dy

            # Deterministic per-cell jitter via a hash
            h = (cx * 1619 + cy * 31337 + rng_seed * 6971) & 0xFFFFFF
            jx = (((h * 2654435761) & 0xFFFFFF) / 0xFFFFFF - 0.5) * jitter
            jy = (((h * 2246822519) & 0xFFFFFF) / 0xFFFFFF - 0.5) * jitter

            cell_x = cx + 0.5 + jx
            cell_y = cy + 0.5 + jy

            ddx = sx - cell_x
            ddy = sy - cell_y
            dist_sq = ddx * ddx + ddy * ddy
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq

    # Max possible distance in a unit cell is ~0.7 (corner to centre)
    # Normalise so typical range is 0–1
    return min(math.sqrt(min_dist_sq) * 1.4, 1.0)


# ---------------------------------------------------------------------------
# Base noise layer (shared state + tick logic)
# ---------------------------------------------------------------------------

class _NoiseLayer:
    """
    One cloud layer. Manages coverage/wind state and lerp logic.
    Subclasses override _sample_raw() to provide their noise character.
    """

    def __init__(self, seed: int, spatial_scale: float, max_opacity: float,
                 opacity_bias: float = 1.0, edge_sharpness: float = 1.0):
        self._noise       = OpenSimplex(seed=seed)
        self._scale       = spatial_scale
        self._max_opacity = max_opacity
        self._seed        = seed

        # Per-layer optical character — set by subclass constructors,
        # not changed at runtime (unlike edge_width which is weather-driven).
        self.opacity_bias:   float = opacity_bias
        self.edge_sharpness: float = edge_sharpness

        self.current_cover: float = 0.0
        self.target_cover:  float = 0.0
        self.offset:        Vec2  = Vec2()
        self.morph_time:    float = 0.0

        # Weather-driven noise parameters — overwritten by weather_update()
        self.edge_width: float = CLOUD_EDGE_WIDTH

    def tick(self, delta_min: float, wind: Vec2, morph_delta: float,
             lerp_rate: float) -> None:
        self.current_cover += (self.target_cover - self.current_cover) * lerp_rate * delta_min
        self.current_cover  = max(0.0, min(1.0, self.current_cover))
        self.offset          = self.offset + wind * delta_min
        self.morph_time     += morph_delta

    def _sample_raw(self, sky_x: float, sky_y: float) -> float:
        """
        Return a raw noise value in [0, 1] at the given sky position.
        Subclasses implement their specific noise strategy here.
        """
        nx = (sky_x + self.offset.x) * self._scale
        ny = (sky_y + self.offset.y) * self._scale
        return (self._noise.noise3(nx, ny, self.morph_time) + 1.0) * 0.5

    def opacity_at(self, sky_x: float, sky_y: float) -> float:
        if self.current_cover <= 0.001:
            return 0.0

        raw = self._sample_raw(sky_x, sky_y)

        # opacity_bias scales the noise field before thresholding.
        # High bias → pixels deep inside the cloud read as "more present",
        # increasing blocking without touching the coverage threshold.
        biased_raw = max(0.0, min(1.0, raw * self.opacity_bias))

        # edge_sharpness scales the transition zone width:
        # narrow = hard edge (stratus), wide = feathered edge (cirrus).
        cover = self.current_cover
        half_edge = self.edge_width * self.edge_sharpness
        edge0 = cover - half_edge
        edge1 = cover + half_edge
        presence = _smoothstep(edge1, edge0, biased_raw)

        return presence * self._max_opacity

    def snap_to_target(self) -> None:
        self.current_cover = self.target_cover

    def set_aware_init(self) -> None:
        self.current_cover = self.target_cover - random.uniform(0.005, 0.05)


# ---------------------------------------------------------------------------
# Low layer — domain-warped simplex
# ---------------------------------------------------------------------------

class _LowCloudLayer(_NoiseLayer):
    """
    Stratus / stratocumulus / cumulus.

    Domain warping distorts the sampling coordinates with a secondary noise
    field before evaluating the primary. This folds and turbulates the cloud
    boundaries, producing the cauliflower edges of cumulus and the ragged
    patches of stratus — rather than the smooth organic blobs of plain simplex.

    Two warp axes (x and y) use the same noise instance at offset seeds
    (the classic Inigo Quilez technique with coordinate offsets 5.2, 1.3).
    """

    def __init__(self, seed: int, spatial_scale: float, max_opacity: float):
        super().__init__(seed, spatial_scale, max_opacity,
                         opacity_bias=LOW_OPACITY_BIAS,
                         edge_sharpness=LOW_EDGE_SHARPNESS)
        self._warp_noise  = OpenSimplex(seed=seed + 47)
        self.warp_strength: float = LOW_WARP_STRENGTH

    def _sample_raw(self, sky_x: float, sky_y: float) -> float:
        ox = (sky_x + self.offset.x) * self._scale
        oy = (sky_y + self.offset.y) * self._scale
        ot = self.morph_time * 0.6   # warp field morphs slightly slower

        wf = LOW_WARP_FREQUENCY
        ws = self.warp_strength

        warp_x = self._warp_noise.noise3(ox * wf,       oy * wf,       ot) * ws
        warp_y = self._warp_noise.noise3(ox * wf + 5.2, oy * wf + 1.3, ot) * ws

        nx = ox + warp_x
        ny = oy + warp_y

        return (self._noise.noise3(nx, ny, self.morph_time) + 1.0) * 0.5


# ---------------------------------------------------------------------------
# Mid layer — cellular / Worley blend
# ---------------------------------------------------------------------------

class _MidCloudLayer(_NoiseLayer):
    """
    Altocumulus / altostratus / nimbostratus.

    Blends inverted Worley F1 (organized puff pattern) with simplex
    (irregular background texture). The blend produces the characteristic
    'mackerel sky' — periodic but not perfectly regular spacing of puffs.

    cellular_blend is driven down toward 0 during precipitation events
    (nimbostratus is a solid sheet, not organised puffs).
    """

    def __init__(self, seed: int, spatial_scale: float, max_opacity: float):
        super().__init__(seed, spatial_scale, max_opacity,
                         opacity_bias=MID_OPACITY_BIAS,
                         edge_sharpness=MID_EDGE_SHARPNESS)
        self.cellular_blend: float = MID_CELLULAR_BLEND

    def _sample_raw(self, sky_x: float, sky_y: float) -> float:
        # Apply offset BEFORE scale (same as base class) — offset units are sky-dome
        ox = (sky_x + self.offset.x) * self._scale
        oy = (sky_y + self.offset.y) * self._scale

        # Worley — add a slow time-based translation so cells visibly drift
        # rather than tiling identically as the offset advances
        f1 = _worley_f1(
            ox + self.morph_time * 0.15,   # ← drift along x
            oy + self.morph_time * 0.07,   # ← drift along y (different rate = shear)
            MID_CELL_DENSITY, MID_CELL_JITTER, self._seed
        )
        cellular = 1.0 - f1

        simplex = (self._noise.noise3(ox, oy, self.morph_time) + 1.0) * 0.5
        return cellular * self.cellular_blend + simplex * (1.0 - self.cellular_blend)


# ---------------------------------------------------------------------------
# High layer — anisotropic simplex
# ---------------------------------------------------------------------------

class _HighCloudLayer(_NoiseLayer):
    """
    Cirrus / cirrocumulus / cirrostratus.

    Stretches the noise sampling coordinates along the wind direction,
    producing the long fibrous streaks characteristic of cirrus. A secondary
    cross-wind warp adds natural curl and waviness (cirrus uncinus hooks).

    Wind direction is updated externally via set_wind_direction().
    """

    def __init__(self, seed: int, spatial_scale: float, max_opacity: float):
        super().__init__(seed, spatial_scale, max_opacity,
                         opacity_bias=HIGH_OPACITY_BIAS,
                         edge_sharpness=HIGH_EDGE_SHARPNESS)
        self._warp_noise   = OpenSimplex(seed=seed + 83)
        self._wind_along   = Vec2(1.0, 0.0)   # unit vector along wind
        self._wind_cross   = Vec2(0.0, 1.0)   # unit vector perpendicular

    def set_wind_direction(self, wind: Vec2) -> None:
        """Call each tick with the current (possibly interpolated) wind vector."""
        self._wind_along = wind.normalized()
        self._wind_cross = self._wind_along.perpendicular()

    def _sample_raw(self, sky_x: float, sky_y: float) -> float:
        ox = sky_x * self._scale
        oy = sky_y * self._scale

        # Project into wind-aligned frame FIRST, then add offset in that frame
        along = ox * self._wind_along.x + oy * self._wind_along.y
        cross  = ox * self._wind_cross.x + oy * self._wind_cross.y

        # Decompose offset into wind-aligned components
        off_along = self.offset.x * self._wind_along.x + self.offset.y * self._wind_along.y
        off_cross  = self.offset.x * self._wind_cross.x + self.offset.y * self._wind_cross.y

        # Apply offset AFTER projection so each axis moves at the right visual rate
        sa = (along + off_along) / HIGH_ANISOTROPY
        sc = (cross  + off_cross) * HIGH_ANISOTROPY * 0.18

        warp = self._warp_noise.noise3(
            sa * 0.5, sc * 0.5, self.morph_time * 0.4
        ) * HIGH_CROSS_WARP

        return (self._noise.noise3(sa, sc + warp, self.morph_time * 0.5) + 1.0) * 0.5


# ---------------------------------------------------------------------------
# Public cloud simulation
# ---------------------------------------------------------------------------

class CloudSimulation:
    """
    Three-layer cloud simulation.

    Each layer uses a noise strategy matched to its cloud morphology:
      _LowCloudLayer  — domain-warped simplex (turbulent edges)
      _MidCloudLayer  — Worley/simplex blend (organised puff structure)
      _HighCloudLayer — anisotropic simplex (fibrous wind-aligned streaks)

    The public interface is unchanged from the original implementation.
    """

    def __init__(self, seed: int = 42):
        self._low  = _LowCloudLayer( seed=seed,       spatial_scale=LOW_NOISE_SCALE,  max_opacity=LOW_MAX_OPACITY)
        self._mid  = _MidCloudLayer( seed=seed + 111, spatial_scale=MID_NOISE_SCALE,  max_opacity=MID_MAX_OPACITY)
        self._high = _HighCloudLayer(seed=seed + 222, spatial_scale=HIGH_NOISE_SCALE, max_opacity=HIGH_MAX_OPACITY)

        self._wind_low:  Vec2 = Vec2()
        self._wind_high: Vec2 = Vec2()
        self._target_wind_low:  Vec2 = Vec2()
        self._target_wind_high: Vec2 = Vec2()

        self._tick_count: int = 0
        self._prev_telemetry = None

    # ------------------------------------------------------------------
    # Weather clock
    # ------------------------------------------------------------------

    def weather_update(self, weather) -> None:
        # -- Cloud cover targets -----------------------------------------------
        self._low.target_cover  = weather.cloud_cover_low  / 100.0
        self._mid.target_cover  = weather.cloud_cover_mid  / 100.0
        self._high.target_cover = weather.cloud_cover_high / 100.0

        # -- Wind vectors -------------------------------------------------------
        self._target_wind_low  = _wind_vector(weather.wind_speed_10m,  weather.wind_direction_10m)
        self._target_wind_high = _wind_vector(weather.wind_speed_120m, weather.wind_direction_10m)

        # -- Derived noise parameters ------------------------------------------
        # These are applied immediately (not lerped) since weather_update fires
        # only every ~15 min and the changes are perceptually gradual anyway.

        cape        = weather.cape        or 0.0
        temperature = weather.temperature or 0.0
        dew_point   = weather.dew_point   or 0.0
        visibility  = weather.visibility_m or 20_000.0
        code        = weather.weather_code or 0

        # 1. CAPE → low layer warp strength
        #    Physical: higher CAPE = more instability = more convective turbulence
        #    Mapping: soft curve so 0–300 J/kg (stable/stratus) maps near 0.0,
        #    1000+ J/kg (convective) approaches 1.0, with diminishing returns above that.
        #    WMO codes 95–99 (thunderstorm) floor CAPE contribution at 0.7 regardless.
        cape_norm = 1.0 - math.exp(-cape / 800.0)   # 0.0 → 0.0, 800 → 0.63, 2400 → 0.95
        if code >= 95:                                # thunderstorm — guarantee convective look
            cape_norm = max(cape_norm, 0.70)
        self._low.warp_strength = 0.15 + cape_norm * 0.65   # range: 0.15 (stable) – 0.80 (severe)

        # 2. Dew point depression → edge softness on all layers
        #    Physical: small depression (near-saturated air) = diffuse cloud edges,
        #    large depression (dry air) = sharp, crisp boundaries.
        #    Depression of 0–2°C → wide/soft; 12°C+ → narrow/crisp.
        depression = max(0.0, temperature - dew_point)
        # Normalise: 0°C depression → 1.0 (maximum softness), 15°C → 0.0 (crispest)
        depression_norm = max(0.0, 1.0 - depression / 15.0)
        edge_width = 0.06 + depression_norm * 0.22   # range: 0.06 (crisp) – 0.28 (diffuse)
        self._low.edge_width  = edge_width
        self._mid.edge_width  = edge_width * 0.85    # mid layer slightly crisper
        self._high.edge_width = edge_width * 0.60    # cirrus always relatively wispy/thin

        # 3. Visibility → fog mode on low layer
        #    Physical: visibility < ~2000m means we're at or inside cloud base.
        #    Fog is laminar (no convective mixing) so warp should be suppressed
        #    regardless of CAPE. Also note WMO codes 45/48 = fog/depositing fog.
        is_fog = (visibility < 2000.0) or (code in (45, 48))
        if is_fog:
            # Fog: smooth, almost unwrapped simplex. Warp still present but minimal
            # so there's some gentle undulation at the fog layer boundary.
            self._low.warp_strength = min(self._low.warp_strength, 0.12)

        # 4. Weather code → precipitation mode on mid layer
        #    WMO 51–67 (drizzle/rain) and 71–77 (snow) imply nimbostratus —
        #    thick, continuous mid layer. Push cellular blend down so it looks
        #    more like a solid sheet than organised puffs.
        is_precipitating = (51 <= code <= 77) or (80 <= code <= 82)
        if is_precipitating:
            self._mid.cellular_blend = max(0.0, MID_CELLULAR_BLEND - 0.35)
        else:
            self._mid.cellular_blend = MID_CELLULAR_BLEND

    # ------------------------------------------------------------------
    # Simulation clock
    # ------------------------------------------------------------------

    def tick(self, delta_minutes: float = 1.0) -> None:
        lr = LERP_RATE_COVER
        wr = LERP_RATE_WIND
        morph = MORPH_RATE * delta_minutes

        self._wind_low  = self._wind_low.lerp_toward(self._target_wind_low,  wr * delta_minutes)
        self._wind_high = self._wind_high.lerp_toward(self._target_wind_high, wr * delta_minutes)

        # Give high layer its current wind direction for anisotropy
        self._high.set_wind_direction(self._wind_high)

        self._low.tick( delta_minutes, self._wind_low,          morph,       lr)
        self._mid.tick( delta_minutes, self._wind_low  * 0.6,   morph * 0.8, lr)
        self._high.tick(delta_minutes, self._wind_high,          morph * 0.5, lr)

        self._tick_count += 1

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def opacity_at(self, azimuth_deg: float, altitude_deg: float) -> float:
        x, y = _sky_to_xy(azimuth_deg, altitude_deg)

        low  = self._low.opacity_at(x, y)
        mid  = self._mid.opacity_at(x, y)
        high = self._high.opacity_at(x, y)

        return 1.0 - (1.0 - low) * (1.0 - mid) * (1.0 - high)

    def simulated_cloud_coverage(self, samples: int = 256) -> float:
        blocked = 0
        rng = np.random.default_rng(seed=0)
        azimuths = rng.uniform(0, 360, samples)

        # Sample altitudes proportional to cos(alt) — correct solid-angle weighting.
        # Equivalent to: alt = arcsin(uniform(0, 1)) mapped to [0, 90]
        u = rng.uniform(0.0, 1.0, samples)
        altitudes = np.degrees(np.arcsin(u))  # concentrates samples near horizon, not zenith

        for az, alt in zip(azimuths, altitudes):
            if self.opacity_at(az, alt) > 0.5:
                blocked += 1
        return blocked / samples

    def snap_to_targets(self) -> None:
        self._low.snap_to_target()
        self._mid.snap_to_target()
        self._high.snap_to_target()
        self._wind_low  = self._target_wind_low
        self._wind_high = self._target_wind_high
        self._high.set_wind_direction(self._wind_high)

    def inits(self) -> None:
        self._low.set_aware_init()
        self._mid.set_aware_init()
        self._high.set_aware_init()
        self._wind_low  = self._target_wind_low
        self._wind_high = self._target_wind_high
        self._high.set_wind_direction(self._wind_high)

    @property
    def tick_count(self) -> int:
        return self._tick_count


# ---------------------------------------------------------------------------
# Sky dome coordinate helpers
# ---------------------------------------------------------------------------

def _sky_to_xy(azimuth_deg: float, altitude_deg: float) -> Tuple[float, float]:
    """
    Project sky dome position to 2D Cartesian coordinates for noise sampling.
    Equal-area-ish projection: distance from zenith proportional to
    (90 - altitude). Horizon is at radius 1.0, zenith at 0, 0.
    """
    alt_rad = math.radians(altitude_deg)
    az_rad  = math.radians(azimuth_deg)

    r = 1.0 - (alt_rad / (math.pi / 2.0))

    x = r * math.cos(az_rad)
    y = r * math.sin(az_rad)
    return x, y