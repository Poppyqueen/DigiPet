from __future__ import annotations
import math
import os
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

from skyfield.api import Star, load, wgs84, Loader
from skyfield import almanac
from skyfield.magnitudelib import planetary_magnitude

from .types import StarResult, PlanetResult, MoonResult, SunResult, TwilightPhase
from .atmosphere import sun_magnitude_loss

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "local_data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Using HYG Database
# THE NEW V4.2 DATASET: Most accurate names/positions
_HYG_URL = "https://codeberg.org/astronexus/hyg/media/branch/main/data/hyg/CURRENT/hyg_v42.csv.gz" # TODO: In the future to prevent requests to codeberg release the filtered dataset into our repo with correct attribution and licensing. It is a few kb of a CSV file we are making right now. Creating and distributing new derivative work.
_HYG_LOCAL_FILTERED = _DATA_DIR / "hyg_v42_naked_eye.csv"
# This module downloads processes stellar data from the HYG Database (v4.2), it then creates and saves a derivative work as a dataset into the local directory. Currently gitignored.
# See: https://www.astronexus.com/projects/hyg

# Source: https://codeberg.org/astronexus/hyg
# Creator: David Nash
# License: CC BY-SA 4.0

# ---------------------------------------------------------------------------
# AstroProvider
# ---------------------------------------------------------------------------

class AstroProvider: # Not sure if this is following the types we have 
    def __init__(self, lat: float, lon: float, elevation_m: float = 0.0):
        self.lat = lat
        self.lon = lon
        
        self._loader = Loader(_DATA_DIR)
        self._ts = self._loader.timescale()
        self._eph = self._loader('de421.bsp')
        self._earth = self._eph['earth']
        self._observer = self._earth + wgs84.latlon(lat, lon, elevation_m=elevation_m)

        # Load/Download the star catalog
        self._star_df = self._setup_stars()
        
        # Initialize Skyfield Star objects from the RA/Dec columns
        # We use .values for maximum speed
        self._star_objects = Star(
            ra_hours=self._star_df['ra'].values,
            dec_degrees=self._star_df['dec'].values
        )

        print(f"[Astro] Ready. {len(self._star_df)} IAU-verified stars loaded.")

    def _setup_stars(self) -> pd.DataFrame:
        """Downloads v4.2 from Codeberg if needed and filters to naked-eye stars."""
        if not _HYG_LOCAL_FILTERED.exists():
            print(f"[Astro] Downloading HYG v4.2 from Codeberg (~15MB compressed)...")
            try:
                # Pandas handles the .gz decompression automatically
                df = pd.read_csv(_HYG_URL, compression='gzip', low_memory=False)
                
                # Filter to stars visible to the human eye (Mag <= 6.5)
                # This reduces the ~120,000 stars to a manageable ~9,000
                df = df[df['mag'] <= 6.5].copy()
                
                # Keep only the essential columns for our simulation
                cols = ['proper', 'mag', 'ra', 'dec', 'con', 'bf']
                df = df[cols]
                
                # Save the filtered version so we never have to download 15MB again
                df.to_csv(_HYG_LOCAL_FILTERED, index=False)

                # 4. Create a persistent License/Attribution file in the data folder
                # This ensures anyone finding the CSV knows its origin and license.
                attribution_path = _DATA_DIR / "HYG_LICENSE.txt"
                with open(attribution_path, "w") as f:
                    f.write("DATASET ATTRIBUTION & LICENSE\n")
                    f.write("============================\n\n")
                    f.write("This directory contains a filtered subset of the HYG Database v4.2.\n")
                    f.write("Original Dataset: https://codeberg.org/astronexus/hyg\n")
                    f.write("Original Author: David Nash\n")
                    f.write("Modifications: Filtered for magnitude <= 6.5 and specific columns.\n\n")
                    f.write("License: This derivative work is licensed under CC BY-SA 4.0.\n")
                    f.write("https://creativecommons.org/licenses/by-sa/4.0/\n")
                    
                print(f"[Astro] Local cache created: {len(df)} naked-eye stars saved.")
                return df
            except Exception as e:
                print(f"[Astro] Critical Error downloading star catalog: {e}")
                raise
        else:
            # Load the already-filtered derivative work
            return pd.read_csv(_HYG_LOCAL_FILTERED)

    def _to_skyfield_time(self, dt: datetime):
        """Helper to ensure any datetime is converted to Skyfield-compatible UTC."""
        if dt.tzinfo is None:
            # If naive, assume UTC (or you could assume Local, but UTC is safer for astro)
            return self._ts.from_datetime(dt.replace(tzinfo=timezone.utc))
        return self._ts.from_datetime(dt.astimezone(timezone.utc))
    
    def get_stars(self, dt: datetime) -> list:
        """Vectorized calculation of star positions."""
        t = self._to_skyfield_time(dt) # Use the helper

            
        astrometric = self._observer.at(t).observe(self._star_objects)
        alt, az, _ = astrometric.apparent().altaz()

        # Map the results to our internal StarResult format
        # We prioritize 'proper' name, then Bayer/Flamsteed 'bf'
        names = self._star_df['proper'].values
        bfs   = self._star_df['bf'].values
        mags  = self._star_df['mag'].values
        cons  = self._star_df['con'].values

        results = []
        for i in range(len(mags)):
            # Human-readable name logic
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
        return results # 

    # ------------------------------------------------------------------
    # Standard Observers
    # ------------------------------------------------------------------

    def get_moon(self, dt: datetime) -> MoonResult:
        t = self._to_skyfield_time(dt)
        astrometric = self._observer.at(t).observe(self._eph['moon'])
        alt, az, _ = astrometric.apparent().altaz()
        phase_angle = almanac.moon_phase(self._eph, t)

        illumination = (1 + math.cos(math.radians(phase_angle.degrees))) / 2.0

        # Days into synodic month (new moon = 0, full = ~14.77, back to new = 29.53)
        SYNODIC_MONTH = 29.530588
        days_from_new = (phase_angle.degrees / 360.0) * SYNODIC_MONTH

        # Determine waxing vs waning by sampling one hour ahead
        t_ahead = self._to_skyfield_time(dt.replace(tzinfo=dt.tzinfo) if dt.tzinfo else dt)
        from datetime import timedelta as _td
        dt_ahead = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        dt_ahead = dt_ahead + _td(hours=1)
        t_ahead = self._to_skyfield_time(dt_ahead)
        phase_ahead = almanac.moon_phase(self._eph, t_ahead)
        illum_ahead = (1 + math.cos(math.radians(phase_ahead.degrees))) / 2.0
        waxing = illum_ahead > illumination

        return MoonResult(
            phase_angle=phase_angle.degrees,
            illumination=illumination,
            days_from_new=days_from_new,
            waxing=waxing,
            azimuth=az.degrees % 360,
            altitude=alt.degrees,
            above_horizon=alt.degrees > 0,
            magnitude_impact=0.0,
        )

    def get_planets(self, dt: datetime) -> list[tuple]:
        t = self._to_skyfield_time(dt) # Use the helper
        keys = ["mercury", "venus", "mars", "jupiter barycenter", "saturn barycenter"]
        names = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
        results = []
        for i, key in enumerate(keys):
            try:
                body = self._eph[key]
                astrometric = self._observer.at(t).observe(body)
                alt, az, _ = astrometric.apparent().altaz()
                mag = planetary_magnitude(astrometric.apparent())
                results.append((names[i], mag, az.degrees % 360, alt.degrees))
            except: continue
        return results # not returning our object

    def get_sun(self, dt: datetime) -> SunResult:
        """
        Return the Sun's full observational state at the given moment.
        This is the authoritative source for day/night and twilight logic.
        """
        t = self._to_skyfield_time(dt)
        astrometric = self._observer.at(t).observe(self._eph['sun'])
        alt, az, _ = astrometric.apparent().altaz()
        altitude = alt.degrees
        azimuth  = az.degrees % 360

        # Classify twilight phase
        if altitude >= 18.0:
            phase = TwilightPhase.DAY
        elif altitude >= 0.0:
            phase = TwilightPhase.CIVIL_TWILIGHT
        elif altitude >= -6.0:
            phase = TwilightPhase.NAUTICAL_TWILIGHT
        elif altitude >= -18.0:
            phase = TwilightPhase.ASTRO_TWILIGHT
        else:
            phase = TwilightPhase.NIGHT


        mag_impact = sun_magnitude_loss(altitude)

        return SunResult(
            azimuth=azimuth,
            altitude=altitude,
            above_horizon=altitude > 0.0,
            twilight_phase=phase,
            magnitude_impact=mag_impact,
        )

    def get_sun_altitude(self, dt: datetime) -> float:
        """Convenience accessor — returns just the altitude in degrees."""
        return self.get_sun(dt).altitude