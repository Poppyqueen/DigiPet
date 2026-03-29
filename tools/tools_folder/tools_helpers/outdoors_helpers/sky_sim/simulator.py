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
    StarResult, PlanetResult, MoonResult, SunResult, TwilightPhase,
    BortleClass, DarkAdaptation, SkyConditionNarrative, VisibilityState,
    EclipseType
)
from .cloud_sim  import CloudSimulation
from .atmosphere import (
    score_atmosphere, atmospheric_extinction,
    cloud_opacity_to_magnitude_loss, visibility_to_magnitude_loss,
    moon_magnitude_loss, sun_magnitude_loss,
)
from .astro import AstroProvider
from datetime import datetime, timezone, timedelta
# Import your custom utility
from utils.loc_datetime import CoordinateDateTime 

ECLIPSE_LOOKUP = False # DEBUG FLAG
ECLIPSE_TARGET = EclipseType.LUNAR
# ---------------------------------------------------------------------------
# Constants & Mappings
# ---------------------------------------------------------------------------

_DARK_ADAPTATION_BONUS = {
    DarkAdaptation.NONE:    -1.5,
    DarkAdaptation.PARTIAL: -0.5,
    DarkAdaptation.FULL:     0.0,
}

_MIN_ALTITUDE_DEG = 5.0

# Bortle limiting magnitude — these already encode light pollution for that sky class.
# Do NOT subtract an additional LP loss from these values.
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
        print(f"elevation: {self.elevation_m}")

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
        self._base_limiting_mag = _BORTLE_LIMITING_MAG[self._bortle]

        print(f"[NightSky] Initialising astronomy engine for {self._coord_clock.timezone_info['name']}...")
        self._astro = AstroProvider(lat, lon, elevation_m)
        self._clouds = CloudSimulation(seed=noise_seed)

        if ECLIPSE_LOOKUP: # DEBUG TO MOVE INTO AN ECLIPSE

            future_eclipse_time = self._astro.get_next_visible_eclipse(self._simulated_time, ECLIPSE_TARGET)
            if future_eclipse_time:
                self._simulated_time = future_eclipse_time
                print(f"Found eclipse for selected location! {future_eclipse_time}. Simulation set to the future!")
            else:
                print(f"Couldn't find {ECLIPSE_TARGET}")
                
        
            

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
        dt_utc  = self._simulated_time
        weather = self._last_weather
        local_dt = dt_utc.astimezone(self._coord_clock.timezone)

        if weather is None:
            raise RuntimeError("No weather data available.")

        # --- Sun (authoritative day/night signal) ---
        sun = self._astro.get_sun(dt_utc)

        # --- Moon ---
        moon    = self._astro.get_moon(dt_utc)
        eclipse = self._astro.get_eclipse(dt_utc)

        moon_loss             = moon_magnitude_loss(moon.illumination, moon.altitude, eclipse)
        moon.magnitude_impact = moon_loss

        # --- Atmosphere (now includes sun altitude) ---
        atm = score_atmosphere(
            weather=weather,
            bortle=self._bortle,
            moon_illumination=moon.illumination,
            moon_altitude=moon.altitude,
            #light_pollution_mag_loss=0.0,   # LP is already baked into _base_limiting_mag
            sun_altitude=sun.altitude,
            eclipse = eclipse
        )

        limiting_mag = self._compute_limiting_magnitude(atm)

        # --- Moon & Sun cloud visibility ---
        # Same pipeline as stars/planets: cloud opacity at their position drives
        # effective_magnitude and visibility state. BELOW_LIMIT is astronomically
        # impossible for the Sun (-26.74) and extremely unlikely for the Moon, but
        # the logic doesn't need special-casing — it just works.
        if moon.above_horizon:
            moon_vis, moon_opacity = self._classify_visibility(
                moon.magnitude, moon.altitude, moon.azimuth, atm, limiting_mag
            )
            moon.effective_magnitude = self._effective_magnitude(
                moon.magnitude, moon.altitude, moon.azimuth, atm
            )
            moon.visibility    = moon_vis
            moon.cloud_opacity = moon_opacity

        if sun.above_horizon:
            sun_vis, sun_opacity = self._classify_visibility(
                sun.magnitude, sun.altitude, sun.azimuth, atm, limiting_mag
            )
            sun.effective_magnitude = self._effective_magnitude(
                sun.magnitude, sun.altitude, sun.azimuth, atm
            )
            sun.visibility    = sun_vis
            sun.cloud_opacity = sun_opacity

        # --- Stars ---
        raw_stars    = self._astro.get_stars(dt_utc)
        star_results = self._evaluate_stars(raw_stars, atm, limiting_mag, sun.altitude)

        # --- Planets ---
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
        """
        The faintest magnitude a fully dark-adapted observer can see under
        current conditions at this Bortle class.

        _base_limiting_mag already encodes light pollution for this Bortle class,
        so we only subtract additional sky-brightness losses on top of that:
          - dark adaptation bonus (negative = reduces limit for unadapted eyes)
          - haze / aerosol visibility loss
          - moon sky-glow
          - sun / twilight sky-glow  (dominant signal during the day)
        """
        adaptation_bonus = _DARK_ADAPTATION_BONUS[self._dark_adaptation]
        
        limiting = (
            self._base_limiting_mag
            + adaptation_bonus
            - atm.visibility_mag_loss
            - atm.moon_mag_loss
            - atm.sun_mag_loss
        )

        # DYNAMIC FLOOR:
        # If it's day (sun_mag_loss > 1.0), we allow the limit to drop deep 
        # into the negatives. If it's night, we keep the 0.5/1.0 comfort floor.
        if atm.sun_mag_loss > 1.0:
            return max(limiting, -4.5) # Only Moon and Venus survive
        
        return max(limiting, 0.5)


    # HYG v4.2 includes Sol (the Sun) as a star with magnitude ~-26.7.
    # We never want it to appear in star lists — it is handled via SunResult.
    _SOL_NAMES = {"sol", "sun"}

    def _full_effective_magnitude(self, mag, alt, az, atm):
        ext = atmospheric_extinction(alt)
        haze = atm.visibility_mag_loss * 0.5
        opacity = self._clouds.opacity_at(az, alt)
        cloud_loss = cloud_opacity_to_magnitude_loss(opacity)
        return mag + ext + haze + cloud_loss, opacity

    def _classify_visibility(self, mag, alt, az, atm, limiting_mag):
        eff_mag, opacity = self._full_effective_magnitude(mag, alt, az, atm)
        if eff_mag <= limiting_mag:
            return VisibilityState.VISIBLE, opacity
        # Diagnose
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
    # Weather Translation (Wiring to your OpenMeteoLoc)
    # ------------------------------------------------------------------

    def _maybe_refresh_weather(self, force: bool = False, initial: bool = False) -> Optional[WeatherSnapshot]:
        if not force and self._minutes_since_weather_refresh < self._weather_refresh_interval:
            return self._last_weather

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