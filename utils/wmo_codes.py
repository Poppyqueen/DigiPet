from enum import Enum

class WMOWeatherCode(Enum):
    """
    Comprehensive Enum for WMO Weather interpretation codes (WW).
    """
    # Clear sky
    CLEAR_SKY = 0

    # Partly cloudy
    MAINLY_CLEAR = 1
    PARTLY_CLOUDY = 2
    OVERCAST = 3

    # Fog
    FOG = 45
    DEPOSITING_RIME_FOG = 48

    # Drizzle
    DRIZZLE_LIGHT = 51
    DRIZZLE_MODERATE = 53
    DRIZZLE_DENSE = 55

    # Freezing Drizzle
    FREEZING_DRIZZLE_LIGHT = 56
    FREEZING_DRIZZLE_DENSE = 57

    # Rain
    RAIN_SLIGHT = 61
    RAIN_MODERATE = 63
    RAIN_HEAVY = 65

    # Freezing Rain
    FREEZING_RAIN_LIGHT = 66
    FREEZING_RAIN_HEAVY = 67

    # Snow fall
    SNOW_FALL_SLIGHT = 71
    SNOW_FALL_MODERATE = 73
    SNOW_FALL_HEAVY = 75

    # Snow grains
    SNOW_GRAINS = 77

    # Rain showers
    RAIN_SHOWERS_SLIGHT = 80
    RAIN_SHOWERS_MODERATE = 81
    RAIN_SHOWERS_VIOLENT = 82

    # Snow showers
    SNOW_SHOWERS_SLIGHT = 85
    SNOW_SHOWERS_HEAVY = 86

    # Thunderstorm
    THUNDERSTORM = 95
    THUNDERSTORM_HAIL_SLIGHT = 96
    THUNDERSTORM_HAIL_HEAVY = 99

    @classmethod
    def from_code(cls, code: int):
        """Returns the Enum member for a given integer code."""
        try:
            return cls(code)
        except ValueError:
            return None

    def __str__(self):
        """Returns a formatted description of the weather code."""
        # Replace underscores with spaces and capitalize words
        return self.name.replace("_", " ").title()
