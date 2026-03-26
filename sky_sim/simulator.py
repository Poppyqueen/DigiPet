"""
sky_sim/simulator.py
--------------------
NightSkySimulator — the single public entry point for the sky simulation.
"""
# We should update this as much as possible and necessary to have rich data for our clustering algorithm, not only rich but standarized, solid and observable.
from __future__ import annotations
import math
#from datetime import datetime, timezone, timedelta
from typing import Optional

from .types import (
    SkySnapshot, WeatherSnapshot, AtmosphereScores,
    StarResult, PlanetResult, MoonResult,
    BortleClass, DarkAdaptation, SkyConditionNarrative,
)
from .cloud_sim  import CloudSimulation
from .atmosphere import (
    score_atmosphere, atmospheric_extinction,
    cloud_opacity_to_magnitude_loss, visibility_to_magnitude_loss,
    moon_magnitude_loss,
)
from .astro import AstroProvider
from datetime import datetime, timezone, timedelta
# Import your custom utility
from utils.loc_datetime import CoordinateDateTime 

# ---------------------------------------------------------------------------
# Constants & Mappings
# ---------------------------------------------------------------------------

_DARK_ADAPTATION_BONUS = {
    DarkAdaptation.NONE:    -1.5,
    DarkAdaptation.PARTIAL: -0.5,
    DarkAdaptation.FULL:     0.0,
}

_MIN_ALTITUDE_DEG = 5.0

# Hardcoded light pollution limits based on Bortle Class (no GeoTIFF needed)
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

_BORTLE_MAG_LOSS = {
    BortleClass.PRISTINE:       0.0,
    BortleClass.TRULY_DARK:     0.2,
    BortleClass.RURAL:          0.5,
    BortleClass.RURAL_SUBURBAN: 1.0,
    BortleClass.SUBURBAN:       1.5,
    BortleClass.BRIGHT_SUBURBAN:2.0,
    BortleClass.SUBURBAN_URBAN: 2.5,
    BortleClass.CITY:           3.0,
    BortleClass.INNER_CITY:     4.0,
}

# ---------------------------------------------------------------------------
# NightSkySimulator
# ---------------------------------------------------------------------------


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
        weather_refresh_minutes: float = 15.0,
    ):
        self.lat = lat
        self.lon = lon
        self.elevation_m = elevation_m

        # --- Timezone Integration ---
        # Initialize your coordinate-aware clock
        self._coord_clock = CoordinateDateTime(lat, lon)
        
        # Set simulated time to "Now" at the target coordinates, converted to UTC
        # This ensures the simulation matches the actual sky at that location
        self._simulated_time = self._coord_clock.now().astimezone(timezone.utc)
        # ----------------------------

        self._weather_provider = weather_provider
        self._dark_adaptation = DarkAdaptation(dark_adaptation)
        self._weather_refresh_interval = weather_refresh_minutes

        self._bortle = BortleClass(bortle_class)
        self._lp_mag_loss = _BORTLE_MAG_LOSS[self._bortle]
        self._base_limiting_mag = _BORTLE_LIMITING_MAG[self._bortle]

        print(f"[NightSky] Initialising astronomy engine for {self._coord_clock.timezone_info['name']}...")
        self._astro = AstroProvider(lat, lon, elevation_m)
        self._clouds = CloudSimulation(seed=noise_seed)

        self._tick_count = 0
        self._minutes_since_weather_refresh = 9999.0
        self._last_weather = None

        self._maybe_refresh_weather(force=True, initial=True)

    # ------------------------------------------------------------------
    # Time Control & Snapshots
    # ------------------------------------------------------------------


    def tick(self, minutes: float = 1.0) -> None:
        # We step forward in UTC time
        self._simulated_time += timedelta(minutes=minutes)
        self._minutes_since_weather_refresh += minutes
        self._clouds.tick(delta_minutes=minutes)
        self._maybe_refresh_weather()
        self._tick_count += 1

    def set_time(self, dt: datetime) -> None:
        self._simulated_time = dt.astimezone(timezone.utc)

    def refresh_weather(self) -> WeatherSnapshot:
        return self._maybe_refresh_weather(force=True)

    def snapshot(self) -> SkySnapshot:
        dt_utc = self._simulated_time
        weather = self._last_weather

        local_dt = dt_utc.astimezone(self._coord_clock.timezone)


        if weather is None:
            raise RuntimeError("No weather data available.")

        # Moon
        moon = self._astro.get_moon(dt_utc)
        moon_loss = moon_magnitude_loss(moon.illumination, moon.altitude)
        moon.magnitude_impact = moon_loss

        # Atmosphere
        atm = score_atmosphere(
            weather=weather,
            bortle=self._bortle,
            moon_illumination=moon.illumination,
            moon_altitude=moon.altitude,
            light_pollution_mag_loss=self._lp_mag_loss,
        )

        limiting_mag = self._compute_limiting_magnitude(atm)

        # Stars & Planets
        raw_stars = self._astro.get_stars(dt_utc)
        star_results = self._evaluate_stars(raw_stars, atm, limiting_mag)
        visible_stars   =[s for s in star_results if s.visible] 
        obscured_stars  =[s for s in star_results if not s.visible and s.altitude >= _MIN_ALTITUDE_DEG] # We need to trace this, debug acts weird and not sure I understand what it is meant to represent, but it is important. "obscured by cloud", seems straightforward, what weirds me out in the logs is that the STARS VISIBLE and OBSCURED BY CLOUD changes do not correlate nor agree. 

        raw_planets  = self._astro.get_planets(dt_utc)
        planet_results = self._evaluate_planets(raw_planets, atm, limiting_mag) # Planets needs to change

        cloud_coverage = self._clouds.simulated_cloud_coverage(samples=200)

        return SkySnapshot(
            latitude=self.lat,
            longitude=self.lon,
            local_time=local_dt.isoformat(), # Now shows the correct local time!
            timezone=self._coord_clock.timezone_info['name'],
            weather=weather,
            atmosphere=atm,
            moon=moon,
            bortle_class=self._bortle,
            limiting_magnitude=limiting_mag,
            stars_visible=visible_stars,
            stars_obscured=obscured_stars, # OBSCURED BY CLOUD  (275) in BortleClass.CITY this doesn't seem right if you think these are only the total pool of visible by the naked eye
            planets=planet_results,
            simulation_tick=self._tick_count,
            cloud_coverage_simulated=cloud_coverage,
            condition=weather.condition_narrative,
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
            - atm.light_pollution_mag_loss * 1 # I changed this from 0, before it was doing nothing, but not sure why it was like that... 
            - atm.moon_mag_loss
            # can we add sun intesnity limiting?
        )
        return max(limiting, 1.0)

    def _effective_magnitude(self, magnitude: float, altitude: float, azimuth: float, atm: AtmosphereScores) -> float:
        ext     = atmospheric_extinction(altitude)
        haze    = atm.visibility_mag_loss * 0.5
        opacity = self._clouds.opacity_at(azimuth, altitude)
        cloud   = cloud_opacity_to_magnitude_loss(opacity)
        return magnitude + ext + haze + cloud

    def _evaluate_stars(self, raw_stars: list, atm: AtmosphereScores, limiting_mag: float) -> list[StarResult]:
        results =[]
        for name, mag, az, alt, const in raw_stars:
            if alt < _MIN_ALTITUDE_DEG: continue
            opacity      = self._clouds.opacity_at(az, alt)
            cloud_loss   = cloud_opacity_to_magnitude_loss(opacity)
            eff_mag      = self._effective_magnitude(mag, alt, az, atm)
            visible      = eff_mag <= limiting_mag

            results.append(StarResult(
                name=name, magnitude=mag, azimuth=az, altitude=alt,
                effective_magnitude=eff_mag, visible=visible,
                obscured_by_cloud=cloud_loss > 2.0, constellation=const,
            ))
        return results

    def _evaluate_planets(self, raw_planets: list, atm: AtmosphereScores, limiting_mag: float) -> list[PlanetResult]:
        results =[] # Is this the best, standard, professional way of doing this?
        for name, mag, az, alt in raw_planets:
            if alt < _MIN_ALTITUDE_DEG: continue
            opacity    = self._clouds.opacity_at(az, alt)
            cloud_loss = cloud_opacity_to_magnitude_loss(opacity)
            eff_mag    = self._effective_magnitude(mag, alt, az, atm)
            visible    = eff_mag <= limiting_mag

            results.append(PlanetResult(
                name=name, magnitude=mag, azimuth=az, altitude=alt,
                effective_magnitude=eff_mag, visible=visible,
                obscured_by_cloud=cloud_loss > 2.0,
            ))
        return results

    # ------------------------------------------------------------------
    # Weather Translation (Wiring to your OpenMeteoLoc)
    # ------------------------------------------------------------------

    def _maybe_refresh_weather(self, force: bool = False, initial: bool = False) -> Optional[WeatherSnapshot]:
        if not force and self._minutes_since_weather_refresh < self._weather_refresh_interval:
            print("DEBUG SIMULATOR, REFRESH WEATHER FAILED")
            return self._last_weather
        print("DEBUG SIMULATOR REFRESH WEATHER CHECK PASSED")

        try:
            print(f"[NightSky] Fetching weather at tick {self._tick_count}...")
            
            # 1. Fetch from your existing class
            raw = self._weather_provider.get_structured_weather()
            
            # Helper to handle 'None' values from _safe()
            def s(val, default=0.0):
                return float(val) if val is not None else default

            # 2. Re-apply the visibility floor right here 
            vis = s(raw.get("visibility"), 10000.0)
            vis = max(vis, 100.0)

            # 3. Map your dictionary into our expected dataclass
            weather = WeatherSnapshot(
                cloud_cover_total=s(raw.get("cloud_cover")),
                cloud_cover_low=s(raw.get("cloud_cover_low")),
                cloud_cover_mid=s(raw.get("cloud_cover_mid")),
                cloud_cover_high=s(raw.get("cloud_cover_high")),
                visibility_m=vis,
                humidity=s(raw.get("humidity")),
                dew_point=s(raw.get("dew_point")),
                temperature=s(raw.get("temperature")),
                precipitation=s(raw.get("precipitation")),
                wind_speed_10m=s(raw.get("wind_speed")),
                wind_direction_10m=s(raw.get("wind_direction")),
                wind_speed_120m=s(raw.get("wind_speed_120m")),
                cape=s(raw.get("cape")),
                weather_code=int(raw.get("weather_code") or 0),
                is_day=bool(raw.get("is_day"))
            )

            self._last_weather = weather
            self._clouds.weather_update(weather)

            # # Snap clouds instantly if this is the initial load
            if initial:
            #     self._clouds.snap_to_targets()
                self._clouds.inits()
                
            self._minutes_since_weather_refresh = 0.0
            return weather
        except Exception as e:
            print(f"[NightSky] Weather fetch failed: {e}")
            return self._last_weather

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def bortle_class(self) -> BortleClass: return self._bortle
    @property
    def simulated_time(self) -> datetime: return self._simulated_time
    @property
    def tick_count(self) -> int: return self._tick_count