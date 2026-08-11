from __future__ import annotations
from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider

from .lunar_sim import LunarSkySimulator, render_snapshot, render_limited


class LunarDomeViewProvider(OutdoorsProvider):
    """
    Outdoors provider for a domed lunar habitat's exterior view.

    No weather dependency — the Moon has none. Sun/Earth geometry is real
    (skyfield-backed where it matters: illumination fraction, synodic
    timing); libration and site-local look angles use a labeled, physically
    grounded approximation (see lunar_sim/ephemeris.py for the split).

    outdoors_type identifier: "lunar-dome-view"
    """

    outdoors_type = "lunar-dome-view"
    tick_every = 1

    def __init__(self, config, lat, lon):
        """
        lat, lon must be SELENOGRAPHIC coordinates (the Moon's own lat/lon
        grid), not Earth coordinates. Convention (IAU):
          - latitude:  -90..90, equator = 0, same sense as Earth.
          - longitude: -180..180, EAST-positive, with 0deg defined as the
            *mean* sub-Earth point (near-side center) and +-180deg the
            far-side center. The true sub-Earth point wobbles a few degrees
            around (0,0) due to libration -- see ephemeris.libration_offset,
            which already accounts for this. (0,0) itself is a fixed
            reference by definition, not an approximation.

        """
        lat = float(lat)
        lon = float(lon)
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"LunarDomeViewProvider: lat {lat} out of range [-90, 90] (selenographic)")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"LunarDomeViewProvider: lon {lon} out of range [-180, 180] (selenographic)")

        self.lat = lat
        self.lon = lon

        pet_dna = config.get_config("AI", "pet_dna")
        clean_dna = "".join(char for char in pet_dna if char.isdigit())
        seed = int(clean_dna)

        self.sim = LunarSkySimulator(lat=self.lat, lon=self.lon, noise_seed=seed)

    def get_limited_perception(self) -> tuple[str, str | None]:
        snap = self.sim.snapshot()
        return render_limited(snap), None

    def get_full_perception(self) -> tuple[str, str | None, tuple[bytes, int] | None]:
        snap = self.sim.snapshot()
        return render_snapshot(snap), None, None

    def tick(self) -> None:
        self.sim.tick()