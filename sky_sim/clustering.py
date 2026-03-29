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

Changes from previous version:
  - Fix: StarCluster.stars now holds only the follower stars (comp[num_leads:]),
    so leads and followers are disjoint. Previously leads were a subset of stars,
    causing every lead to appear twice in renders.
  - Fix: MERGE_RADIUS_DEG is now computed adaptively from star density, so a
    rich Bortle-1 sky (500+ visible stars) collapses into a small number of
    grand regions rather than 20+ small clusters.
  - New: minimum cluster size gate — tiny components with no anchor are demoted
    to lonely stars after the merge pass.
  - New: forced-merge cap — after all adaptive merging, if the cluster count
    still exceeds max_clusters the two closest-center clusters are merged
    repeatedly until the cap is satisfied.
  - New: fold_stars() accepts a max_clusters parameter (default 8) exposed all
    the way up to the renderer.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from .types import StarResult, StarCluster

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

_BASE_RADIUS_DEG: float    = 2.0
_BRIGHT_ANCHOR_MAG: float  = 1.5
_LONE_ANCHOR_MAG: float    = -0.5

# Adaptive merge radius: linearly interpolated between these two anchor points.
#   ≤ _DENSITY_LOW stars  → _MERGE_RADIUS_SPARSE
#   ≥ _DENSITY_HIGH stars → _MERGE_RADIUS_DENSE
_DENSITY_LOW: int         = 50
_DENSITY_HIGH: int        = 400
_MERGE_RADIUS_SPARSE: float = 18.0   # degrees — matches previous fixed value
_MERGE_RADIUS_DENSE: float  = 42.0   # degrees — large enough to fold a rich Bortle-1 sky

# A component is only kept as a cluster if it has at least this many members
# OR contains a star bright enough to anchor it relative to the sky.
# The anchor threshold is computed dynamically — see _anchor_mag_threshold().
_MIN_CLUSTER_SIZE: int       = 4


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
    dots = np.clip(xyz @ xyz.T, -1.0, 1.0)
    return np.degrees(np.arccos(dots))           # (n, n), symmetric, zero diagonal


def _connection_radius_matrix(mags: np.ndarray) -> np.ndarray:
    """
    Vectorized connection radii for every pair (i, j).
    The brighter of the two drives the threshold.
    Returns (n, n) symmetric matrix in degrees.
    """
    m_i = mags[:, np.newaxis]                    # (n, 1)
    m_j = mags[np.newaxis, :]                    # (1, n)
    brightest = np.minimum(m_i, m_j)            # (n, n)

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
    """
    if len(stars) < 2:
        return 0.0, 0.0

    cx, cy, cz = _star_to_xyz(center_az, center_alt)
    c = np.array([cx, cy, cz])

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

    azimuths  = np.array([s.azimuth  for s in stars])
    altitudes = np.array([s.altitude for s in stars])
    xyz = _stars_to_xyz_array(azimuths, altitudes)   # (n, 3)

    denom = xyz @ c                                   # (n,)
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
# Adaptive merge radius
# ---------------------------------------------------------------------------

def _adaptive_merge_radius(n_stars: int) -> float:
    """
    Return a merge radius (degrees) scaled to the number of visible stars.

    The intuition: in a dense sky the proximity graph produces many small
    components that a human eye would perceive as one large region.  A larger
    merge radius collapses these into a small number of grand clusters.

    The function is a simple linear ramp clamped at the two anchor points:
      n ≤ _DENSITY_LOW  → _MERGE_RADIUS_SPARSE (18°)
      n ≥ _DENSITY_HIGH → _MERGE_RADIUS_DENSE  (42°)
    """
    if n_stars <= _DENSITY_LOW:
        return _MERGE_RADIUS_SPARSE
    if n_stars >= _DENSITY_HIGH:
        return _MERGE_RADIUS_DENSE
    t = (n_stars - _DENSITY_LOW) / (_DENSITY_HIGH - _DENSITY_LOW)
    return _MERGE_RADIUS_SPARSE + t * (_MERGE_RADIUS_DENSE - _MERGE_RADIUS_SPARSE)


# ---------------------------------------------------------------------------
# Adaptive anchor magnitude threshold
# ---------------------------------------------------------------------------

def _anchor_mag_threshold(stars: List[StarResult]) -> float:
    """
    Return the magnitude threshold below which a single bright star is
    considered enough to anchor a small (< _MIN_CLUSTER_SIZE) component.

    The key insight: in a rich Bortle-1 sky with 500+ visible stars, mag 4
    is unremarkable — a random pair of mag-4 stars near each other isn't a
    meaningful cluster.  In a Bortle-3 moon-washed sky with 40 visible stars,
    mag 2.5 IS remarkable — Castor and Pollux at the zenith absolutely deserve
    to be called a cluster.

    We set the threshold at the 30th percentile of the visible star magnitudes.
    This means: a small component is anchored if its brightest star is in the
    top 30% of tonight's visible stars.  The threshold naturally tightens in
    rich skies (where the 30th-pct is dim) and relaxes in sparse skies (where
    even the 30th-pct is a first-magnitude star).

    An absolute floor of mag 1.5 is applied so that even in the densest sky a
    genuinely prominent pair (e.g. Castor + Pollux) is never discarded.
    """
    if not stars:
        return 1.5
    mags = sorted(s.magnitude for s in stars)
    idx  = max(0, int(len(mags) * 0.30) - 1)
    return max(1.5, mags[idx])

def fold_stars(stars: List[StarResult],
               max_leads: int = 3,
               max_clusters: int = 8) -> Tuple[List[StarCluster], List[StarResult]]:
    """
    Group visible stars into perceptual clusters.

    Returns (clusters, lonely_stars) both sorted brightest-first.

    Parameters
    ----------
    stars        : visible StarResult objects (above horizon, visibility == VISIBLE)
    max_leads    : brightest stars shown individually per cluster (default 3)
    max_clusters : hard cap on the number of clusters returned.  After adaptive
                   merging, any excess clusters are force-merged into their nearest
                   neighbour until the count is ≤ max_clusters (default 8).

    Pipeline
    --------
    Stage 1  — vectorized proximity graph → Union-Find components
    Stage 2  — adaptive merge pass (merge radius scales with star density)
    Stage 2b — minimum-size gate (demote tiny, dim components to lonely)
    Stage 2c — forced-merge cap (collapse closest-pair until ≤ max_clusters)
    Stage 3  — build StarCluster output objects
    """
    n = len(stars)
    if n == 0:
        return [], []

    # ------------------------------------------------------------------
    # Pre-compute numpy arrays once
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

    connected = (dist_matrix <= radius_matrix) & ~np.eye(n, dtype=bool)

    parent = np.arange(n)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    rows, cols = np.where(connected)
    for i, j in zip(rows.tolist(), cols.tolist()):
        union(i, j)

    from collections import defaultdict
    root_to_indices: dict = defaultdict(list)
    for i in range(n):
        root_to_indices[find(i)].append(i)

    components: List[List[StarResult]] = [
        [stars[i] for i in idx] for idx in root_to_indices.values()
    ]

    # ------------------------------------------------------------------
    # Stage 2: adaptive merge pass
    # ------------------------------------------------------------------
    merge_radius = _adaptive_merge_radius(n)

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
                if angular_distance(az_b, alt_b, az_o, alt_o) <= merge_radius:
                    base    = base + other
                    used[j] = True
                    changed = True

            new_comps.append(base)

        components = new_comps

    # ------------------------------------------------------------------
    # Stage 2b: minimum-size gate
    # Demote components that are too small and too dim to deserve a cluster
    # entry.  The anchor threshold is computed relative to tonight's visible
    # stars so the gate tightens in rich skies and relaxes in sparse ones.
    #
    # A component is kept if ANY of these hold:
    #   (a) It has enough members to be meaningful (_MIN_CLUSTER_SIZE).
    #   (b) Its brightest star is in the top 30% of tonight's sky — i.e. it
    #       is a genuinely prominent pair or triplet (Castor+Pollux, the
    #       Gemini twins, the Pointers, etc.).
    #
    # Note: we deliberately do NOT require has_followers (len > max_leads).
    # A 2-star cluster with both stars as leads is still a valid cluster —
    # the renderer already handles the zero-follower case gracefully.
    # ------------------------------------------------------------------
    anchor_thresh = _anchor_mag_threshold(stars)

    kept:    List[List[StarResult]] = []
    demoted: List[StarResult]       = []

    for comp in components:
        brightest       = _comp_brightest(comp)
        has_enough_size = len(comp) >= _MIN_CLUSTER_SIZE
        has_anchor      = brightest <= anchor_thresh
        if has_enough_size or has_anchor:
            kept.append(comp)
        else:
            demoted.extend(comp)

    components = kept

    # ------------------------------------------------------------------
    # Stage 2c: forced-merge cap
    # If we still have more clusters than max_clusters, repeatedly merge
    # the pair of clusters whose centres are closest until we hit the cap.
    # ------------------------------------------------------------------
    while len(components) > max_clusters:
        # Find the closest pair of cluster centres
        centers = [_cluster_center(c) for c in components]
        best_dist  = math.inf
        best_i = 0
        best_j = 1

        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                az_i, alt_i = centers[i]
                az_j, alt_j = centers[j]
                d = angular_distance(az_i, alt_i, az_j, alt_j)
                if d < best_dist:
                    best_dist = d
                    best_i, best_j = i, j

        # Merge j into i (remove j, expand i)
        merged = components[best_i] + components[best_j]
        components = [c for k, c in enumerate(components) if k != best_i and k != best_j]
        components.append(merged)

    # ------------------------------------------------------------------
    # Stage 3: build output objects
    # ------------------------------------------------------------------
    clusters: List[StarCluster] = []
    lonely:   List[StarResult]  = list(demoted)   # start with demoted stars

    for comp in components:
        comp.sort(key=lambda s: s.magnitude)

        if len(comp) == 1:
            lonely.append(comp[0])
            continue

        az_c, alt_c   = _cluster_center(comp)
        width, height = _gnomonic_span(comp, az_c, alt_c)
        num_leads     = min(max_leads, len(comp))
        leads         = comp[:num_leads]
        followers     = comp[num_leads:]          # disjoint from leads — FIX

        clusters.append(StarCluster(
            stars=followers,
            leads=leads,
            center_az=az_c,
            center_alt=alt_c,
            width=width,
            height=height,
        ))

    clusters.sort(key=lambda c: c.brightest_magnitude)
    lonely.sort(key=lambda s: s.magnitude)

    return clusters, lonely