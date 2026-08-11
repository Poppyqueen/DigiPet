"""
lunar_sim/renderer.py
-----------------------
Converts a LunarSnapshot into human-readable text. Pure functions only —
no randomness, no config, no state. Mirrors sky_sim/renderer.py's shape.
"""

from __future__ import annotations

from .types import LunarSnapshot, DomePhase, FlareIntensity

_CARDINAL = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def _cardinal(deg: float) -> str:
    idx = round(deg / 22.5) % 16
    return _CARDINAL[idx]


def _format_pos(az: float, alt: float) -> str:
    return f"{_cardinal(az)} (az {az:.0f}°, alt {alt:.0f}°)"


def _format_pct(val: float) -> str:
    return f"{val:.0%}"


def _humanize_phase(phase: DomePhase) -> str:
    return {
        DomePhase.LUNAR_DAY: "Lunar Day",
        DomePhase.LUNAR_NIGHT: "Lunar Night",
        DomePhase.TERMINATOR_RISING: "Sunrise Terminator",
        DomePhase.TERMINATOR_SETTING: "Sunset Terminator",
    }[phase]


# --- limited (ambient glance through the viewport) -----------------------

def render_limited(snap: LunarSnapshot) -> str:
    lines = []

    if snap.sun.phase == DomePhase.LUNAR_DAY:
        lines.append("Harsh, unfiltered sunlight floods the viewport — no atmosphere to soften it.")
    elif snap.sun.phase == DomePhase.LUNAR_NIGHT:
        lines.append("Beyond the glass, the surface lies in the flat black of lunar night.")
    else:
        lines.append("The terminator is crossing your sector — the line between blinding light and total dark, with no dusk in between.")

    if snap.earth.visible:
        lines.append("Earth hangs in its usual place in the sky, unmoving against the stars.")

    if snap.dome.viewport_haze > 0.6:
        lines.append("A film of fine regolith dust has crept over the outer pane, softening everything you can see.")

    if snap.space_weather.flare != FlareIntensity.NONE:
        lines.append("The dome's radiation warning strip along the viewport frame is glowing.")

    return "\n".join(lines)


# --- full (deliberate look) ----------------------------------------------

def _render_sun(snap: LunarSnapshot) -> str:
    s = snap.sun
    lines = [f"Solar Phase: {_humanize_phase(s.phase)}"]
    if s.above_horizon:
        lines.append(f"Sun Position: {_format_pos(s.azimuth, s.altitude)}")
        lines.append("No twilight, no dusk — the sun's disk sits at full, undimmed intensity the instant it clears the horizon.")
    else:
        lines.append(f"Sun below horizon (alt {s.altitude:.0f}°) — night here runs roughly 14 Earth-days.")
    return "\n".join(lines)


def _render_earth(snap: LunarSnapshot) -> str:
    e = snap.earth
    if not e.visible:
        return "Earth is not visible from this site — you are far enough onto the far side that it never crests the horizon."

    lines = [
        f"Earth Position: {_format_pos(e.azimuth, e.altitude)}",
        f"Earth Illumination: {_format_pct(e.illuminated_fraction)} lit",
        f"Libration Drift: {e.libration_lon_deg:+.1f}° lon / {e.libration_lat_deg:+.1f}° lat from mean center",
    ]
    if abs(e.libration_lon_deg) > 6.0 or abs(e.libration_lat_deg) > 6.0:
        lines.append("Earth is near the edge of its slow libration wobble — an extra sliver of far-side terrain has crept into view at the limb.")
    return "\n".join(lines)


def _render_space_weather(snap: LunarSnapshot) -> str:
    sw = snap.space_weather
    lines = [f"Ambient Radiation: {sw.radiation_dose_rate_uSv_h:.2f} µSv/h"]
    if sw.flare != FlareIntensity.NONE:
        lines.append(f"⚠ Solar Flare Event: {sw.flare.value.upper()} — est. {sw.flare_ticks_remaining} tick(s) remaining")
    return "\n".join(lines)


def _render_dome(snap: LunarSnapshot) -> str:
    d = snap.dome
    lines = [
        f"Viewport Haze: {_format_pct(d.viewport_haze)}",
        f"Hull Integrity: {_format_pct(d.structural_integrity)}",
    ]
    if d.micrometeorite_pings_today > 0:
        lines.append(f"Micrometeorite Pings Logged: {d.micrometeorite_pings_today} — faint ticks against the outer shell, felt more than heard.")
    return "\n".join(lines)


def _render_stars(snap: LunarSnapshot) -> str:
    if snap.stars_visible <= 0:
        return ""
    return (
        f"Stars Visible: {snap.stars_visible} — no atmosphere means no twinkle and no scatter; "
        f"they burn as hard, fixed points from horizon to horizon."
    )


def render_snapshot(snap: LunarSnapshot) -> str:
    sections = [
        _render_sun(snap),
        "",
        _render_earth(snap),
        "",
        _render_space_weather(snap),
        "",
        _render_dome(snap),
        "",
        _render_stars(snap),
    ]
    return "\n".join(s for s in sections if s.strip())