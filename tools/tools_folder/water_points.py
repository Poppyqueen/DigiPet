from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager  # just for typing

import random

WATER_FEATURE_TYPE = "water_point"
DRINKING_FROM_NARRATIVE = "narrative_drinking"
WASH_SELF_NARRATIVE = "narrative_wash_self"


class WaterInstallation:
    def __init__(self, state_manager, signal=None):
        self._signal_callback = signal
        # Store the state_manager reference
        self.state_manager: InventoryHouseManager = state_manager

    @staticmethod
    def _get_item_text(item_deets, source: str):
        item_texts = item_deets.get(source, [])
        return random.choice(item_texts)

    def _validate_interface(self, item_id: int):
        result = self.state_manager.find_item(
            item_id,
            required_type=WATER_FEATURE_TYPE,
            required_location="accessible",
        )
        if result.toggle_state is False:
            return None, f"Water point {self.state_manager.format_item_for_display(item_id, False)}, is 'off' can't use it like that."
        if not result.success:
            return None, result.error
        return result.item_data, None

    def drink_from_water_point(self, source_id):
        item_details, error = self._validate_interface(source_id)
        if error:
            return error

        name = self.state_manager.format_item_for_display(item_details)
        desc = self._get_item_text(item_details, "descriptions")
        phenom = self._get_item_text(item_details, DRINKING_FROM_NARRATIVE)

        stats_messages = []
        stats_edit = item_details["stats_edit"]
        for stat, amount in stats_edit.items():
            edit = self.state_manager.adjust_stat(stat, amount)
            stats_messages.append(edit.message)

        message = f"Drank some water from the {name}, {desc} {phenom}! {'\n'.join(stats_messages)}"
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"})
        return message

    def wash_self_water_feature(self, source_id):
        item_details, error = self._validate_interface(source_id)
        if error:
            return error

        item_name = self.state_manager.format_item_for_display(item_details)
        desc = self._get_item_text(item_details, "descriptions")
        phenom = self._get_item_text(item_details, WASH_SELF_NARRATIVE)

        hydration_edit = random.uniform(0.05, 0.15)
        stats_edit = self.state_manager.adjust_stat("hydration", hydration_edit)
        stats_message = stats_edit.message

        message = f"You reach for the {item_name}, {desc}\n{phenom}\n{stats_message}"
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/water_icon.png"})
        return message

    # TODO: This could refill water container types, however we need to think about consumables, how they work and all that jazz