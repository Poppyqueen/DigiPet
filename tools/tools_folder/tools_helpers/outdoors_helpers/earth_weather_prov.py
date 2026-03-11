from __future__ import annotations
from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider


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
        message = "\n".join([
            "From where you stand, you can catch an incomplete glimplse of the outside world through an opening around you,",
            f"Is day: {structure_weather["is_day"]}",
            f"Precipitation: {structure_weather["precipitation"]}"
        ])
        return message

    def get_full_perception(self) -> str:
        """
        Complete weather perception.
        Used when the agent actively looks through an accessible aperture or
        is standing in an outdoors_area room — mirrors the original
        outdoors_perception() output.
        """
        return self.open_meteo.get_full_weather()