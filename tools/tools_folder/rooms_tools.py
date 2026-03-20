# rooms_tools.py

# State manager is being passed into this


# Here we cointain simple tools for each room, mostly based on
# flavor text

# Some use utils to interact with some simple APIs or data structures.

# the state manager has access to inventory and wellness stats access

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager # just for typing


import asyncio
import math

from tools.tools_folder.tools_helpers import random_object # outdated

from tools.tools_folder.tools_helpers.ai_cook import cook

import random

from utils.loc_datetime import datetime


from utils.misc import check_one_in


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



class room_garden:
    def __init__(self, state_manager, signal=None, open_meteo=None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state_manager : InventoryHouseManager = state_manager
        self.open_meteo = open_meteo
        #print("Garden initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    def lay_down(self):
        edit=5
        self.state_manager.adjust_stat("energy", edit)
        message=f"You lay down in the middle of the garden. The fresh ambience makes you feel revilatized, you recover {edit} energy points."
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/lying_icon.png"}) # Example icon
        # ------------------------
        return message


    def dig_hole(self):
        edit = -15
        self.state_manager.adjust_stat("energy", edit)
        self.state_manager.adjust_stat("hydration", edit)
        self.state_manager.adjust_stat("fullness", edit)
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/dig_icon.png"})

        message = (
            f"You dig around and found nothing. All your stats have been lowered by {abs(edit)}. "
            "It at least was good exercise."
        )

        if check_one_in(50):
            found_item = random_object.load_and_get_random_item("found_items/garden_found_items_data.json")
            result = self.state_manager.create_item("inventory", None, found_item)
            if result.success:
                message = (
                    f"While digging in the garden you found something! "
                    f"It is a {found_item['name']}! {result.message} "
                    f"All your stats have been lowered by {abs(edit)} for digging around."
                )
            else:
                message = (
                    f"While digging you found something, but couldn't pick it up. {result.error} "
                    f"All your stats have been lowered by {abs(edit)}."
                )
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/dig_icon.png", "popup_type": 2})

        return message


# Define the main handler class
class main_tools_handle:
    def __init__(self, state_manager, signal=None, memory_manager=None, config_manager=None, open_meteo=None):
        self.memory=memory_manager

        # wikipedia_enabled = config_manager.get_config('Tools', "enable_wikipedia")


        # print(f"DEBUG: WIKPEDIA enabled (config): {wikipedia_enabled}") # TODO: initialization and loading shouldn't be hiding here, move to tool_registry, conditional loading

        # self.wiki=None
        # if wikipedia_enabled:
        #     try: 
        #         from tools.tools_folder.tools_helpers.services.wiki_handle import Wikipedia_handle
        #         self.wiki=Wikipedia_handle(self.memory)
        #     except Exception as e:
        #         print(f"Error initializing Wikipedia_handle: {e}")

        print("Main tools handler initialized.")
        self._signal_callback=signal # Store the main signal callback here
        # Store the state_manager reference
        self.state_manager : InventoryHouseManager = state_manager

        self.open_meteo = open_meteo


        self.garden = room_garden(self.state_manager, self._signal_callback, self.open_meteo)


    # You already have _send_signal in main_tools_handle, but it's not currently used
    # by the room methods. The approach above adds it *to* the room instances.
    # If you wanted main_tools_handle itself to send signals, you'd use this method.
    # For signals originating *from* room actions, adding the helper to the rooms is better.
    # You can keep this one if main_tools_handle might signal independently later.
    # def _send_signal(self, signal_data):
    #     """Helper method to send signals using the registered callback."""
    #     if self._signal_callback:
    #         print(f"main_tools_handle signaling: {signal_data}") # Optional: uncomment for debug
    #         try:
    #             self._signal_callback(signal_data)
    #         except Exception as e:
    #             print(f"Error sending signal from main_tools_handle: {e}")
    #     else:
    #         print(f"main_tools_handle attempted to signal, but no callback registered: {signal_data}") # Optional: uncomment for debug
    #         pass # Silently fail if no callback is registered, or log loudly