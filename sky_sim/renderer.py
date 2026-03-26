"""
sky_sim/renderer.py
-------------------
Converts a SkySnapshot into a human-readable string.
This is the "output string" layer — kept separate so you can
swap it for JSON, markdown, or any other format.
"""

from __future__ import annotations
from .types import SkySnapshot, SkyConditionNarrative, BortleClass

from .clustering import fold_stars
from collections import Counter


# ---------------------------------------------------------------------------
# Condition descriptions
# ---------------------------------------------------------------------------

_CONDITION_TEXT = {
    SkyConditionNarrative.CLEAR:         "Clear sky",
    SkyConditionNarrative.MOSTLY_CLEAR:  "Mostly clear",
    SkyConditionNarrative.PARTLY_CLOUDY: "Partly cloudy",
    SkyConditionNarrative.MOSTLY_CLOUDY: "Mostly cloudy",
    SkyConditionNarrative.OVERCAST:      "Overcast",
    SkyConditionNarrative.FOG:           "Fog",
    SkyConditionNarrative.PRECIPITATION: "Precipitation",
    SkyConditionNarrative.THUNDERSTORM:  "Thunderstorm",
}

_BORTLE_TEXT = {
    BortleClass.PRISTINE:          "Bortle 1 — pristine dark sky",
    BortleClass.TRULY_DARK:        "Bortle 2 — truly dark sky",
    BortleClass.RURAL:             "Bortle 3 — rural sky",
    BortleClass.RURAL_SUBURBAN:    "Bortle 4 — rural/suburban transition",
    BortleClass.SUBURBAN:          "Bortle 5 — suburban sky",
    BortleClass.BRIGHT_SUBURBAN:   "Bortle 6 — bright suburban sky",
    BortleClass.SUBURBAN_URBAN:    "Bortle 7 — suburban/urban transition",
    BortleClass.CITY:              "Bortle 8 — city sky",
    BortleClass.INNER_CITY:        "Bortle 9 — inner city sky",
}

_CARDINAL = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def _cardinal(deg: float) -> str:
    idx = round(deg / 22.5) % 16
    return _CARDINAL[idx]


def _quality_bar(score: float, width: int = 10) -> str:
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def _format_az_alt(az: float, alt: float) -> str:
    return f"{_cardinal(az)} (az {az:.0f}°, alt {alt:.0f}°)"



def _get_direction(az):
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    return directions[int((az + 11.25) / 22.5) % 16]
# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_snapshot(snap: SkySnapshot, compact: bool = False) -> str:
    lines = []
    w = lines.append   # shorthand

    # Header
    w("=" * 60)
    w(f"  NIGHT SKY  |  {snap.latitude:.4f}°, {snap.longitude:.4f}°")
    w(f"  {snap.local_time}")
    w("=" * 60)

    # Conditions
    w("")
    w(f"CONDITIONS")
    w(f"  {_CONDITION_TEXT.get(snap.condition, snap.condition.value)}")
    w(f"  {_BORTLE_TEXT[snap.bortle_class]}")
    w(f"  Limiting magnitude: {snap.limiting_magnitude:.1f}  "
      f"(cloud cover sim: {snap.cloud_coverage_simulated * 100:.0f}%)")
    w("")

    # Atmosphere quality bars
    atm = snap.atmosphere
    w(f"ATMOSPHERE QUALITY")
    w(f"  Transparency  {_quality_bar(atm.transparency)}  {atm.transparency:.2f}")
    w(f"  Seeing        {_quality_bar(atm.seeing)}  {atm.seeing:.2f}")
    w(f"  Fog risk      {_quality_bar(atm.fog_risk)}  {atm.fog_risk:.2f}  "
      f"{'⚠ dew forming' if atm.fog_risk > 0.6 else ''}")
    w(f"  Overall       {_quality_bar(atm.overall_quality)}  {atm.overall_quality:.2f}")
    w("")

    # Weather summary
    wx = snap.weather
    w(f"WEATHER")
    w(f"  Cloud layers  low {wx.cloud_cover_low:.0f}%  "
      f"mid {wx.cloud_cover_mid:.0f}%  "
      f"high {wx.cloud_cover_high:.0f}%")
    w(f"  Visibility    {wx.visibility_m / 1000:.1f} km")
    w(f"  Humidity      {wx.humidity:.0f}%  "
      f"(dew point spread {wx.dew_point_spread:.1f}°C)")
    w(f"  Wind (low)    {wx.wind_speed_10m:.0f} km/h {_cardinal(wx.wind_direction_10m)}")
    w(f"  Wind (high)   {wx.wind_speed_120m:.0f} km/h")
    w(f"  CAPE          {wx.cape:.0f} J/kg  "
      f"{'stable' if wx.cape < 300 else 'unstable' if wx.cape < 1000 else 'very unstable'}")
    w("")

    # Moon
    moon = snap.moon
    moon_vis = "above horizon" if moon.above_horizon else "below horizon"
    w(f"MOON {moon_vis}")
    w(f"  {moon.phase_name.title()}  —  {moon.illumination * 100:.0f}% illuminated")
    if moon.above_horizon:
        w(f"  Position: {_format_az_alt(moon.azimuth, moon.altitude)}")
        if moon.illumination > 0.5:
            w(f"  ⚠ Bright moon washing out faint stars "
              f"(+{atm.moon_mag_loss:.1f} mag loss)")
    else:
        w(f"  Below horizon — no moonlight interference")
    w("")

    # Planets
    if snap.planets:
        w(f"PLANETS")
        for p in snap.planets:
            status = "VISIBLE" if p.visible else "obscured"
            flag   = " [cloud]" if p.obscured_by_cloud else ""
            if p.altitude >= 5:
                w(f"  {p.name:<10} mag {p.magnitude:+.1f}  "
                  f"{_format_az_alt(p.azimuth, p.altitude)}  {status}{flag}")
        w("")

    # Stars visible
    visible = snap.stars_visible
    w(f"STARS VISIBLE  ({len(visible)} of {len(visible) + len(snap.stars_obscured)} above horizon)")
    if visible:
        # Sort by magnitude (brightest first)
        # for s in sorted(visible, key=lambda x: x.magnitude):
        #     const = f"  [{s.constellation}]" if s.constellation else ""
        #     w(f"  {s.name:<16} mag {s.magnitude:+.2f}  "
        #       f"{_format_az_alt(s.azimuth, s.altitude)}{const}")

        clusters, lonely = fold_stars(snap.stars_visible)

        if clusters:
            lines.append("\n  STAR GROUPS & FORMATIONS")
            for c in clusters:
                # Format the Leads: "Sirius, Adhara, and Murzim"
                lead_names =[s.name or "Unnamed" for s in c.leads]
                if len(lead_names) > 1:
                    names_str = ", ".join(lead_names[:-1]) + f", & {lead_names[-1]}"
                else:
                    names_str = lead_names[0]

                # Intelligent follower summary (Magnitude ranges)
                followers = c.stars[len(c.leads):]
                if followers:
                    min_mag = min(s.magnitude for s in followers)
                    max_mag = max(s.magnitude for s in followers)
                    follower_text = f" (+ {len(followers)} others, mag {min_mag:.1f} to {max_mag:.1f})"
                else:
                    follower_text = ""

                # Try to deduce the Constellation identity # we don't want this
                consts =[s.constellation for s in c.stars if s.constellation and str(s.constellation).lower() != 'nan']
                if consts:
                    top_const, count = Counter(consts).most_common(1)[0]
                    # If 50%+ of the cluster belongs to one constellation, call it out
                    if count >= len(c.stars) * 0.5:
                        const_tag = f" [Mostly {top_const}]" if count < len(c.stars) else f" [{top_const}]"
                    else:
                        const_tag = ""
                else:
                    const_tag = ""
                
                # Output Assembly
                dir_label = _get_direction(c.center_az)
                lines.append(f"    • {names_str}{follower_text}{const_tag}")
                lines.append(f"      Center: {dir_label} (az {c.center_az:.0f}°, alt {c.center_alt:.0f}°)  |  Span: {c.width:.1f}° W × {c.height:.1f}° H")

        if lonely:
            lines.append("\n  LONELY STARS")
            for s in lonely[:10]:
                lines.append(f"    • {s.name or 'Star'} — {s.magnitude:+.2f} mag in the {_get_direction(s.azimuth)}")
            if len(lonely) > 10:
                lines.append(f"      ...and {len(lonely)-10} other isolated points.")
    else:
        w("  None — sky conditions prevent naked-eye star visibility")
    w("")

    if not compact and snap.stars_obscured: # stars obscured is wrong!
        obscured_by_cloud = [s for s in snap.stars_obscured if s.obscured_by_cloud]
        if obscured_by_cloud:
            w(f"OBSCURED BY CLOUD  ({len(obscured_by_cloud)})")
            for s in sorted(obscured_by_cloud, key=lambda x: x.magnitude)[:10]:
                w(f"  {s.name:<16} mag {s.magnitude:+.2f}  "
                  f"{_format_az_alt(s.azimuth, s.altitude)}")
            w("")

    # Tick info
    w(f"  sim tick #{snap.simulation_tick}")
    w("=" * 60)

    return "\n".join(lines)