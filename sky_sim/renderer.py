"""
sky_sim/renderer.py
-------------------
Converts a SkySnapshot into a human-readable string.
Updated to work with the new visibility properties and SunResult structure.
"""

from __future__ import annotations
from collections import Counter

from typing import List
from enum import Enum
import re



from .types import (SkySnapshot, 
                    WeatherSnapshot, SkyConditionNarrative,
                    VisibilityState, AtmosphereScores, BortleClass,
                    MoonResult, SunResult, TwilightPhase, 
                    EclipseResult, EclipsePhase, EclipseType,
                    PlanetResult, 
                    StarResult, StarCluster

                    )
from .clustering import fold_stars


# ---------------------------------------------------------------------------
# Formatting Helpers
# ---------------------------------------------------------------------------

_CARDINAL = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

class StarLevel(str, Enum):
    FULL = "Full"
    COMPACT = "Compact"
# Formatting

def _format_pct(val: float, precision: int = 0) -> str:
    """Converts a 0-1 float to a percentage string."""
    return f"{val:.{precision}%}"

def _humanize(text: str) -> str:
    """Converts snake_case or CamelCase into 'Title Case Text'."""
    # Split camelCase and replace underscores with spaces
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', text)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)
    return s2.replace('_', ' ').title().strip()

def _cardinal(deg: float) -> str:
    """Converts degrees to a 16-point cardinal direction string."""
    idx = round(deg / 22.5) % 16
    return _CARDINAL[idx]

def _quality_bar(score: float, width: int = 10) -> str:
    """Returns a visual progress bar █ for values 0.0-1.0."""
    filled = max(0, min(width, round(score * width)))
    return "█" * filled + "░" * (width - filled)

def _format_pos(az: float, alt: float) -> str:
    """Standard format for Azimuth and Altitude."""
    return f"{_cardinal(az)} (az {az:.0f}°, alt {alt:.0f}°)"

def _format_shorthand(az: float, alt: float) -> str:
    return  f"({_cardinal(az)} {alt:.0f}°)"

# Rendering

def _star_vis(obj: StarResult, level: StarLevel) -> str:

    if obj.visibility == VisibilityState.VISIBLE:
        if level == StarLevel.FULL:
            return f"Pos: {_format_pos(obj.azimuth,obj.altitude)}, Mag: {obj.magnitude}"
        else:
            return f"Pos: {_format_shorthand(obj.azimuth, obj.altitude)}, Mag: {obj.magnitude}"


def _obj_vis(obj: PlanetResult | MoonResult | SunResult) -> str:
    strings = []

    if obj.visibility == VisibilityState.CLOUDED:
        strings.append(f"   - Clouded")
        strings.append(f"   - Position: {_format_shorthand(obj.azimuth, obj.altitude)}")

    elif obj.visibility == VisibilityState.VISIBLE:
        strings.append(f"   - Visible")
        strings.append(f"   - Effective Magnitude: {obj.effective_magnitude:.2f}.")
        strings.append(f"   - Position: {_format_pos(obj.azimuth,obj.altitude)}")

    strings.append(f"   - Cloud Occlusion: {_format_pct(obj.cloud_opacity)}")

    return '\n'.join(strings)

def _render_atmosphere(snap: SkySnapshot) -> str:
    atmos : AtmosphereScores = snap.atmosphere
    wx : WeatherSnapshot = snap.weather

    strings = []
    strings.append(f"Atmosphere Quality: {_format_pct(atmos.overall_quality)}")
    strings.append(f"Local cloud coverage: {_format_pct(snap.cloud_coverage_simulated)}")
    strings.append(f"Cloud Layers\n     - Low {wx.cloud_cover_low:.0f}% | Mid {wx.cloud_cover_mid:.0f}% | High {wx.cloud_cover_high:.0f}%")
    return '\n'.join(strings)

def _render_snm(snap: SkySnapshot) -> str:
    s = snap.sun
    m = snap.moon
    strings = []

    # Sun display
    if s.above_horizon:
        strings.append(f"The sun is {_obj_vis(s)}")

        if s.visibility == VisibilityState.VISIBLE:
            strings.append(f"Twilight Phase: {_humanize(s.twilight_phase)}")

    # Moon display
    if m.above_horizon:
        strings.append(f"The moon is {_obj_vis(m)}")

        if m.visibility == VisibilityState.VISIBLE:
            trend = "Waxing" if m.waxing else "Waning"
            strings.append(f"Moon Phase Trend: {trend}")
            strings.append(f"Moon current illumination: {_format_pct(m.illumination)}")
            if m.magnitude_impact > 0.5:
                strings.append(f"  ⚠ Lunar Glow  +{m.magnitude_impact:.1f} mag wash-out")
    return '\n'.join(strings)

def _render_eclipse(snap: SkySnapshot) -> str:
    eclipse : EclipseResult = snap.eclipse
    strings = []
    if not eclipse.eclipse_type == EclipseType.NONE and eclipse.visible_from_here == True:
        strings.append(f"Eclipse event!")
        strings.append(f"Eclipse info: {eclipse.note}\nObscuration: {eclipse.obscuration}")

    return '\n'.join(strings)


def _render_planets(snap: SkySnapshot) -> str:
    strings = []
    planets = snap.planets
    
    is_any_visible = any(p.visibility == VisibilityState.VISIBLE for p in planets)
    
    if is_any_visible:
        strings.append("Visible Planets:")
        
        for p in planets:
            if p.visibility == VisibilityState.VISIBLE:
                strings.append(f"{_humanize(p.name)} is visible!")
                strings.append(f"{_obj_vis(p)}")

    return '\n'.join(strings)

def _render_lonely(lonely_stars: List[StarResult]) -> str:
    strings = []

    is_any_visible = any(s.visibility == VisibilityState.VISIBLE for s in lonely_stars)
    
    if is_any_visible:
        strings.append("Lonely Stars Visible:")
        for s in lonely_stars:
            if s.visibility == VisibilityState.VISIBLE:
                strings.append(f"{s.name} {_star_vis(s, StarLevel.FULL)}")

    return '\n'.join(strings)

def _render_cluster(star_cluster: StarCluster) -> str:
    strings = []

    leads : List[StarResult] = star_cluster.leads
    followers : List[StarResult] = star_cluster.stars

    bag = leads + followers

    is_any_visible = any(s.visibility == VisibilityState.VISIBLE for s in bag)

    if is_any_visible:
        strings.append(f"Cluster | Total Stars: {star_cluster.total_count} | Center: {_format_shorthand(star_cluster.center_az, star_cluster.center_alt)} | Span: {star_cluster.width:.1f}°W × {star_cluster.height:.1f}°H")

        if leads:
            strings.append(f"Cluster Star Leads:")
            for l in leads:
                strings.append(f"   {l.name} {_star_vis(l, StarLevel.FULL)}")

        if followers:
            strings.append(f"Cluster Followers:")
            LIMIT = 5
            for f in followers[:LIMIT]:
                strings.append(f"   {f.name}, {_star_vis(f, StarLevel.COMPACT)}")
            if len(followers) > LIMIT:
                strings.append(f"   ... and {len(followers) - LIMIT} more followers.")

    return '\n'.join(strings)
    
    
def _render_stars(snap: SkySnapshot) -> str:
    total_visible = snap.total_stars_visible
    visible_stars = snap.stars_visible

    strings = []

    if visible_stars:
        strings.append(f"Total Visible Stars: {total_visible}")
        clusters, lonely = fold_stars(visible_stars)

        if clusters:
            for c in clusters:
                strings.append(_render_cluster(c))
        if lonely:
            strings.append(_render_lonely(lonely))

    return '\n'.join(strings)

# ---------------------------------------------------------------------------
# Main Render Function
# ---------------------------------------------------------------------------


def render_snapshot(snap: SkySnapshot, compact: bool = False) -> str:
    """The high-level orchestrator."""
    sections = [
        _render_atmosphere(snap),
        "",
        _render_snm(snap),
        "",
        _render_eclipse(snap),
        f"Final Effective MAG: {snap.limiting_magnitude:.2f} limit",
        _render_planets(snap),
        "",
        _render_stars(snap)
    ]
    
    # Filter out empty strings if a section (like Eclipse) returns nothing
    return "\n".join([s for s in sections if s.strip()])
