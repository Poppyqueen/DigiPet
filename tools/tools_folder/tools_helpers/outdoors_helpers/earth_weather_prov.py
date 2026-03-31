from __future__ import annotations
from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider

from utils.wmo_codes import WMOWeatherCode

class EarthWeatherProvider(OutdoorsProvider):
    """
    Outdoors provider for real-world Earth weather data.

    Wraps the existing open_meteo service. This is the default provider —
    any item or room without an explicit outdoors_type list will fall back
    to this one.

    outdoors_type identifier: "earth-weather"
    """

    outdoors_type = "earth-weather"

    def __init__(self, open_meteo):
        self.open_meteo = open_meteo

    def get_limited_perception(self) -> str:
        """
        Short ambient glimpse of weather conditions.
        Used when the agent is in a room with a nearby window but has not
        actively looked through it.
        Reveals only day/night state and precipitation — mirrors the original
        window_perception() output.
        """
        structure_weather = self.open_meteo.get_structured_weather()
        messages =[
            "From where you stand, you can catch an incomplete glimplse of the outside world through an opening around you,",
            f"Is day: {structure_weather["is_day"]}",
            f"Cloud cover: {structure_weather["cloud_cover"]:.2f}%",
            f"Precipitation: {structure_weather["precipitation"]:.2f} mm" if structure_weather["precipitation"] > 0 else "",
            f"Snowfall: {structure_weather["snowfall"]:.2f} cm" if structure_weather["snowfall"] > 0 else "",
            f"Most severe weather event: {WMOWeatherCode.from_code(int(structure_weather["weather_code"]))}"
        ]
        clean = "\n".join([s for s in messages if s.strip()])

        return clean, None

    def get_full_perception(self) -> tuple[str, str | None, bool]:
        return self.open_meteo.get_full_weather(), None, None