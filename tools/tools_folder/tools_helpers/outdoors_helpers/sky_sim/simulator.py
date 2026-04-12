"""
sky_sim/simulator.py
--------------------
NightSkySimulator — the single public entry point for the sky simulation.
Time is always real: coord_clock.now(). There is no simulated time.
"""
from __future__ import annotations
import math
from typing import Optional
from datetime import timezone

from .types import (
    SkySnapshot, WeatherSnapshot, AtmosphereScores,
    StarResult, PlanetResult, MoonResult, SunResult, TwilightPhase,
    BortleClass, DarkAdaptation, SkyConditionNarrative, VisibilityState,
    EclipseType
)
from .cloud_sim import CloudSimulation
from .atmosphere import (
    score_atmosphere, atmospheric_extinction,
    cloud_opacity_to_magnitude_loss, visibility_to_magnitude_loss,
    moon_magnitude_loss, sun_magnitude_loss,
)
from .astro import AstroProvider
from utils.loc_datetime import CoordinateDateTime


_DARK_ADAPTATION_BONUS = {
    DarkAdaptation.NONE:    -1.5,
    DarkAdaptation.PARTIAL: -0.5,
    DarkAdaptation.FULL:     0.0,
}

_MIN_ALTITUDE_DEG = 5.0

_BORTLE_LIMITING_MAG = {
    BortleClass.PRISTINE:       7.0,
    BortleClass.TRULY_DARK:     6.8,
    BortleClass.RURAL:          6.5,
    BortleClass.RURAL_SUBURBAN: 6.0,
    BortleClass.SUBURBAN:       5.5,
    BortleClass.BRIGHT_SUBURBAN:5.0,
    BortleClass.SUBURBAN_URBAN: 4.5,
    BortleClass.CITY:           4.0,
    BortleClass.INNER_CITY:     3.0,
}


class NightSkySimulator:
    def __init__(
        self,
        lat: float,
        lon: float,
        weather_provider,
        elevation_m: float = 0.0,
        bortle_class: int = 4,
        dark_adaptation: str = "full",
        noise_seed: int = 42,
    ):
        self.lat = lat
        self.lon = lon
        self.elevation_m = elevation_m
        print(f"elevation: {self.elevation_m}")

        self._coord_clock = CoordinateDateTime(lat, lon)
        self._weather_provider = weather_provider
        self._dark_adaptation = DarkAdaptation(dark_adaptation)

        self._bortle = BortleClass(bortle_class)
        self._base_limiting_mag = _BORTLE_LIMITING_MAG[self._bortle]

        print(f"[NightSky] Initialising astronomy engine for {self._coord_clock.timezone_info['name']}...")
        self._astro = AstroProvider(lat, lon, elevation_m)
        self._clouds = CloudSimulation(seed=noise_seed)

        self._tick_count = 0

        # Prime the cloud sim with current weather on init
        self._bootstrap_clouds()

    # ------------------------------------------------------------------
    # Time — always real, never simulated
    # ------------------------------------------------------------------

    @property
    def now_utc(self):
        return self._coord_clock.now().astimezone(timezone.utc)

    # ------------------------------------------------------------------
    # Tick — advances cloud morphology only; time comes from the clock
    # ------------------------------------------------------------------

    def tick(self) -> None:
        weather = self._fetch_weather()
        self._clouds.weather_update(weather)
        self._clouds.tick(delta_minutes=1.0)
        self._tick_count += 1

    # ------------------------------------------------------------------
    # Snapshot — observe the sky right now
    # ------------------------------------------------------------------

    def snapshot(self) -> SkySnapshot:
        dt_utc   = self.now_utc
        local_dt = dt_utc.astimezone(self._coord_clock.timezone)

        weather = self._fetch_weather()
        self._clouds.weather_update(weather)

        # --- Sun ---
        sun = self._astro.get_sun(dt_utc)
        print(f"DEBUG SKY SIM SIMULATOR: SUN {sun}")

        # --- Moon ---
        moon    = self._astro.get_moon(dt_utc)
        eclipse = self._astro.get_eclipse(dt_utc)

        moon.magnitude_impact = moon_magnitude_loss(moon.illumination, moon.altitude, eclipse)

        # --- Atmosphere ---
        atm = score_atmosphere(
            weather=weather,
            bortle=self._bortle,
            moon_illumination=moon.illumination,
            moon_altitude=moon.altitude,
            sun_altitude=sun.altitude,
            eclipse=eclipse,
        )

        limiting_mag = self._compute_limiting_magnitude(atm)

        # --- Moon visibility ---
        if moon.above_horizon:
            moon_vis, moon_opacity = self._classify_visibility(
                moon.magnitude, moon.altitude, moon.azimuth, atm, limiting_mag
            )
            moon.effective_magnitude = self._effective_magnitude(
                moon.magnitude, moon.altitude, moon.azimuth, atm
            )
            moon.visibility    = moon_vis
            moon.cloud_opacity = moon_opacity

        # --- Sun visibility ---
        if sun.above_horizon:
            sun_vis, sun_opacity = self._classify_visibility(
                sun.magnitude, sun.altitude, sun.azimuth, atm, limiting_mag
            )
            sun.effective_magnitude = self._effective_magnitude(
                sun.magnitude, sun.altitude, sun.azimuth, atm
            )
            sun.visibility    = sun_vis
            sun.cloud_opacity = sun_opacity

        # --- Stars & planets ---
        raw_stars      = self._astro.get_stars(dt_utc)
        star_results   = self._evaluate_stars(raw_stars, atm, limiting_mag, sun.altitude)

        raw_planets    = self._astro.get_planets(dt_utc)
        planet_results = self._evaluate_planets(raw_planets, atm, limiting_mag)

        cloud_coverage = self._clouds.simulated_cloud_coverage(samples=200)

        return SkySnapshot(
            latitude=self.lat,
            longitude=self.lon,
            local_time=local_dt.isoformat(),
            timezone=self._coord_clock.timezone_info['name'],
            weather=weather,
            atmosphere=atm,
            moon=moon,
            sun=sun,
            bortle_class=self._bortle,
            limiting_magnitude=limiting_mag,
            stars=star_results,
            stars_above_horizon=len(star_results),
            planets=planet_results,
            simulation_tick=self._tick_count,
            cloud_coverage_simulated=cloud_coverage,
            condition=weather.condition_narrative,
            eclipse=eclipse,
        )

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def _compute_limiting_magnitude(self, atm: AtmosphereScores) -> float:
        adaptation_bonus = _DARK_ADAPTATION_BONUS[self._dark_adaptation]
        limiting = (
            self._base_limiting_mag
            + adaptation_bonus
            - atm.visibility_mag_loss
            - atm.moon_mag_loss
            - atm.sun_mag_loss
        )
        if atm.sun_mag_loss > 1.0:
            return max(limiting, -4.5)
        return max(limiting, 0.5)

    _SOL_NAMES = {"sol", "sun"}

    def _full_effective_magnitude(self, mag, alt, az, atm):
        ext        = atmospheric_extinction(alt)
        haze       = atm.visibility_mag_loss * 0.5
        opacity    = self._clouds.opacity_at(az, alt)
        cloud_loss = cloud_opacity_to_magnitude_loss(opacity)
        return mag + ext + haze + cloud_loss, opacity

    def _classify_visibility(self, mag, alt, az, atm, limiting_mag):
        eff_mag, opacity = self._full_effective_magnitude(mag, alt, az, atm)
        if eff_mag <= limiting_mag:
            return VisibilityState.VISIBLE, opacity
        eff_no_cloud = eff_mag - cloud_opacity_to_magnitude_loss(opacity)
        if eff_no_cloud <= limiting_mag:
            return VisibilityState.CLOUDED, opacity
        return VisibilityState.BELOW_LIMIT, opacity

    def _effective_magnitude(self, mag, alt, az, atm):
        eff, _ = self._full_effective_magnitude(mag, alt, az, atm)
        return eff

    def _evaluate_stars(self, raw_stars, atm, limiting_mag, sun_altitude) -> list[StarResult]:
        results = []
        for name, mag, az, alt, const in raw_stars:
            if alt < _MIN_ALTITUDE_DEG:
                continue
            if str(name).lower() in self._SOL_NAMES:
                continue
            state, opacity = self._classify_visibility(mag, alt, az, atm, limiting_mag)
            eff_mag = self._effective_magnitude(mag, alt, az, atm)
            results.append(StarResult(
                name=name, magnitude=mag, azimuth=az, altitude=alt,
                effective_magnitude=eff_mag, constellation=const,
                visibility=state, cloud_opacity=opacity,
            ))
        return results

    def _evaluate_planets(self, raw_planets, atm, limiting_mag) -> list[PlanetResult]:
        results = []
        for name, mag, az, alt in raw_planets:
            if alt < _MIN_ALTITUDE_DEG:
                continue
            state, opacity = self._classify_visibility(mag, alt, az, atm, limiting_mag)
            eff_mag = self._effective_magnitude(mag, alt, az, atm)
            results.append(PlanetResult(
                name=name, magnitude=mag, azimuth=az, altitude=alt,
                effective_magnitude=eff_mag, visibility=state, cloud_opacity=opacity,
            ))
        return results

    # ------------------------------------------------------------------
    # Weather — fetched fresh on every call, no caching
    # ------------------------------------------------------------------

    def _fetch_weather(self) -> WeatherSnapshot:
        print(f"[NightSky] Fetching weather at tick {self._tick_count}...")
        raw = self._weather_provider.get_structured_weather()

        def s(val, default=0.0):
            return float(val) if val is not None else default

        vis = max(s(raw.get("visibility"), 10000.0), 100.0)

        return WeatherSnapshot(
            cloud_cover_total   = s(raw.get("cloud_cover")),
            cloud_cover_low     = s(raw.get("cloud_cover_low")),
            cloud_cover_mid     = s(raw.get("cloud_cover_mid")),
            cloud_cover_high    = s(raw.get("cloud_cover_high")),
            visibility_m        = vis,
            humidity            = s(raw.get("humidity")),
            dew_point           = s(raw.get("dew_point")),
            temperature         = s(raw.get("temperature")),
            precipitation       = s(raw.get("precipitation")),
            wind_speed_10m      = s(raw.get("wind_speed")),
            wind_direction_10m  = s(raw.get("wind_direction")),
            wind_speed_120m     = s(raw.get("wind_speed_120m")),
            cape                = s(raw.get("cape")),
            weather_code        = int(raw.get("weather_code") or 0),
            is_day              = bool(raw.get("is_day")),
        )

    def _bootstrap_clouds(self) -> None:
        """Prime the cloud sim with current conditions on startup."""
        weather = self._fetch_weather()
        self._clouds.weather_update(weather)
        self._clouds.inits()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def bortle_class(self) -> BortleClass: return self._bortle

    @property
    def tick_count(self) -> int: return self._tick_count