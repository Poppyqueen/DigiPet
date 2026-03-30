from __future__ import annotations
import math
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

from skyfield.api import Star, load, wgs84, Loader
from skyfield import almanac
from skyfield.magnitudelib import planetary_magnitude

from .types import (StarResult, PlanetResult,
                    MoonResult, SunResult, TwilightPhase,
                    EclipseResult, EclipseType, EclipsePhase,
                    )

from .atmosphere import sun_magnitude_loss

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------
_PARENT = Path(__file__).parent
_DATA_DIR = _PARENT / "local_data"

_HYG_DERIVATIVE_FOLDER = _PARENT / "HYG_Database" 
_HYG_LOCAL_FILTERED = _HYG_DERIVATIVE_FOLDER / "hyg_v42_naked_eye.csv"
# HYG Database v4.2 — filtered derivative work (mag <= 6.5, key columns only).
# See local_data/HYG_ATTRIBUTION.md for license and source information.
# See: https://www.astronexus.com/projects/hyg

# ---------------------------------------------------------------------------
# AstroProvider
# ---------------------------------------------------------------------------

class AstroProvider:
    def __init__(self, lat: float, lon: float, elevation_m: float = 0.0):
        self.lat = lat
        self.lon = lon

        self._loader = Loader(_DATA_DIR)
        self._ts = self._loader.timescale()
        self._eph = self._loader('de421.bsp')
        self._earth = self._eph['earth']
        
        # Store the raw geographic location (Topos/Geodetic)
        self._location = wgs84.latlon(lat, lon, elevation_m=elevation_m)

        self._observer = self._earth + self._location

        self._star_df = self._load_stars()

        # Initialize Skyfield Star objects from the RA/Dec columns.
        # Using .values for maximum speed.
        self._star_objects = Star(
            ra_hours=self._star_df['ra'].values,
            dec_degrees=self._star_df['dec'].values
        )

        print(f"[Astro] Ready. {len(self._star_df)} IAU-verified stars loaded.")

    def _load_stars(self) -> pd.DataFrame:
        if not _HYG_LOCAL_FILTERED.exists():
            raise FileNotFoundError(
                f"Star catalog missing!!! {_HYG_LOCAL_FILTERED}.\n"
                "This shouldn't happen under normal conditions.\n"
                "Use sky_sim/HYG_Database/generate_star_catalog.py as a module (python -m) to re-generate."
            )
        return pd.read_csv(_HYG_LOCAL_FILTERED, comment='#')

    def _to_skyfield_time(self, dt: datetime):
        """Helper to ensure any datetime is converted to Skyfield-compatible UTC."""
        if dt.tzinfo is None:
            return self._ts.from_datetime(dt.replace(tzinfo=timezone.utc))
        return self._ts.from_datetime(dt.astimezone(timezone.utc))

    def get_stars(self, dt: datetime) -> list:
        """Vectorized calculation of star positions."""
        t = self._to_skyfield_time(dt)

        astrometric = self._observer.at(t).observe(self._star_objects)
        alt, az, _ = astrometric.apparent().altaz()

        names = self._star_df['proper'].values
        bfs   = self._star_df['bf'].values
        mags  = self._star_df['mag'].values
        cons  = self._star_df['con'].values

        results = []
        for i in range(len(mags)):
            if pd.notna(names[i]):
                label = names[i]
            elif pd.notna(bfs[i]):
                label = bfs[i]
            else:
                label = f"Star in {cons[i]}"

            results.append((
                label,
                float(mags[i]),
                float(az.degrees[i] % 360),
                float(alt.degrees[i]),
                str(cons[i])
            ))
        return results

    # ------------------------------------------------------------------
    # Standard Observers
    # ------------------------------------------------------------------

    def get_moon(self, dt: datetime) -> MoonResult:
        t = self._to_skyfield_time(dt)
        astrometric = self._observer.at(t).observe(self._eph['moon'])
        apparent = astrometric.apparent()
        alt, az, _ = apparent.altaz()
        phase_angle = almanac.moon_phase(self._eph, t)

        illumination = (1 - math.cos(math.radians(phase_angle.degrees))) / 2.0

        # Days into synodic month (new moon = 0, full = ~14.77, back to new = 29.53)
        SYNODIC_MONTH = 29.530588
        days_from_new = (phase_angle.degrees / 360.0) * SYNODIC_MONTH

        # Determine waxing vs waning by sampling one hour ahead
        dt_ahead = (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)) + timedelta(hours=1)
        t_ahead = self._to_skyfield_time(dt_ahead)
        phase_ahead = almanac.moon_phase(self._eph, t_ahead)
        illum_ahead = (1 - math.cos(math.radians(phase_ahead.degrees))) / 2.0
        waxing = illum_ahead > illumination

        # Apparent magnitude — Skyfield computes this from phase angle and distance.
        # Ranges from ~-12.7 (full moon) down to ~-2.5 (thin crescent).
        try:
            mag = apparent.magnitude()
        except Exception:
            # Fallback: approximate from illumination if Skyfield can't compute it
            # Full moon ~ -12.7, new moon ~ -2.5, linear in between is a rough but safe fallback
            mag = -2.5 + (-12.7 - (-2.5)) * illumination

        return MoonResult(
            phase_angle=phase_angle.degrees,
            illumination=illumination,
            days_from_new=days_from_new,
            waxing=waxing,
            azimuth=az.degrees % 360,
            altitude=alt.degrees,
            above_horizon=alt.degrees > 0,
            magnitude_impact=0.0,   # filled in by simulator after eclipse is known
            magnitude=float(mag),
            # effective_magnitude, visibility, cloud_opacity filled in by simulator
        )

    def get_planets(self, dt: datetime) -> list[tuple]:
        t = self._to_skyfield_time(dt)
        keys  = ["mercury", "venus", "mars", "jupiter barycenter", "saturn barycenter"]
        names = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
        results = []
        for i, key in enumerate(keys):
            try:
                body = self._eph[key]
                astrometric = self._observer.at(t).observe(body)
                alt, az, _ = astrometric.apparent().altaz()
                mag = planetary_magnitude(astrometric.apparent())
                results.append((names[i], mag, az.degrees % 360, alt.degrees))
            except:
                continue
        return results

    def get_sun(self, dt: datetime) -> SunResult:
        """
        Return the Sun's full observational state at the given moment.
        This is the authoritative source for day/night and twilight logic.
        """
        t = self._to_skyfield_time(dt)
        astrometric = self._observer.at(t).observe(self._eph['sun'])
        apparent = astrometric.apparent()
        alt, az, _ = apparent.altaz()
        altitude = alt.degrees
        azimuth  = az.degrees % 360
        
        f = almanac.dark_twilight_day(self._eph, self._location)
        phase_value = int(f(t))

        phase_mapping = {
            0: TwilightPhase.NIGHT,
            1: TwilightPhase.ASTRO_TWILIGHT,
            2: TwilightPhase.NAUTICAL_TWILIGHT,
            3: TwilightPhase.CIVIL_TWILIGHT,
            4: TwilightPhase.DAY
        }
        phase = phase_mapping.get(phase_value)

        mag_impact = sun_magnitude_loss(altitude)

        # The Sun's apparent magnitude is essentially fixed at -26.74.
        # Skyfield can compute it but it barely varies, so we use the constant
        # and let the cloud sim do its work on effective_magnitude in the simulator.
        SUN_APPARENT_MAGNITUDE = -26.74

        return SunResult(
            azimuth=azimuth,
            altitude=altitude,
            above_horizon=altitude > 0.0,
            twilight_phase=phase,
            magnitude_impact=mag_impact,
            magnitude=SUN_APPARENT_MAGNITUDE,
            # effective_magnitude, visibility, cloud_opacity filled in by simulator
        )
    
    def get_sun_altitude(self, dt: datetime) -> float:
        """Convenience accessor — returns just the altitude in degrees."""
        return self.get_sun(dt).altitude

    def get_next_visible_eclipse(self, dt: datetime, eclipse_type: EclipseType = None) -> EclipseResult:
        """
        Finds the next eclipse visible from the observer's specific lat/lon.
        If eclipse_type is None, it returns the very next one (Solar or Lunar).
        """
        ts = self._ts
        eph = self._eph
        t0 = self._to_skyfield_time(dt)
        # Search up to 2 years ahead to ensure we find one
        t1 = ts.from_datetime(dt + timedelta(days=365 * 2))

        # Find New Moons (0) and Full Moons (2)
        f = almanac.moon_phases(eph)
        times, phases = almanac.find_discrete(t0, t1, f)

        for t, phase in zip(times, phases):
            # Skip quarters
            if phase in [1, 3]: 
                continue
                
            # Convert Skyfield time back to datetime for your internal method
            check_dt = t.astimezone(timezone.utc)
            
            # Use your existing heavy-lifting logic!
            result = self.get_eclipse(check_dt)

            # 1. Filter by the type requested (if any)
            if eclipse_type and result.eclipse_type != eclipse_type:
                continue

            # 2. The Golden Rule: Is it visible at our coordinates?
            # This checks if the Sun/Moon is above the horizon and if the shadow hits us.
            if result.visible_from_here and result.eclipse_type != EclipseType.NONE:
                # We add the time to the result so the user knows WHEN it is
                # (You might need to add a 'time' field to your EclipseResult type)
                result.note = f"Visible at {check_dt.strftime('%Y-%m-%d %H:%M')} UTC. " + result.note
                return check_dt  - timedelta(minutes=2.95*60)

        return None
    



    def get_eclipse(self, dt: datetime) -> "EclipseResult":
        """
        Compute the current eclipse state (solar or lunar) for the observer.

        Algorithm:
        Solar eclipse  — Moon passes in front of the Sun (new moon geometry).
                        We compute the angular separation between Sun and Moon
                        centres, then compare against combined apparent radii.
        Lunar eclipse  — Earth's shadow falls on the Moon (full moon geometry).
                        We use the Moon's elongation from the Sun and compare
                        against the umbral and penumbral cone radii projected
                        at the Moon's distance.

        All angular quantities are in degrees.
        Magnitude follows the IAU convention:
        solar:  (R_sun + R_moon − sep) / (2 × R_moon)
        lunar:  (R_umbra + R_moon − sep_from_shadow_axis) / (2 × R_moon)
        where R_* are apparent radii in degrees.
        """

        t = self._to_skyfield_time(dt)

        sun  = self._eph['sun']
        moon = self._eph['moon']

        # Geocentric positions — for lunar shadow cone geometry (Earth-centred phenomenon)
        earth_centre = self._eph['earth']
        sun_geo  = earth_centre.at(t).observe(sun).apparent()
        moon_geo = earth_centre.at(t).observe(moon).apparent()

        # Topocentric positions — for what this specific observer actually sees
        sun_topo  = self._observer.at(t).observe(sun).apparent()
        moon_topo = self._observer.at(t).observe(moon).apparent()
        sun_alt,  _, _ = sun_topo.altaz()
        moon_alt, _, _ = moon_topo.altaz()

        # Geocentric separation — used for lunar shadow axis distance
        sep_deg_geo  = sun_geo.separation_from(moon_geo).degrees
        # Topocentric separation — used for solar eclipse (what this observer sees)
        sep_deg_topo = sun_topo.separation_from(moon_topo).degrees

        # ── Apparent radii (degrees) ────────────────────────────────────────────
        # Derived from known physical radii and current distances.
        R_SUN_KM   = 696_000.0
        R_MOON_KM  =   1_737.4
        R_EARTH_KM =   6_371.0

        sun_distance_km  = sun_geo.distance().km
        moon_distance_km = moon_geo.distance().km

        r_sun_app  = math.degrees(math.atan(R_SUN_KM  / sun_distance_km))
        r_moon_app = math.degrees(math.atan(R_MOON_KM / moon_distance_km))

        # ── Solar eclipse check ─────────────────────────────────────────────────
        # Topocentric: does *this observer* see the Moon covering the Sun?
        solar_limit      = r_sun_app + r_moon_app
        is_solar_contact = sep_deg_topo < solar_limit

        # ── Lunar eclipse check ─────────────────────────────────────────────────
        # Geocentric: is the Moon inside Earth's shadow cone?
        f1 = math.atan((R_SUN_KM + R_EARTH_KM) / sun_distance_km)   # penumbra half-angle
        f2 = math.atan((R_SUN_KM - R_EARTH_KM) / sun_distance_km)   # umbra half-angle
        r_penumbra_app = math.degrees(f1 + math.atan(R_EARTH_KM / moon_distance_km))
        r_umbra_app    = math.degrees(math.atan(R_EARTH_KM / moon_distance_km) - f2)

        dist_from_shadow_axis = abs(180.0 - sep_deg_geo)

        is_penumbral_contact = dist_from_shadow_axis < (r_penumbra_app + r_moon_app)
        is_umbral_contact    = dist_from_shadow_axis < (r_umbra_app    + r_moon_app)

        # ── Classify ────────────────────────────────────────────────────────────
        eclipse_type  = EclipseType.NONE
        eclipse_phase = EclipsePhase.NONE
        magnitude     = 0.0
        obscuration   = 0.0
        umbral_depth  = 0.0
        gamma         = None
        note          = "No eclipse in progress."

        if is_solar_contact:
            eclipse_type = EclipseType.SOLAR
            magnitude = (r_sun_app + r_moon_app - sep_deg_topo) / (2.0 * r_moon_app)

            # Obscuration — lens-shaped intersection of two circles
            d, r, R = sep_deg_topo, r_moon_app, r_sun_app
            if d <= abs(R - r):
                obscuration = min(r, R)**2 / R**2
            elif d < r + R:
                cos_a = (d*d + R*R - r*r) / (2*d*R)
                cos_b = (d*d + r*r - R*R) / (2*d*r)
                cos_a = max(-1.0, min(1.0, cos_a))
                cos_b = max(-1.0, min(1.0, cos_b))
                alpha = math.acos(cos_a)
                beta  = math.acos(cos_b)
                area  = R*R*alpha + r*r*beta - R*R*math.sin(alpha)*math.cos(alpha) - r*r*math.sin(beta)*math.cos(beta)
                obscuration = area / (math.pi * R * R)
            else:
                obscuration = 0.0
            obscuration = max(0.0, min(1.0, obscuration))

            if sep_deg_topo <= abs(r_sun_app - r_moon_app):
                if r_moon_app >= r_sun_app:
                    eclipse_phase = EclipsePhase.TOTAL
                    note = f"Total solar eclipse! Magnitude {magnitude:.3f}. Corona visible. Day becomes night."
                else:
                    eclipse_phase = EclipsePhase.ANNULAR
                    note = f"Annular solar eclipse. Moon's disc ({r_moon_app*60:.1f}') < Sun's ({r_sun_app*60:.1f}'). Ring of fire visible."
            else:
                eclipse_phase = EclipsePhase.PARTIAL
                note = f"Partial solar eclipse. Magnitude {magnitude:.3f}, {obscuration*100:.1f}% of solar disc obscured."

        elif is_penumbral_contact:
            eclipse_type = EclipseType.LUNAR
            umbral_depth = dist_from_shadow_axis - r_moon_app

            if is_umbral_contact:
                in_umbra  = dist_from_shadow_axis + r_moon_app < r_umbra_app
                magnitude = (r_umbra_app + r_moon_app - dist_from_shadow_axis) / (2.0 * r_moon_app)
                if in_umbra:
                    eclipse_phase = EclipsePhase.TOTAL
                    note = (f"Total lunar eclipse! Moon fully immersed in Earth's umbra. "
                            f"Expect deep red/copper colour (Danjon scale). "
                            f"Magnitude {magnitude:.3f}.")
                else:
                    eclipse_phase = EclipsePhase.PARTIAL
                    note = (f"Partial lunar eclipse. {(dist_from_shadow_axis/r_umbra_app)*100:.0f}% "
                            f"of umbra traversed. Magnitude {magnitude:.3f}.")
                obscuration = max(0.0, min(1.0, magnitude))
            else:
                eclipse_phase = EclipsePhase.PENUMBRAL
                magnitude = (r_penumbra_app + r_moon_app - dist_from_shadow_axis) / (2.0 * r_moon_app)
                note = (f"Penumbral lunar eclipse. Subtle shading only — "
                        f"Moon in Earth's outer shadow. Magnitude {magnitude:.3f}. "
                        f"Unlikely to be visible to the naked eye unless deep.")
                obscuration = 0.0

        visible = (
            (eclipse_type == EclipseType.SOLAR and sun_alt.degrees  > 0.0) or
            (eclipse_type == EclipseType.LUNAR and moon_alt.degrees > 0.0)
        )

        return EclipseResult(
            eclipse_type=eclipse_type,
            phase=eclipse_phase,
            magnitude=magnitude,
            obscuration=obscuration,
            separation_deg=sep_deg_geo,   # geocentric — intrinsic orbital geometry
            umbral_depth=umbral_depth,
            visible_from_here=visible,
            saros_series=None,
            gamma=gamma,
            note=note,
        )