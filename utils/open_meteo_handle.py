import math
import openmeteo_requests
import requests_cache
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
# Cache expires after 900 seconds (15 minutes)
cache_session = requests_cache.CachedSession('.cache', expire_after=900)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
_MARINE_URL  = "https://marine-api.open-meteo.com/v1/marine"


def _safe(value) -> float | None:
    """Return None if value is NaN, otherwise return the value as-is."""
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


class OpenMeteoLoc:
    def __init__(self, lat, long):
        self.lat  = lat
        self.long = long

        self._weather_params = {
            "latitude":  self.lat,
            "longitude": self.long,
            "current": [
                "relative_humidity_2m",  # [0]
                "apparent_temperature",  # [1]
                "is_day",                # [2]
                "wind_speed_10m",        # [3]
                "wind_direction_10m",    # [4]
                "precipitation",         # [5]
                "cloud_cover",           # [6]
            ],
            "timezone": "auto",
        }

        self._marine_params = {
            "latitude":  self.lat,
            "longitude": self.long,
            "current": [
                "wave_height",          # [0]  m       — combined significant wave height
                "wave_period",          # [1]  s       — combined mean wave period
                "wave_direction",       # [2]  °       — combined mean wave direction (from)
                "wind_wave_height",     # [3]  m       — locally generated wind wave height
                "wind_wave_direction",  # [4]  °       — wind wave direction (from)
                "wind_wave_period",     # [5]  s       — wind wave period
                "swell_wave_height",    # [6]  m       — traveled swell height
                "swell_wave_direction", # [7]  °       — swell direction (from)
                "swell_wave_period",    # [8]  s       — swell period (longer = traveled farther)
                "ocean_current_velocity",  # [9]  km/h — surface current speed
                "sea_level_height_msl",    # [10] m    — tide state (approx, unreliable inland)
                "sea_surface_temperature", # [11] °C   — surface water temperature
            ],
        }

    # ------------------------------------------------------------------
    # Timezone
    # ------------------------------------------------------------------

    def get_timezone(self, lat=None, long=None) -> dict:
        """Return timezone identifier and abbreviation for the location."""
        params = self._weather_params
        if lat and long:
            params = {**self._weather_params, "latitude": lat, "longitude": long}

        response = openmeteo.weather_api(_WEATHER_URL, params=params)[0]
        return {
            "timezone":              response.Timezone(),
            "timezone_abbreviation": response.TimezoneAbbreviation(),
        }

    # ------------------------------------------------------------------
    # Weather
    # ------------------------------------------------------------------

    def get_structured_weather(self) -> dict:
        """Return current weather conditions as a typed dict."""
        response = openmeteo.weather_api(_WEATHER_URL, params=self._weather_params)[0]
        current  = response.Current()

        return {
            "humidity":       current.Variables(0).Value(),   # %
            "temperature":    current.Variables(1).Value(),   # °C apparent
            "is_day":         "True" if current.Variables(2).Value() == 1 else "False",
            "wind_speed":     current.Variables(3).Value(),   # km/h
            "wind_direction": current.Variables(4).Value(),   # °
            "precipitation":  current.Variables(5).Value(),   # mm
            "cloud_cover":    current.Variables(6).Value(),   # %
        }

    def get_full_weather(self) -> str:
        """Return current weather conditions as a formatted string."""
        d = self.get_structured_weather()
        return (
            f"Current Weather Information:"
            f"Current apparent temperature:  {d['temperature']}°C\n"
            f"Current relative humidity:     {d['humidity']}%\n"
            f"Is it daytime?:                {d['is_day']}\n"
            f"Current wind speed (10m):      {d['wind_speed']} km/h\n"
            f"Current wind direction (10m):  {d['wind_direction']}°\n"
            f"Current precipitation:         {d['precipitation']} mm\n"
            f"Current cloud cover:           {d['cloud_cover']}%\n"
        )

    # ------------------------------------------------------------------
    # Marine
    # ------------------------------------------------------------------

    def get_structured_marine(self) -> dict:
        """
        Return current marine conditions as a typed dict.
        Values that are unavailable from the model are returned as None.

        Units
        -----
        wave heights          : metres
        wave periods          : seconds
        wave directions       : degrees (direction the waves are coming FROM)
                                0° = from north, 90° = from east
        ocean_current_velocity: km/h
        sea_level_height_msl  : metres above global mean sea level (tide approx)
        sea_surface_temperature: °C
        """
        response = openmeteo.weather_api(_MARINE_URL, params=self._marine_params)[0]
        current  = response.Current()

        return {
            "wave_height":              _safe(current.Variables(0).Value()),
            "wave_period":              _safe(current.Variables(1).Value()),
            "wave_direction":           _safe(current.Variables(2).Value()),
            "wind_wave_height":         _safe(current.Variables(3).Value()),
            "wind_wave_direction":      _safe(current.Variables(4).Value()),
            "wind_wave_period":         _safe(current.Variables(5).Value()),
            "swell_wave_height":        _safe(current.Variables(6).Value()),
            "swell_wave_direction":     _safe(current.Variables(7).Value()),
            "swell_wave_period":        _safe(current.Variables(8).Value()),
            "ocean_current_velocity":   _safe(current.Variables(9).Value()),
            "sea_level_height_msl":     _safe(current.Variables(10).Value()),
            "sea_surface_temperature":  _safe(current.Variables(11).Value()),
        }

    def get_full_marine(self) -> str:
        """Return current marine conditions as a formatted string."""
        d = self.get_structured_marine()

        def fmt(value, unit: str, decimals: int = 2) -> str:
            return f"{round(value, decimals)} {unit}" if value is not None else "unavailable"

        return (
            f"Current Marine Weather:"
            f"Wave height:               {fmt(d['wave_height'], 'm')}\n"
            f"Wave period:               {fmt(d['wave_period'], 's')}\n"
            f"Wave direction:            {fmt(d['wave_direction'], '°')}\n"
            f"Wind wave height:          {fmt(d['wind_wave_height'], 'm')}\n"
            f"Wind wave direction:       {fmt(d['wind_wave_direction'], '°')}\n"
            f"Wind wave period:          {fmt(d['wind_wave_period'], 's')}\n"
            f"Swell wave height:         {fmt(d['swell_wave_height'], 'm')}\n"
            f"Swell wave direction:      {fmt(d['swell_wave_direction'], '°')}\n"
            f"Swell wave period:         {fmt(d['swell_wave_period'], 's')}\n"
            f"Ocean current velocity:    {fmt(d['ocean_current_velocity'], 'km/h')}\n"
            f"Sea level height:          {fmt(d['sea_level_height_msl'], 'm')}\n"
            f"Sea surface temperature:   {fmt(d['sea_surface_temperature'], '°C')}\n"
        )


# Thanks to open-meteo, check docs here:
# https://open-meteo.com
# https://open-meteo.com/en/docs
# https://open-meteo.com/en/docs/marine-weather-api