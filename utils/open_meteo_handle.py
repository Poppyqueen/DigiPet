import math
import traceback
import openmeteo_requests
import requests_cache
from retry_requests import retry
import os

# Setup the Open-Meteo API client with cache and retry on error
os.makedirs(".cache", exist_ok=True)

cache_session = requests_cache.CachedSession(
    '.cache/openmeteo',
    backend='filesystem',
    expire_after=900,
    urls_expire_after={
    '*/elevation*': 2592000, # 30 days   
}
)

retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
_MARINE_URL  = "https://marine-api.open-meteo.com/v1/marine"

_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


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


def _api_call(client, url, params):
    """Wrapper around openmeteo API calls that preserves full error details."""
    try:
        return client.weather_api(url, params=params)
    except Exception as e:
        print("=" * 60)
        print(f"Open-Meteo API error calling: {url}")
        print(f"Params: {params}")
        print(f"Error: {e}")
        print("-" * 60)
        raise


class OpenMeteoLoc:
    def __init__(self, lat, long):
        self.lat  = lat
        self.long = long

        self._weather_params = {
            "latitude":  self.lat,
            "longitude": self.long,
            "current":[
                "relative_humidity_2m",  # [0]
                "apparent_temperature",  # [1]
                "is_day",                # [2]
                "wind_speed_10m",        #[3]
                "wind_direction_10m",    # [4]
                "precipitation",         # [5]
                "cloud_cover",           # [6]
                "cloud_cover_low",       # [7]
                "cloud_cover_mid",       # [8]
                "cloud_cover_high",      # [9]
                "visibility",            # [10]
                "dew_point_2m",          # [11]
                "wind_speed_120m",       # [12]
                "cape",                  # [13]
                "weather_code",          # [14]
                "snow_depth",            # [15]
                "snowfall",              # [16]
            ],
            "timezone": "auto",
        }

        self._marine_params = {
            "latitude":  self.lat,
            "longitude": self.long,
            "current": [
                "wave_height",             # [0]  m       — combined significant wave height
                "wave_period",             # [1]  s       — combined mean wave period
                "wave_direction",          # [2]  °       — combined mean wave direction (from)
                "wind_wave_height",        # [3]  m       — locally generated wind wave height
                "wind_wave_direction",     # [4]  °       — wind wave direction (from)
                "wind_wave_period",        # [5]  s       — wind wave period
                "swell_wave_height",       # [6]  m       — traveled swell height
                "swell_wave_direction",    # [7]  °       — swell direction (from)
                "swell_wave_period",       # [8]  s       — swell period (longer = traveled farther)
                "ocean_current_velocity",  # [9]  km/h    — surface current speed
                "sea_level_height_msl",    # [10] m       — tide state (approx, unreliable inland)
                "sea_surface_temperature", # [11] °C      — surface water temperature
            ],
        }

    def _format_value(self, value, unit: str, decimals: int = 2) -> str:
        """Helper to round values and append units, or return 'unavailable'."""
        if value is None:
            return "unavailable"
        return f"{round(value, decimals)} {unit}"

    # ------------------------------------------------------------------
    # Timezone
    # ------------------------------------------------------------------

    def get_timezone(self, lat=None, long=None) -> dict:
        params = self._weather_params
        if lat and long:
            params = {**self._weather_params, "latitude": lat, "longitude": long}

        response = _api_call(openmeteo, _WEATHER_URL, params)[0]
        return {
            "timezone":              response.Timezone(),
            "timezone_abbreviation": response.TimezoneAbbreviation(),
        }
    
    def get_elevation(self) -> float | None:
        """Fetch terrain elevation for the current coordinates."""
        try:
            response = retry_session.get(
                _ELEVATION_URL,
                params={"latitude": self.lat, "longitude": self.long}
            )
            response.raise_for_status()
            data = response.json()
            value = data["elevation"][0]
            return _safe(value)
        except Exception as e:
            print("=" * 60)
            print(f"Open-Meteo Elevation API error")
            print(f"Coords: ({self.lat}, {self.long})")
            print(f"Error: {e}")
            print("-" * 60)
            raise

    # ------------------------------------------------------------------
    # Weather
    # ------------------------------------------------------------------

    def get_structured_weather(self) -> dict:
        response = _api_call(openmeteo, _WEATHER_URL, self._weather_params)[0]
        current  = response.Current()

        # Safely fetch weather code so we can cast to int if it exists
        raw_weather_code = _safe(current.Variables(14).Value())
        weather_code = int(raw_weather_code) if raw_weather_code is not None else None

        return {
            "humidity":         _safe(current.Variables(0).Value()),
            "temperature":      _safe(current.Variables(1).Value()),
            "is_day":           current.Variables(2).Value() == 1,
            "wind_speed":       _safe(current.Variables(3).Value()),
            "wind_direction":   _safe(current.Variables(4).Value()),
            "precipitation":    _safe(current.Variables(5).Value()),
            "cloud_cover":      _safe(current.Variables(6).Value()),
            "cloud_cover_low":  _safe(current.Variables(7).Value()),
            "cloud_cover_mid":  _safe(current.Variables(8).Value()),
            "cloud_cover_high": _safe(current.Variables(9).Value()),
            "visibility":       _safe(current.Variables(10).Value()),
            "dew_point":        _safe(current.Variables(11).Value()),
            "wind_speed_120m":  _safe(current.Variables(12).Value()),
            "cape":             _safe(current.Variables(13).Value()),
            "weather_code":     weather_code,
            "snow_depth":       _safe(current.Variables(15).Value()),
            "snowfall":         _safe(current.Variables(16).Value()),
        }

    def get_full_weather(self) -> str:
        d = self.get_structured_weather()
        return (
            f"Current Weather Information:\n"
            f"Apparent temperature:  {self._format_value(d['temperature'], '°C')}\n"
            f"Dew point (2m):        {self._format_value(d['dew_point'], '°C')}\n"
            f"Relative humidity:     {self._format_value(d['humidity'], '%')}\n"
            f"Is it daytime?:        {d['is_day']}\n"
            f"Weather code:          {self._format_value(d['weather_code'], 'WMO')}\n"
            f"Visibility:            {self._format_value(d['visibility'], 'm')}\n"
            f"Wind speed (10m):      {self._format_value(d['wind_speed'], 'km/h')}\n"
            f"Wind direction (10m):  {self._format_value(d['wind_direction'], '°')}\n"
            f"Wind speed (120m):     {self._format_value(d['wind_speed_120m'], 'km/h')}\n"
            f"Precipitation:         {self._format_value(d['precipitation'], 'mm')}\n"
            f"Snowfall:              {self._format_value(d['snowfall'], 'cm')}\n"
            f"Snow depth:            {self._format_value(d['snow_depth'], 'm')}\n"
            f"Cloud cover (total):   {self._format_value(d['cloud_cover'], '%')}\n"
            f"Cloud cover (low):     {self._format_value(d['cloud_cover_low'], '%')}\n"
            f"Cloud cover (mid):     {self._format_value(d['cloud_cover_mid'], '%')}\n"
            f"Cloud cover (high):    {self._format_value(d['cloud_cover_high'], '%')}\n"
            f"CAPE:                  {self._format_value(d['cape'], 'J/kg')}\n"
        )

    # ------------------------------------------------------------------
    # Marine
    # ------------------------------------------------------------------

    def get_structured_marine(self) -> dict:
        response = _api_call(openmeteo, _MARINE_URL, self._marine_params)[0]
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
        d = self.get_structured_marine()
        return (
            f"Current Marine Weather:\n"
            f"Wave height:               {self._format_value(d['wave_height'], 'm')}\n"
            f"Wave period:               {self._format_value(d['wave_period'], 's')}\n"
            f"Wave direction:            {self._format_value(d['wave_direction'], '°')}\n"
            f"Wind wave height:          {self._format_value(d['wind_wave_height'], 'm')}\n"
            f"Wind wave direction:       {self._format_value(d['wind_wave_direction'], '°')}\n"
            f"Wind wave period:          {self._format_value(d['wind_wave_period'], 's')}\n"
            f"Swell wave height:         {self._format_value(d['swell_wave_height'], 'm')}\n"
            f"Swell wave direction:      {self._format_value(d['swell_wave_direction'], '°')}\n"
            f"Swell wave period:         {self._format_value(d['swell_wave_period'], 's')}\n"
            f"Ocean current velocity:    {self._format_value(d['ocean_current_velocity'], 'km/h')}\n"
            f"Sea level height (MSL):    {self._format_value(d['sea_level_height_msl'], 'm')}\n"
            f"Sea surface temperature:   {self._format_value(d['sea_surface_temperature'], '°C')}\n"
        )