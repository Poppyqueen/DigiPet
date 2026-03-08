from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager # just for typing


import random

WATER_FEATURE_TYPE = "water_point"
DRINKING_FROM_NARRATIVE = "narrative_drinking"
WASH_SELF_NARRATIVE = "narrative_wash_self"


class WaterInstallation:
    def __init__(self, state_manager, signal=None):
        self._signal_callback=signal
        # Store the state_manager reference
        self.state_manager : InventoryHouseManager = state_manager
        #print("Bathroom initialized.")

    @staticmethod
    def _get_item_text(item_deets, source:str):
        item_texts = item_deets.get(source, []) 
        return random.choice(item_texts)

    # Make methods instance methods by adding 'self'
    def drink_from_water_point(self, source_id):
        # You can now access the state_manager if needed

        lookup = self.state_manager.find_item(source_id, WATER_FEATURE_TYPE, "accessible")
        if lookup.error:
            return lookup.error

        item_details = lookup.item_data
        
        name = item_details["name"]
        desc = self._get_item_text(item_details, "descriptions")
        phenom = self._get_item_text(item_details, DRINKING_FROM_NARRATIVE)

        stats_messages = []
        stats_edit = item_details["stats_edit"]
        for stat, amount in stats_edit.items():
            edit = self.state_manager.adjust_stat(stat, amount)
            stats_messages.append(edit.message)

        message=f"Drank some water from the {name}, {desc} {phenom}! {"\n".join(stats_messages)}"


        # --- Add signal call ---
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"})
        # ------------------------
        return message

    # # Make methods instance methods by adding 'self'
    def wash_self_water_feature(self, source_id):
        edit=2
        lookup = self.state_manager.find_item(source_id, WATER_FEATURE_TYPE, "accessible")
        if lookup.error:
            return lookup.error

        item_details = lookup.item_data
        item_name = item_details['name']
        desc = self._get_item_text(item_details, "descriptions")
        phenom = self._get_item_text(item_details, WASH_SELF_NARRATIVE
        )
        #print("Washing hands...")
        stats_edit = self.state_manager.adjust_stat("hydration", edit) # Washing hands might not give hydration, maybe hygiene or something else?
        stats_message = stats_edit.message

        message=f"You reach for the {item_name}, {desc}\n{phenom}\n{stats_message}"
        # --- Add signal call ---
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"}) # Or a soap icon?
        # ------------------------
        return message

    # TODO: This could refill water container types, however we need to think about consumables, how they work and all that jazz