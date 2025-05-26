import openmeteo_requests
import requests_cache
from retry_requests import retry
import os
from dotenv import load_dotenv
import sys

from utils.time_manager import get_time_tag_from_now

load_dotenv()

my_latitude = os.getenv("LATITUDE")
my_longitude = os.getenv("LONGITUDE")


if not my_longitude or not my_latitude:
    sys.exit("Missing longitude and latitude on .env file. Necessary for weather integration.")

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=900)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Make sure all required weather variables are listed here
# The order of variables in 'current' must match how they are extracted
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": my_latitude,
    "longitude": my_longitude,
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

def get_structured_weather():
    time_tag=get_time_tag_from_now()
    responses = openmeteo.weather_api(url, params=params)
    
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

def get_full_weather():
    
    weather_data = get_structured_weather()
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