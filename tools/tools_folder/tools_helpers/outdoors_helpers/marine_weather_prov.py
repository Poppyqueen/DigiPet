from __future__ import annotations
from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider


class MarineWeatherProvider(OutdoorsProvider):
    """
    Outdoors provider for real-world marine weather data.

    Wraps the existing open_meteo service and uses their marine endpoint.

    outdoors_type identifier: "ocean-views"
    """

    outdoors_type = "ocean-views"

    def __init__(self, open_meteo):
        self.open_meteo = open_meteo

    def get_limited_perception(self) -> str:
        """
        Short ambient glimpse of weather conditions.
        Used when the agent is in a room with a nearby window but has not
        actively looked through it.
        Reveals only wave_height and wave_period
        """
        structure_marine = self.open_meteo.get_structured_marine()
        message = "\n".join([
            "The sea around your location makes itself known with its roar and swell breaking through your walls and reaching from your windows and apertures around you; you can notice a few faint details on its qualities:",
            f"Wave height: {structure_marine["wave_height"]:.2f} m",
            f"Wave period: {structure_marine["wave_period"]:.2f} s",
        ])
        return message, None

    def get_full_perception(self) -> tuple[str, str | None, bool]:
        return self.open_meteo.get_full_marine(), None, None