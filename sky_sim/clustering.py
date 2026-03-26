"""
sky_sim/clustering.py
---------------------
Groups visible stars into perceptual clusters that approximate what a
human observer would call "the prominent groups" in the sky.

Design philosophy (Gestalt):
  - A human does not enumerate every pair of nearby stars — they perceive
    regions of density anchored by bright objects.
  - The algorithm works in two stages:
      1. Build a proximity graph with a tight, magnitude-aware connection
         radius and extract connected components.
      2. Run a merge pass: collapse any two components whose centres are
         within MERGE_RADIUS_DEG of each other into one, provided neither
         is anchored by a very bright star that should stand alone.
  - Span (width × height) is computed via gnomonic (tangent-plane)
    projection centred on the cluster's 3D mean vector, which correctly
    handles the zenith and the 360°/0° azimuth wrap.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple
from .types import StarResult

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

# Base connection radius used for average-brightness pairs (~mag 3-4).
# Smaller than the old value to avoid over-connecting a dense dark sky.
_BASE_RADIUS_DEG: float = 2.0

# A bright anchor (mag < this) extends its reach further.
_BRIGHT_ANCHOR_MAG: float = 1.5

# How far the merge pass will pull two cluster centres together (degrees).
# This is the key parameter that reduces "80 tiny clusters" to "~10 regions".
_MERGE_RADIUS_DEG: float = 18.0

# Stars this bright or brighter stay lonely rather than merging into a group.
_LONE_ANCHOR_MAG: float = -0.5   # Sirius, Canopus, etc.


# ---------------------------------------------------------------------------
# Data type
# ---------------------------------------------------------------------------

@dataclass
class StarCluster:
    stars:      List[StarResult]
    leads:      List[StarResult]   # brightest members, used as label
    center_az:  float              # degrees
    center_alt: float              # degrees
    width:      float              # angular span east-west (gnomonic), degrees
    height:     float              # angular span north-south (gnomonic), degrees

    @property
    def total_count(self) -> int:
        return len(self.stars)

    @property
    def brightest_magnitude(self) -> float:
        return self.leads[0].magnitude if self.leads else 99.0


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def angular_distance(az1: float, alt1: float, az2: float, alt2: float) -> float:
    """Great-circle angular distance between two alt-az positions (degrees)."""
    phi1, lam1 = math.radians(alt1), math.radians(az1)
    phi2, lam2 = math.radians(alt2), math.radians(az2)
    cos_d = (math.sin(phi1) * math.sin(phi2) +
             math.cos(phi1) * math.cos(phi2) * math.cos(lam1 - lam2))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_d))))


def _star_to_xyz(az_deg: float, alt_deg: float) -> Tuple[float, float, float]:
    """Convert alt-az to unit 3-vector on the celestial sphere."""
    alt_r = math.radians(alt_deg)
    az_r  = math.radians(az_deg)
    return (
        math.cos(alt_r) * math.cos(az_r),
        math.cos(alt_r) * math.sin(az_r),
        math.sin(alt_r),
    )


def _xyz_to_altaz(x: float, y: float, z: float) -> Tuple[float, float]:
    """Convert unit 3-vector back to (alt_deg, az_deg)."""
    alt = math.degrees(math.atan2(z, math.hypot(x, y)))
    az  = math.degrees(math.atan2(y, x)) % 360
    return alt, az


def _cluster_center(stars: List[StarResult]) -> Tuple[float, float]:
    """Mean direction of a set of stars via 3D vector average. Returns (az, alt)."""
    x = y = z = 0.0
    for s in stars:
        xi, yi, zi = _star_to_xyz(s.azimuth, s.altitude)
        x += xi; y += yi; z += zi
    alt, az = _xyz_to_altaz(x, y, z)
    return az, alt


def _gnomonic_span(stars: List[StarResult],
                   center_az: float, center_alt: float) -> Tuple[float, float]:
    """
    Project all stars onto the tangent plane at (center_az, center_alt) using
    gnomonic projection, then return (width_deg, height_deg).

    This correctly handles the zenith (where azimuth is undefined) and the
    0°/360° azimuth seam that broke the old linear subtraction approach.
    """
    if len(stars) < 2:
        return 0.0, 0.0

    cx, cy, cz = _star_to_xyz(center_az, center_alt)

    # Build tangent-plane axes: east_hat and north_hat
    if abs(center_alt) > 89.5:
        # At the zenith the azimuth direction is degenerate; use cardinal axes
        east_hat  = (1.0, 0.0, 0.0)
        north_hat = (0.0, 1.0, 0.0)
    else:
        az_r = math.radians(center_az)
        ex, ey, ez = -math.sin(az_r), math.cos(az_r), 0.0
        norm = math.hypot(ex, ey)
        east_hat = (ex / norm, ey / norm, 0.0)

        # north_hat = east_hat × centre  (points toward higher altitude)
        nx = east_hat[1] * cz - east_hat[2] * cy
        ny = east_hat[2] * cx - east_hat[0] * cz
        nz = east_hat[0] * cy - east_hat[1] * cx
        norm = math.sqrt(nx*nx + ny*ny + nz*nz)
        if norm < 1e-9:
            return 0.0, 0.0
        north_hat = (nx / norm, ny / norm, nz / norm)

    xs_proj, ys_proj = [], []

    for s in stars:
        sx, sy, sz = _star_to_xyz(s.azimuth, s.altitude)
        denom = sx * cx + sy * cy + sz * cz
        if denom < 1e-6:
            continue
        px = (sx * east_hat[0]  + sy * east_hat[1]  + sz * east_hat[2])  / denom
        py = (sx * north_hat[0] + sy * north_hat[1] + sz * north_hat[2]) / denom
        xs_proj.append(math.degrees(math.atan(px)))
        ys_proj.append(math.degrees(math.atan(py)))

    if not xs_proj:
        return 0.0, 0.0

    return max(xs_proj) - min(xs_proj), max(ys_proj) - min(ys_proj)


# ---------------------------------------------------------------------------
# Connection radius
# ---------------------------------------------------------------------------

def _connection_radius(mag1: float, mag2: float) -> float:
    """
    Angular distance threshold for two stars to be considered perceptually
    connected. The brighter of the two drives the threshold.

      very bright (< 0)  → up to ~8°  (pulls in a wide neighbourhood)
      mag ~1.5           → ~2.0°      (base)
      mag ~3             → ~1.4°
      mag ~5             → ~0.6°      (only group when really close)
    """
    brightest = min(mag1, mag2)
    if brightest < _BRIGHT_ANCHOR_MAG:
        return _BASE_RADIUS_DEG + (_BRIGHT_ANCHOR_MAG - brightest) * 3.0
    return max(0.5, _BASE_RADIUS_DEG - (brightest - _BRIGHT_ANCHOR_MAG) * 0.4)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def fold_stars(stars: List[StarResult],
               max_leads: int = 3) -> Tuple[List[StarCluster], List[StarResult]]:
    """
    Group visible stars into perceptual clusters.

    Returns (clusters, lonely_stars) both sorted brightest-first.
    """
    n = len(stars)
    if n == 0:
        return [], []

    # ------------------------------------------------------------------
    # Stage 1: proximity graph → connected components
    # ------------------------------------------------------------------
    adj: List[List[int]] = [[] for _ in range(n)]

    for i in range(n):
        s1 = stars[i]
        for j in range(i + 1, n):
            s2    = stars[j]
            dist  = angular_distance(s1.azimuth, s1.altitude,
                                     s2.azimuth, s2.altitude)
            if dist <= _connection_radius(s1.magnitude, s2.magnitude):
                adj[i].append(j)
                adj[j].append(i)

    visited:    set             = set()
    components: List[List[StarResult]] = []

    for i in range(n):
        if i in visited:
            continue
        comp  = []
        stack = [i]
        visited.add(i)
        while stack:
            curr = stack.pop()
            comp.append(stars[curr])
            for nb in adj[curr]:
                if nb not in visited:
                    visited.add(nb)
                    stack.append(nb)
        components.append(comp)

    # ------------------------------------------------------------------
    # Stage 2: merge pass
    # Repeatedly merge pairs of components whose 3D-mean centres are
    # within MERGE_RADIUS_DEG, until nothing changes.
    # Brilliant lone stars (_LONE_ANCHOR_MAG) are exempt from absorption.
    # ------------------------------------------------------------------
    def _comp_brightest(comp: List[StarResult]) -> float:
        return min(s.magnitude for s in comp)

    changed = True
    while changed:
        changed      = False
        used         = [False] * len(components)
        new_comps: List[List[StarResult]] = []

        for i in range(len(components)):
            if used[i]:
                continue
            base = components[i]

            for j in range(i + 1, len(components)):
                if used[j]:
                    continue
                other = components[j]

                # Protect brilliant singletons from being swallowed
                if len(base)  == 1 and _comp_brightest(base)  <= _LONE_ANCHOR_MAG:
                    continue
                if len(other) == 1 and _comp_brightest(other) <= _LONE_ANCHOR_MAG:
                    continue

                az_b, alt_b = _cluster_center(base)
                az_o, alt_o = _cluster_center(other)
                if angular_distance(az_b, alt_b, az_o, alt_o) <= _MERGE_RADIUS_DEG:
                    base    = base + other
                    used[j] = True
                    changed = True

            new_comps.append(base)

        components = new_comps

    # ------------------------------------------------------------------
    # Stage 3: build output objects
    # ------------------------------------------------------------------
    clusters: List[StarCluster] = []
    lonely:   List[StarResult]  = []

    for comp in components:
        comp.sort(key=lambda s: s.magnitude)  # brightest first

        if len(comp) == 1:
            lonely.append(comp[0])
            continue

        az_c, alt_c     = _cluster_center(comp)
        width, height   = _gnomonic_span(comp, az_c, alt_c)
        num_leads       = min(max_leads, len(comp))

        clusters.append(StarCluster(
            stars=comp,
            leads=comp[:num_leads],
            center_az=az_c,
            center_alt=alt_c,
            width=width,
            height=height,
        ))

    clusters.sort(key=lambda c: c.brightest_magnitude)
    lonely.sort(key=lambda s: s.magnitude)

    return clusters, lonely