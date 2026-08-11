# outdoors_type_definitions.py

# Outdoors types live here.
# Each string is an outdoors_type identifier that can appear as a value in:
#   - fenestration_aperture item data  (flat key: "outdoors_type")
#   - outdoors_area room extra_data    (flat key: "outdoors_type")
#
# To add a new outdoors type:
#   1. Add the string here.
#   2. Create a provider class in tools/tools_folder/outdoors/providers/
#      that sets outdoors_type = "<your_string>" and implements both
#      get_limited_perception() and get_full_perception().
#   3. Register the provider in OutdoorsPerception.__init__().
#
# The Literal type and name string below are consumed by the schema validator
# the same way TVType is built from TV_TYPE_CHANNELS.

OUTDOORS_TYPES: list[str] = [
    "earth-weather",
    "ocean-views",
    "xeno-canto",
    "earth-astro-views",
    "walled-window",
    "lunar-dome-view"
    # "space-traveler",   # future: space travel data
    # "world-camera",     # future: live public camera feeds → text perception
]