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

Performance notes (numpy rewrite):
  - All pairwise angular distances are computed in one vectorized broadcast
    (no Python loop over star pairs).
  - The connection-radius matrix is also fully vectorized.
  - Gnomonic span uses numpy dot products instead of per-star Python loops.
  - Component extraction (BFS/union-find) still has a Python loop over
    components, but n ≲ 9 000 naked-eye stars and the graph is very sparse,
    so this is not a bottleneck.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from .types import StarResult

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

_BASE_RADIUS_DEG: float    = 2.0
_BRIGHT_ANCHOR_MAG: float  = 1.5
_MERGE_RADIUS_DEG: float   = 18.0
_LONE_ANCHOR_MAG: float    = -0.5


# ---------------------------------------------------------------------------
# Data type
# ---------------------------------------------------------------------------

@dataclass
class StarCluster:
    stars:      List[StarResult]
    leads:      List[StarResult]
    center_az:  float
    center_alt: float
    width:      float
    height:     float

    @property
    def total_count(self) -> int:
        return len(self.stars)

    @property
    def brightest_magnitude(self) -> float:
        return self.leads[0].magnitude if self.leads else 99.0


# ---------------------------------------------------------------------------
# Geometry helpers (scalar — used only for single-point queries)
# ---------------------------------------------------------------------------

def angular_distance(az1: float, alt1: float, az2: float, alt2: float) -> float:
    """Great-circle angular distance between two alt-az positions (degrees)."""
    phi1, lam1 = math.radians(alt1), math.radians(az1)
    phi2, lam2 = math.radians(alt2), math.radians(az2)
    cos_d = (math.sin(phi1) * math.sin(phi2) +
             math.cos(phi1) * math.cos(phi2) * math.cos(lam1 - lam2))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_d))))


def _star_to_xyz(az_deg: float, alt_deg: float) -> Tuple[float, float, float]:
    alt_r = math.radians(alt_deg)
    az_r  = math.radians(az_deg)
    return (
        math.cos(alt_r) * math.cos(az_r),
        math.cos(alt_r) * math.sin(az_r),
        math.sin(alt_r),
    )


def _xyz_to_altaz(x: float, y: float, z: float) -> Tuple[float, float]:
    alt = math.degrees(math.atan2(z, math.hypot(x, y)))
    az  = math.degrees(math.atan2(y, x)) % 360
    return alt, az


# ---------------------------------------------------------------------------
# Vectorized geometry helpers (numpy)
# ---------------------------------------------------------------------------

def _stars_to_xyz_array(azimuths: np.ndarray, altitudes: np.ndarray) -> np.ndarray:
    """
    Convert arrays of (az, alt) in degrees to unit XYZ vectors.
    Returns shape (n, 3).
    """
    alt_r = np.radians(altitudes)
    az_r  = np.radians(azimuths)
    x = np.cos(alt_r) * np.cos(az_r)
    y = np.cos(alt_r) * np.sin(az_r)
    z = np.sin(alt_r)
    return np.stack([x, y, z], axis=1)          # (n, 3)


def _pairwise_angular_distance(xyz: np.ndarray) -> np.ndarray:
    """
    Vectorized great-circle distances between all pairs of unit vectors.
    Returns symmetric (n, n) matrix in degrees.
    Uses the identity: angle = arccos(dot(u, v)).
    """
    # dot products via matrix multiplication: (n, 3) @ (3, n) → (n, n)
    dots = np.clip(xyz @ xyz.T, -1.0, 1.0)
    return np.degrees(np.arccos(dots))           # (n, n), symmetric, zero diagonal


def _connection_radius_matrix(mags: np.ndarray) -> np.ndarray:
    """
    Vectorized connection radii for every pair (i, j).
    The brighter of the two drives the threshold — same formula as before.
    Returns (n, n) symmetric matrix in degrees.
    """
    # brightest of each pair: min(mags[i], mags[j])
    m_i = mags[:, np.newaxis]                    # (n, 1)
    m_j = mags[np.newaxis, :]                    # (1, n)
    brightest = np.minimum(m_i, m_j)            # (n, n)

    # Two regimes, vectorized
    bright_mask = brightest < _BRIGHT_ANCHOR_MAG
    radius = np.where(
        bright_mask,
        _BASE_RADIUS_DEG + (_BRIGHT_ANCHOR_MAG - brightest) * 3.0,
        np.maximum(0.5, _BASE_RADIUS_DEG - (brightest - _BRIGHT_ANCHOR_MAG) * 0.4),
    )
    return radius                                # (n, n)


# ---------------------------------------------------------------------------
# Cluster centre & span (numpy)
# ---------------------------------------------------------------------------

def _cluster_center_xyz(xyz_subset: np.ndarray) -> Tuple[float, float]:
    """Mean direction of a set of stars. Returns (az_deg, alt_deg)."""
    mean = xyz_subset.sum(axis=0)                # (3,)
    norm = np.linalg.norm(mean)
    if norm < 1e-9:
        return 0.0, 0.0
    mean /= norm
    alt, az = _xyz_to_altaz(*mean)
    return az, alt


def _gnomonic_span(stars: List[StarResult],
                   center_az: float, center_alt: float) -> Tuple[float, float]:
    """
    Project all stars onto the tangent plane at (center_az, center_alt) using
    gnomonic projection, then return (width_deg, height_deg).
    Uses numpy for the projection dot products.
    """
    if len(stars) < 2:
        return 0.0, 0.0

    cx, cy, cz = _star_to_xyz(center_az, center_alt)
    c = np.array([cx, cy, cz])

    # Tangent-plane axes
    if abs(center_alt) > 89.5:
        east_hat  = np.array([1.0, 0.0, 0.0])
        north_hat = np.array([0.0, 1.0, 0.0])
    else:
        az_r = math.radians(center_az)
        east = np.array([-math.sin(az_r), math.cos(az_r), 0.0])
        east_hat = east / np.linalg.norm(east)

        north = np.cross(east_hat, c)
        nn = np.linalg.norm(north)
        if nn < 1e-9:
            return 0.0, 0.0
        north_hat = north / nn

    # Vectorized projection for all stars at once
    azimuths  = np.array([s.azimuth  for s in stars])
    altitudes = np.array([s.altitude for s in stars])
    xyz = _stars_to_xyz_array(azimuths, altitudes)   # (n, 3)

    denom = xyz @ c                                   # (n,)  dot with centre
    valid = denom > 1e-6
    if not valid.any():
        return 0.0, 0.0

    xyz_v = xyz[valid]
    denom_v = denom[valid, np.newaxis]

    px = np.degrees(np.arctan((xyz_v @ east_hat)  / denom_v.ravel()))
    py = np.degrees(np.arctan((xyz_v @ north_hat) / denom_v.ravel()))

    return float(px.max() - px.min()), float(py.max() - py.min())


# ---------------------------------------------------------------------------
# Cluster centre helper for merge pass
# ---------------------------------------------------------------------------

def _cluster_center(stars: List[StarResult]) -> Tuple[float, float]:
    """Mean direction via 3D vector average. Returns (az, alt)."""
    x = y = z = 0.0
    for s in stars:
        xi, yi, zi = _star_to_xyz(s.azimuth, s.altitude)
        x += xi; y += yi; z += zi
    alt, az = _xyz_to_altaz(x, y, z)
    return az, alt


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def fold_stars(stars: List[StarResult],
               max_leads: int = 3) -> Tuple[List[StarCluster], List[StarResult]]:
    """
    Group visible stars into perceptual clusters.

    Returns (clusters, lonely_stars) both sorted brightest-first.

    Performance path:
      - Stage 1 builds the full pairwise adjacency in one numpy broadcast.
      - Stages 2-3 still use Python loops over *components* (≪ n), which is
        fast enough since the merge pass works on O(k²) cluster pairs, not
        O(n²) star pairs.
    """
    n = len(stars)
    if n == 0:
        return [], []

    # ------------------------------------------------------------------
    # Pre-compute numpy arrays once — reused in Stage 1 and gnomonic spans
    # ------------------------------------------------------------------
    azimuths  = np.array([s.azimuth  for s in stars], dtype=np.float64)
    altitudes = np.array([s.altitude for s in stars], dtype=np.float64)
    mags      = np.array([s.magnitude for s in stars], dtype=np.float64)
    xyz       = _stars_to_xyz_array(azimuths, altitudes)   # (n, 3)

    # ------------------------------------------------------------------
    # Stage 1: vectorized proximity graph → connected components
    # ------------------------------------------------------------------
    dist_matrix   = _pairwise_angular_distance(xyz)        # (n, n) degrees
    radius_matrix = _connection_radius_matrix(mags)        # (n, n) degrees

    # Adjacency: connected if distance ≤ threshold (and not self)
    connected = (dist_matrix <= radius_matrix) & ~np.eye(n, dtype=bool)

    # Union-Find for connected components (faster than BFS for dense graphs)
    parent = np.arange(n)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]   # path compression
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    rows, cols = np.where(connected)
    for i, j in zip(rows.tolist(), cols.tolist()):
        union(i, j)

    # Group stars by root
    from collections import defaultdict
    root_to_indices: dict = defaultdict(list)
    for i in range(n):
        root_to_indices[find(i)].append(i)

    components: List[List[StarResult]] = [
        [stars[i] for i in idx] for idx in root_to_indices.values()
    ]

    # ------------------------------------------------------------------
    # Stage 2: merge pass (operates on components, not individual stars)
    # ------------------------------------------------------------------
    def _comp_brightest(comp: List[StarResult]) -> float:
        return min(s.magnitude for s in comp)

    changed = True
    while changed:
        changed = False
        used    = [False] * len(components)
        new_comps: List[List[StarResult]] = []

        for i in range(len(components)):
            if used[i]:
                continue
            base = components[i]

            for j in range(i + 1, len(components)):
                if used[j]:
                    continue
                other = components[j]

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
        comp.sort(key=lambda s: s.magnitude)

        if len(comp) == 1:
            lonely.append(comp[0])
            continue

        az_c, alt_c   = _cluster_center(comp)
        width, height = _gnomonic_span(comp, az_c, alt_c)
        num_leads     = min(max_leads, len(comp))

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