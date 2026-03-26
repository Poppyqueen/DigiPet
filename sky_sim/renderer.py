"""
sky_sim/renderer.py
-------------------
Converts a SkySnapshot into a human-readable string.
Updated to work with the new visibility properties and SunResult structure.
"""

from __future__ import annotations
from collections import Counter
from .types import SkySnapshot, SkyConditionNarrative, BortleClass, TwilightPhase, VisibilityState
from .clustering import fold_stars


# ---------------------------------------------------------------------------
# Formatting Helpers
# ---------------------------------------------------------------------------

_CARDINAL = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

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


# ---------------------------------------------------------------------------
# Main Render Function
# ---------------------------------------------------------------------------

def render_snapshot(snap: SkySnapshot, compact: bool = False) -> str:
    lines = []
    w = lines.append   # Shorthand helper

    # --- HEADER ---
    w("=" * 65)
    w(f"  NIGHT SKY  |  {snap.latitude:.4f}°, {snap.longitude:.4f}° ({snap.timezone})")
    w(f"  {snap.local_time}")
    w("=" * 65)

    # --- CONDITIONS ---
    w("")
    w("CONDITIONS")
    # condition is now a SkyConditionNarrative Enum
    status_text = snap.condition.value.replace('_', ' ').title()
    w(f"  Status:       {status_text}")
    w(f"  Bortle Class: {snap.bortle_class.value} ({snap.bortle_class.name.replace('_', ' ').title()})")
    w(f"  Limit Mag:    {snap.limiting_magnitude:.2f}  (Sky Coverage: {snap.cloud_coverage_simulated * 100:.0f}%)")
    w("")

    # --- ATMOSPHERE QUALITY ---
    atm = snap.atmosphere
    w("ATMOSPHERE QUALITY")
    w(f"  Transparency  {_quality_bar(atm.transparency)}  {atm.transparency:.2f}")
    w(f"  Seeing        {_quality_bar(atm.seeing)}  {atm.seeing:.2f}")
    w(f"  Fog Risk      {_quality_bar(atm.fog_risk)}  {atm.fog_risk:.2f}  "
      f"{'⚠ DEW/FOG FORMING' if atm.fog_risk > 0.6 else ''}")
    
    # Sun Status (using explicit SunResult)
    sun = snap.sun
    sun_phase = sun.twilight_phase.value.replace('_', ' ').title()
    w(f"  Sun Altitude  {sun.altitude:+.1f}° ({sun_phase})")
    if sun.magnitude_impact > 0.1:
        w(f"  ⚠ Sky Glow    +{sun.magnitude_impact:.1f} mag loss from sunlight")
    
    w(f"  Overall       {_quality_bar(atm.overall_quality)}  {atm.overall_quality:.2f}")
    w("")

    # --- WEATHER SUMMARY ---
    wx = snap.weather
    w("WEATHER")
    w(f"  Cloud Layers  Low {wx.cloud_cover_low:.0f}% | Mid {wx.cloud_cover_mid:.0f}% | High {wx.cloud_cover_high:.0f}%")
    w(f"  Visibility    {wx.visibility_m / 1000:.1f} km")
    w(f"  Humidity      {wx.humidity:.0f}% (Dew Point Spread: {wx.dew_point_spread:.1f}°C)")
    w(f"  Wind (low)    {wx.wind_speed_10m:.0f} km/h {_cardinal(wx.wind_direction_10m)}")
    
    stability = 'Stable' if wx.cape < 300 else 'Unstable' if wx.cape < 1000 else 'Very Unstable'
    w(f"  Air Mass      {wx.cape:.0f} J/kg CAPE ({stability})")
    w("")

    # --- MOON ---
    moon = snap.moon
    moon_vis = "ABOVE HORIZON" if moon.above_horizon else "BELOW HORIZON"
    w(f"MOON {moon_vis}")
    
    trend = "Waxing" if moon.waxing else "Waning"
    w(f"  {trend} Phase — {moon.illumination * 100:.1f}% illuminated")
    
    if moon.above_horizon:
        w(f"  Position:     {_format_pos(moon.azimuth, moon.altitude)}")
        if moon.magnitude_impact > 0.5:
            w(f"  ⚠ Lunar Glow  +{moon.magnitude_impact:.1f} mag wash-out")
    w("")

# --- PLANETS ---
    if snap.planets:
        print(f"RENDERER DEBUG RAW PLANETS:\n {snap.planets}")
        w("PLANETS")
        for p in snap.planets:
            # Determine primary status string
            status = "VISIBLE" if p.visibility == VisibilityState.VISIBLE else "OBSCURED"
            
            # Identify the reason for obscuration via flags
            flag = ""
            if p.visibility == VisibilityState.CLOUDED:
                # Optional: Show opacity % if you want more detail in the text
                flag = f"[CLOUDED {p.cloud_opacity*100:.0f}%]"
            elif p.visibility == VisibilityState.BELOW_LIMIT:
                flag = f"[TOO FAINT (eff: {p.effective_magnitude:+.1f})]"

            # Standardized line format
            w(f"  {p.name:<10} mag {p.magnitude:+.1f}  "
              f"{_format_pos(p.azimuth, p.altitude)}  {status} {flag}")
        w("")

    # --- STARS VISIBLE ---
    # Using the new snap.total_stars_visible property
    w(f"STARS VISIBLE ({snap.total_stars_visible} of {snap.stars_above_horizon} above horizon)")
    
    # Using the new snap.stars_visible property
    visible_list = snap.stars_visible
    if visible_list:
        clusters, lonely = fold_stars(visible_list)

        if clusters:
            w("  STAR GROUPS & FORMATIONS")
            for c in clusters:
                lead_names = [s.name or "Unnamed" for s in c.leads]
                if len(lead_names) > 1:
                    names_str = ", ".join(lead_names[:-1]) + f", & {lead_names[-1]}"
                else:
                    names_str = lead_names[0]

                followers = c.stars[len(c.leads):]
                follower_text = ""
                if followers:
                    min_mag = min(s.magnitude for s in followers)
                    max_mag = max(s.magnitude for s in followers)
                    follower_text = f" (+{len(followers)} others, mag {min_mag:.1f} to {max_mag:.1f})"

                # Detect dominant constellation in group
                consts = [s.constellation for s in c.stars if s.constellation and str(s.constellation).lower() != 'nan']
                const_tag = ""
                if consts:
                    top_const, count = Counter(consts).most_common(1)[0]
                    const_tag = f" [{top_const}]"
                
                w(f"    • {names_str}{follower_text}{const_tag}")
                w(f"      Center: {_format_pos(c.center_az, c.center_alt)} | Span: {c.width:.1f}°W × {c.height:.1f}°H")

        if lonely:
            w("\n  ISOLATED BRIGHT POINTS")
            # Show top brightest lonely stars
            for s in sorted(lonely, key=lambda x: x.magnitude)[:8]:
                w(f"    • {s.name or 'Star'} — {s.magnitude:+.2f} mag in the {_cardinal(s.azimuth)}")
    else:
        # Narrative context for why nothing is visible
        if snap.sun.above_horizon:
            w("  None — Sunlight prevents naked-eye star visibility.")
        elif snap.weather.cloud_cover_total > 95:
            w("  None — Heavy cloud cover obscuring all stars.")
        else:
            w("  None — Local light pollution or twilight preventing visibility.")
    w("")

    # --- OBSCURATION INFO ---
    if not compact:
        clouded = snap.stars_clouded
        if clouded:
            w(f"OBSCURED BY CLOUDS ({len(clouded)})")
            # Show top 5 brightest stars currently blocked
            for s in sorted(clouded, key=lambda x: x.magnitude)[:5]:
                w(f"  [!] {s.name:<14} mag {s.magnitude:+.2f} ({_cardinal(s.azimuth)})")
            w("")
        
        below_lim = snap.stars_below_limit
        if below_lim:
            w(f"BELOW VISIBILITY LIMIT ({len(below_lim)})")
            w(f"  Fainter than {snap.limiting_magnitude:.2f} mag due to conditions.")
            w("")

    # --- FOOTER ---
    w(f"  Sim Tick: #{snap.simulation_tick}")
    w("=" * 65)

    return "\n".join(lines)