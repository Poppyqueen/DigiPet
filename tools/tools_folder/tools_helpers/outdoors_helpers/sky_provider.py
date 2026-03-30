from __future__ import annotations
from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider

from .sky_sim import NightSkySimulator, render_snapshot, render_limited
from .sky_sim.types import SkySnapshot, VisibilityState, TwilightPhase, EclipseType, EclipsePhase

class EarthAstroViews(OutdoorsProvider):
    """
    Outdoors provider for real-world astro sky.

    outdoors_type identifier:"earth-astro-views"
    """

    outdoors_type = "earth-astro-views"

    def __init__(self, open_meteo, config, lat, lon):
        self.open_meteo = open_meteo

        self.lat  = float(lat)
        self.lon = float(lon)

        print(f"DEBUG INTEGRATION, LAT TYPE {type(self.lat)}, LON TYPE {type(self.lon)}")

        self.pet_dna = config.get_config("AI", "pet_dna")
        # Remove colons and dots, then convert to int
        clean_dna = "".join(char for char in self.pet_dna if char.isdigit())
        dna_int = int(clean_dna) # Use this for a seed in the noise

        self._tick_interval_minutes: float = 15.0  # default, overridden below


        self.bortle_class = int(config.get_config("outdoors_perception", "astro_bortle_level"))

        if not self.bortle_class:
            default = 4
            print(f"ASTRO VIEWS ALERT! NO BORTLE CLASS CONFIGURED, USING DEFAULT {default}")
            self.bortle_class = default
        else:
            print(f"SKY SIM, Found config Bortle {self.bortle_class}")


        self.sim = NightSkySimulator(
        lat=self.lat, lon=self.lon, 
        weather_provider=self.open_meteo, 

        bortle_class=self.bortle_class,

        noise_seed=dna_int,
        elevation_m=self.open_meteo.get_elevation()
    )
        


    def get_limited_perception(self) -> str:
        snap = self.sim.snapshot()
        return render_limited(snap), None


    def get_full_perception(self) -> tuple[str, str | None, bool]:
        snap = self.sim.snapshot()
        rendered = render_snapshot(snap)
        return rendered, None, None
    
    def set_tick_interval_minutes(self, minutes: float) -> None:
        self._tick_interval_minutes = minutes

    def tick(self) -> None:
        self.sim.tick(minutes=self._tick_interval_minutes)