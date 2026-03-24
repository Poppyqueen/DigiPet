# python -m utils.test_marine
from utils.open_meteo_handle import OpenMeteoLoc
import time
from utils.loc_datetime import CoordinateDateTime




SLEEP_RATE = 2.5 # seconds

terrible_tilly_lat = "45.9375"
terrible_tilly_long = "-124.0189"

anacapa_island_lat = "34.0167"
anacapa_island_long = "-119.45"

boston_light_lat = "42.361145"
boston_light_long = "-71.006139"

cape_spencer_lat = "58.19722"
cape_spencer_long = "-136.63936"

locations_map = {
    "Terrible Tilly": (terrible_tilly_lat, terrible_tilly_long),
    # "Anacapa Island": (anacapa_island_lat, anacapa_island_long),
    # "Boston Light": (boston_light_lat, boston_light_long),
    # "Cape Spencer": (cape_spencer_lat, cape_spencer_long),
}

for location in locations_map:
    provider = OpenMeteoLoc(lat=locations_map[location][0],long=locations_map[location][1])
    coordinate_datetime = CoordinateDateTime(provider.lat, provider.long)
    now = coordinate_datetime.now()


    print(f"{location}:\n Current time: {now}\n {provider.get_full_marine()}")
    print("\n")
    time.sleep(SLEEP_RATE)
    # print(f"{location}:\n {provider.get_structured_marine()}")
    # print("\n")


# provider = OpenMeteoLoc(lat=cape_spencer_lat,long=cape_spencer_long)

# print(provider.get_full_marine())