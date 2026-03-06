
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager # just for typing

class OutdoorsPerception: # this could follow the pattern of the TV that allows for TV to have different channels, it would check current accessible apertures from the items, which the TV does, it would have to extend that idea to current room type? and... room type... type ??? (you would have to just track outdoors_area room types, and if we are standing on it, it should have what kind of outdoor it is, this is a bit better than it being a pet state, but not that much) and determine what the 'outside' is with that... maybe make the outside type a value for the main state, state manager, like currency is
    def __init__(self, state_manager, signal=None, open_meteo = None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state_manager : InventoryHouseManager = state_manager

        self.open_meteo = open_meteo


    # --- Helper method to be added to each room class ---
    def _send_signal(self, signal_data):
        """Helper method to send signals using the registered callback."""
        if self._signal_callback:
            # print(f"{self.__class__.__name__} signaling: {signal_data}") # Optional: uncomment for debug
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from {self.__class__.__name__}: {e}")
        else:
            # print(f"{self.__class__.__name__} attempted to signal, but no callback registered: {signal_data}") # Optional: uncomment for debug
            pass # Silently fail if no callback is registered, or log loudly
    # ------------------------------------------------------

    def outdoors_perception(self): # Full perception of the weather, used for environment awareness in outdoors areas, and as a helper to look_through_aperture
        return self.open_meteo.get_full_weather()

    def window_perception(self): # Limited perception of the weather, it revels rain and day conditions, used for environment awareness affordance when around a Fenêtre and helper to look_through_aperture
        structure_weather = self.open_meteo.get_structured_weather()
        message = "\n".join([
            "From where you stand, you can catch an incomplete glimplse of the outside world through an opening around you,",
            f"Is day: {structure_weather["is_day"]}",
            f"Precipitation: {structure_weather["precipitation"]}"
            ]
        )
        return message

    def look_through_aperture(self, aperture_id):
        """
        Returns a string with the current weather information
        delegated to Open Meteo handle
        """
        # --- Add signal call ---
        item_object = self.state_manager.find_item(item_id=aperture_id, required_type="fenestration_aperture", required_location="room") # we need it to be a 'fenestration_aperture' to look through
        if not item_object.success:
            return item_object.error

        # Safe to access item_data only after success check
        item_details = item_object.item_data
        # Nothing to do about the window details.
        descriptions = item_details.get("descriptions", [])

        # one could add a window type that instead of returning weather data retuns for example astronomical information, or others

        accessibility_flag = item_details.get("accessible", True) # Determines if such apperture is accessible for walking close to it

        weather_info = "" # Decide what kind of perception the agent will get based on accessibility
        accessibility_message = "" # Flavor text for the agent
        if accessibility_flag:
            weather_info = self.outdoors_perception() # Agent can call the window to look at it, it gets full perception of the outdoors
            accessibility_message = "You walk right besides the window, standing there it allows you to see everything outside, with clarity"
            # could add fun stuff here
        else:
            weather_info = self.window_perception() # Agent can't get close to such aperture (a glass ceiling, or raised window), it gets simpler perception of the weather
            accessibility_message = "That aperture is not in a place you can walk to, you focus all your attention into it for a second,"

        message = "\n".join([
            "You get as close as you can to the aperture in the room;",
            "\n".join(accessibility_message),
            "\n".join(descriptions),
            f"As you peer outwards, you notice the weather with absolute precision:",
            f"{weather_info}"
        ])

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/window_icon.png"})

        return message