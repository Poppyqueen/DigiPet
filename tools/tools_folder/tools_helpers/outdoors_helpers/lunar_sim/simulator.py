"""
lunar_sim/simulator.py
------------------------
Owns all mutable state for a single dome's view. Mirrors NightSkySimulator's
role in the Earth astro provider: construct once, call .tick() on a cadence,
call .snapshot() to get an immutable read of current state for rendering.
"""

from __future__ import annotations
import random
from utils.loc_datetime import datetime

from .types import (
    LunarSnapshot, SunResult, EarthResult, SpaceWeather, DomeStatus,
    DomePhase, FlareIntensity, CycleState,
)
from . import ephemeris as eph
from .events import DecayCycle, HULL_EVENT_LABELS, VIEWPORT_EVENT_LABELS

# --- tunables -----------------------------------------------------------

_BASE_RADIATION_uSv_h = 0.6             # ambient lunar surface background (unshielded proxy)
_FLARE_RADIATION_MULT = {
    FlareIntensity.NONE: 1.0,
    FlareIntensity.MINOR: 3.0,
    FlareIntensity.MODERATE: 12.0,
    FlareIntensity.SEVERE: 40.0,
}
_FLARE_ROLL_CHANCE = 0.015              # per tick, chance a new flare starts
_FLARE_DURATION_TICKS = {
    FlareIntensity.MINOR: (2, 5),
    FlareIntensity.MODERATE: (1, 3),
    FlareIntensity.SEVERE: (1, 2),
}
_MICROMETEORITE_CHANCE = 0.08           # per tick, chance of at least one *cosmetic* ping (independent of hull events)
_STARS_VISIBLE_NIGHT = 2500             # no atmosphere, no scatter — a *lot* more than Earth
_TERMINATOR_BAND_DEG = 2.0              # sun altitude window counted as "terminator", not full day/night

# Hull: rarer, more severe, slower to fix.
_HULL_EVENT_CHANCE = 0.01
_HULL_SEVERITY_RANGE = (0.03, 0.10)
_HULL_REPAIR_TICKS_RANGE = (6, 14)

# Viewport haze: more frequent, milder, faster to clear.
_VIEWPORT_EVENT_CHANCE = 0.03
_VIEWPORT_SEVERITY_RANGE = (0.10, 0.30)
_VIEWPORT_REPAIR_TICKS_RANGE = (3, 8)


class LunarSkySimulator:
    def __init__(self, lat: float, lon: float, noise_seed: int):
        self.lat = float(lat)
        self.lon = float(lon)
        self.rng = random.Random(noise_seed)

        self.tick_count = 0
        self.micrometeorite_pings_today = 0

        self.hull_cycle = DecayCycle(
            rng=self.rng, event_chance=_HULL_EVENT_CHANCE,
            severity_range=_HULL_SEVERITY_RANGE,
            repair_ticks_range=_HULL_REPAIR_TICKS_RANGE,
            event_labels=HULL_EVENT_LABELS,
        )
        self.viewport_cycle = DecayCycle(
            rng=self.rng, event_chance=_VIEWPORT_EVENT_CHANCE,
            severity_range=_VIEWPORT_SEVERITY_RANGE,
            repair_ticks_range=_VIEWPORT_REPAIR_TICKS_RANGE,
            event_labels=VIEWPORT_EVENT_LABELS,
        )

        self.flare = FlareIntensity.NONE
        self.flare_ticks_remaining = 0

    # -- state advance -----------------------------------------------

    def tick(self) -> None:
        self.tick_count += 1

        self.hull_cycle.tick()
        self.viewport_cycle.tick()

        self._advance_flare()
        self._roll_micrometeorites()

    def _advance_flare(self) -> None:
        if self.flare != FlareIntensity.NONE:
            self.flare_ticks_remaining -= 1
            if self.flare_ticks_remaining <= 0:
                self.flare = FlareIntensity.NONE
            return

        if self.rng.random() < _FLARE_ROLL_CHANCE:
            roll = self.rng.random()
            if roll < 0.6:
                self.flare = FlareIntensity.MINOR
            elif roll < 0.9:
                self.flare = FlareIntensity.MODERATE
            else:
                self.flare = FlareIntensity.SEVERE
            lo, hi = _FLARE_DURATION_TICKS[self.flare]
            self.flare_ticks_remaining = self.rng.randint(lo, hi)

    def _roll_micrometeorites(self) -> None:
        """Cosmetic ping count for flavor text -- independent of whether a
        hull DecayCycle event actually fired this tick. A ping doesn't
        always mean damage; a hull event always implies at least one."""
        self.micrometeorite_pings_today = 0
        if self.hull_cycle.state == CycleState.EVENT:
            self.micrometeorite_pings_today = self.rng.randint(1, 3)
        elif self.rng.random() < _MICROMETEORITE_CHANCE:
            self.micrometeorite_pings_today = 1

    # -- read ----------------------------------------------------------

    def snapshot(self, dt: datetime | None = None) -> LunarSnapshot:
        dt = dt or datetime.now()

        sun_alt, sun_az = eph.sun_look_angle(self.lat, self.lon, dt)
        sun_phase = self._sun_phase(sun_alt)

        earth_alt, earth_az, earth_visible = eph.earth_look_angle(self.lat, self.lon, dt)
        lib_lon, lib_lat = eph.libration_offset(dt)
        earth_lit_fraction = eph.earth_illuminated_fraction(dt)

        stars = _STARS_VISIBLE_NIGHT if sun_alt < 0 else 0

        return LunarSnapshot(
            timestamp_tick=self.tick_count,
            sun=SunResult(
                altitude=sun_alt, azimuth=sun_az,
                above_horizon=sun_alt > 0, phase=sun_phase,
            ),
            earth=EarthResult(
                visible=earth_visible and earth_alt > 0,
                altitude=earth_alt, azimuth=earth_az,
                illuminated_fraction=earth_lit_fraction,
                libration_lon_deg=lib_lon, libration_lat_deg=lib_lat,
            ),
            space_weather=SpaceWeather(
                flare=self.flare,
                flare_ticks_remaining=self.flare_ticks_remaining,
                radiation_dose_rate_uSv_h=_BASE_RADIATION_uSv_h * _FLARE_RADIATION_MULT[self.flare],
            ),
            dome=DomeStatus(
                viewport_haze=1.0 - self.viewport_cycle.value,
                viewport_state=self.viewport_cycle.state,
                viewport_event_label=self.viewport_cycle.current_label,
                viewport_repair_eta_ticks=self.viewport_cycle.repair_eta_ticks,

                structural_integrity=self.hull_cycle.value,
                hull_state=self.hull_cycle.state,
                hull_event_label=self.hull_cycle.current_label,
                hull_repair_eta_ticks=self.hull_cycle.repair_eta_ticks,

                micrometeorite_pings_today=self.micrometeorite_pings_today,
            ),
            stars_visible=stars,
            site_lat=self.lat, site_lon=self.lon,
        )

    @staticmethod
    def _sun_phase(sun_alt: float) -> DomePhase:
        if abs(sun_alt) <= _TERMINATOR_BAND_DEG:
            return DomePhase.TERMINATOR_RISING if sun_alt >= 0 else DomePhase.TERMINATOR_SETTING
        return DomePhase.LUNAR_DAY if sun_alt > 0 else DomePhase.LUNAR_NIGHT