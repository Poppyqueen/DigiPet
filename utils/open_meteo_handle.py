import os
import sys

# --- TEMPORARY FIX FOR DIRECT EXECUTION ---
# This block allows the script to find the 'utils' package
# when run directly from its current location.
# Assuming 'utils' is in the parent directory of this script's location
# This adds the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
# -------------------------------------------



import openmeteo_requests
import requests_cache
from retry_requests import retry
import os
import sys

from utils.time_manager import get_time_tag_from_now

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=900)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


class OpenMeteoLoc:
    def __init__(self, long, lat):
        self.long=long
        self.lat=lat

        self.url = "https://api.open-meteo.com/v1/forecast"


        self.params = {
            "latitude": self.lat,
            "longitude": self.long,
            "current": [
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "wind_speed_10m",
                "precipitation",
                "cloud_cover"
            ],
            "timezone": "auto"
        }


    def get_timezone(self,lat=None, long=None):
        """
        Extracts the timezone information from the weather API response.
        """
        if lat and long:
            params = {
                "latitude": lat,
                "longitude": long,
                "current": [
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "is_day",
                    "wind_speed_10m",
                    "precipitation",
                    "cloud_cover"
                ],
                "timezone": "auto"
            }
        timezone_params={}
        if lat and long: 
            timezone_params=params
        else:
            timezone_params=self.params
        responses = openmeteo.weather_api(self.url, params=timezone_params)
        response = responses[0]


        timezone = response.Timezone()

        time_zone_data = {
            "timezone": timezone,
            "timezone_abbreviation": response.TimezoneAbbreviation()
        }
        return time_zone_data

    def get_structured_weather(self,now):
        time_tag=get_time_tag_from_now(now)
        responses = openmeteo.weather_api(self.url, params=self.params)
        
        # Process the first location in the response
        response = responses[0]
        current = response.Current()
        
        current_relative_humidity_2m = current.Variables(0).Value()
        current_apparent_temperature = current.Variables(1).Value()
        current_is_day = current.Variables(2).Value()
        current_wind_speed_10m = current.Variables(3).Value()
        current_precipitation = current.Variables(4).Value()
        current_cloud_cover = current.Variables(5).Value()
        
        is_day = "True" if current_is_day == 1 else "False"

        weather_data={
            "time":time_tag,
            "current humidity":current_relative_humidity_2m,
            "current temperature": current_apparent_temperature,
            "is_day": is_day,
            "wind_speed": current_wind_speed_10m,
            "precipitation": current_precipitation,
            "cloud_cover": current_cloud_cover
        }

        return weather_data

    def get_full_weather(self, now):

        weather_data = self.get_structured_weather(now)
        time_tag = weather_data["time"]
        current_apparent_temperature = weather_data["current temperature"]
        current_relative_humidity_2m = weather_data["current humidity"]
        is_day = weather_data["is_day"]
        current_wind_speed_10m = weather_data["wind_speed"]
        current_precipitation = weather_data["precipitation"]
        current_cloud_cover = weather_data["cloud_cover"]

        stringed_response = f"""
    Current apparent temperature: {current_apparent_temperature}°C
    Current relative humidity (2m): {current_relative_humidity_2m}%
    Is it daytime?: {is_day}, 
    It is: {time_tag}
    Current wind speed (10m): {current_wind_speed_10m} m/s
    Current precipitation: {current_precipitation} mm
    Current cloud cover: {current_cloud_cover}%
    """
        return stringed_response

