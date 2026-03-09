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

from inventory_items.items_provider.item_store import ItemStore


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

# class room_kitchen:
#     def __init__(self, state_manager, signal=None, config_manager=None):
#         self._signal_callback=signal

#         # Store the state_manager reference
#         self.state_manager : InventoryHouseManager = state_manager
#         self.cook = cook(config_manager)
#         #print("Kitchen initialized.")

#     # Add the helper method
#     _send_signal = _send_signal # Assign the common helper function (?)

#     def drink_water(self):
#         print("Drinking water...")
#         # You can now access the state_manager if needed
#         edit=10
#         self.state_manager.adjust_stat("hydration", edit)
#         message=f"Drank some water from the kitchen faucet! Got {edit} hydration points."
#         # --- Add signal call ---
#         self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"})
#         # ------------------------
#         return message

#     def _scale_stats(self, stats_edit, amount):
#         if not stats_edit:
#             return {}
#         return {k: round(v * amount, 2) for k, v in stats_edit.items()}
            

#     def prepare_food(self, process, items_list):
#         if not items_list:
#             return "Error: No items specified for preparation."

#         consumables, tools, errors = [], [], []

#         for entry in items_list:
#             item_id = entry.get("item_id")
#             amount = entry.get("amount", 1)

#             result = self.state_manager.find_item(item_id, required_location="inventory")
#             if not result.success:
#                 errors.append(result.error)
#                 continue

#             item = result.item_data
#             types = item.get("type", [])

#             if "consumable" in types:
#                 uses = item.get("consume_uses_left")
#                 if uses is not None and amount > uses:
#                     errors.append(f"'{item['name']}' only has {uses} use(s) left, {amount} requested.")
#                     continue
#                 consumables.append((item, amount))

#             elif "tool" in types:
#                 tools.append(item)

#             else:
#                 errors.append(f"'{item.get('name')}' is not a consumable or tool.")

#         if errors:
#             return "Preparation failed: " + "; ".join(errors)

#         ingredients = [
#             {**{k: item[k] for k in ("name", "descriptions", "effects", "stats_edit") if k in item},
#             "amount": amount,
#             "stats_edit": self._scale_stats(item.get("stats_edit"), amount)}
#             for item, amount in consumables
#         ] + [
#             {**{k: item[k] for k in ("name", "descriptions", "effects", "stats_edit") if k in item},
#             "stats_edit": self._scale_stats(item.get("stats_edit"), 1)}
#             for item in tools
#         ]

#         generated = self.cook.prepare_food(ingredients, process)
#         if not generated:
#             return "You mime and begin preparing food, your plan was perfect, however when you start, you trip up the sequence of actions!... You just trace back your steps and start right from the beginning."

#         for item_data in generated:
#             self.state_manager.create_item("inventory", None, item_data)

#         for item, amount in consumables:
#             item_id = int(item["id"])
#             uses = item.get("consume_uses_left")
#             if uses is None or uses - amount <= 0:
#                 self.state_manager.remove_item(item_id)
#             else:
#                 self.state_manager.set_item_attribute(item_id, "consume_uses_left", uses - amount)

#         created_names = [i.get("name", "item") for i in generated]
#         self._send_signal({
#             "type": "show_icon_popup",
#             "icon_path": "style/images/action_icons/plate_icon.png",
#             "popup_type": 2,
#         })
#         return f"Preparation successful! Created: {', '.join(created_names)}."



# class room_bathroom:
#     def __init__(self, state_manager, signal=None):
#         self._signal_callback=signal
#         # Store the state_manager reference
#         self.state_manager : InventoryHouseManager = state_manager
#         #print("Bathroom initialized.")

#     # Add the helper method
#     _send_signal = _send_signal # Assign the common helper function


#     # Make methods instance methods by adding 'self'
#     def drink_water(self):
#         print("Drinking water...")
#         # You can now access the state_manager if needed
#         edit=10
#         self.state_manager.adjust_stat("hydration", edit)
#         message=f"Drank some water from the faucet! Got {edit} hydration points."
#         # --- Add signal call ---
#         self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"})
#         # ------------------------
#         return message

#     # Make methods instance methods by adding 'self'
#     def wash_hands(self):
#         edit=2
#         print("Washing hands...")
#         self.state_manager.adjust_stat("hydration", edit) # Washing hands might not give hydration, maybe hygiene or something else?
#         message=f"You wash your hands, you feel refreshed."
#         # --- Add signal call ---
#         self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"}) # Or a soap icon?
#         # ------------------------
#         return message



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


class room_computer:
    def __init__(self, state_manager, signal=None, wiki=None):
        self._signal_callback=signal
        self.wiki=wiki
        # Store the state_manager reference
        self.state_manager : InventoryHouseManager = state_manager

        self.last_accessed_wiki=""
        self.last_wiki_query=""
        #print("Computer room initialized.")

    # Add the helper method
    _send_signal = _send_signal # Assign the common helper function

    def display_information(self):
        message=f"""The last query made into the wiki was:\n{self.last_wiki_query}\n
                    The last accessed article was: \n{self.last_accessed_wiki}\n 
                """
        return message

    def write_blog_post(self, post):        
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/writing_icon.png"}) # Example icon
        # ------------------------
        # Implement blog writing logic... maybe adjust a stat or create an item?
        return f"You wrote a blog post about: {post}. It feels good to express yourself."


    def random_wikipedia(self):
        "Delegated, returns a structured string with title and body for a random wikipedia article"
        # --- Add signal call ---
        edit=-2
        self.state_manager.adjust_stat("energy", edit)

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})
        # ------------------------
        article=self.wiki.fetch_random_wiki_article()
        self.last_accessed_wiki=article
        return article
    
    def search_wikipedia_articles(self, query):
        "Delegated, returns a structured string with title and body for a random wikipedia article"
        edit=-2
        self.state_manager.adjust_stat("energy", edit)
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})
        # ------------------------
        query_result=self.wiki.search_wikipedia(query)
        self.last_wiki_query=query_result
        return query_result

    def get_wikipedia_article_content(self, title):
        "Delegated, returns a structured string with title and body for a random wikipedia article"
        edit=-5
        self.state_manager.adjust_stat("energy", edit)
        # --- Add signal call ---
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})
        # ------------------------
        article=self.wiki.get_wikipedia_content_by_title(title)
        self.last_accessed_wiki=article
        return article
    

# Define the main handler class
class main_tools_handle:
    def __init__(self, state_manager, signal=None, memory_manager=None, config_manager=None, open_meteo=None):
        self.memory=memory_manager

        wikipedia_enabled = config_manager.get_config('Tools', "enable_wikipedia")


        print(f"DEBUG: WIKPEDIA enabled (config): {wikipedia_enabled}") # TODO: initialization and loading shouldn't be hiding here, move to tool_registry, conditional loading

        self.wiki=None
        if wikipedia_enabled:
            try: 
                from tools.tools_folder.tools_helpers.services.wiki_handle import Wikipedia_handle
                self.wiki=Wikipedia_handle(self.memory)
            except Exception as e:
                print(f"Error initializing Wikipedia_handle: {e}")

        print("Main tools handler initialized.")
        self._signal_callback=signal # Store the main signal callback here
        # Store the state_manager reference
        self.state_manager : InventoryHouseManager = state_manager

        self.open_meteo = open_meteo

        # Instantiate the room classes and store them as attributes
        # Pass the state_manager AND the signal callback to the room instances
        #self.bathroom = room_bathroom(self.state_manager, self._signal_callback)
        #self.bedroom = room_bedroom(self.state_manager, self._signal_callback, self.memory)
        #self.living_room= room_living_room(self.state_manager, self._signal_callback, self.open_meteo)
        self.computer = room_computer(self.state_manager, self._signal_callback, self.wiki)
        self.garden = room_garden(self.state_manager, self._signal_callback, self.open_meteo)
        # --- Fix: Removed the extra 'self' argument here ---
        #  self.white_room = room_white(self.state_manager, self._signal_callback)
        # ---------------------------------------------------
        # self.kitchen = room_kitchen(self.state_manager, self._signal_callback, config_manager)

       # self.comfort = ComfortAffordances(self.state_manager, self._signal_callback, self.memory)

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