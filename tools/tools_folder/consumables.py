# tools_folder/item_action_tools.py
# consume_item extracted from StatTracker.
# Follows the same pattern as BookTools: state_manager injected directly,
# all state access through the public facade, no private member access.

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager #

import random


class ConsumablesTools:
    def __init__(self, state_manager, signal_callback):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal_callback = signal_callback

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from ConsumablesTools: {e}")

    def _item_display(self, item_data: dict) -> str:
        return self.state_manager.format_item_for_display(item_data)

    def consume_item(self, item_id: int, uses: int = 1) -> str:
        if not isinstance(item_id, int):
            return f"Failed to consume: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        # find_item handles existence, location, and returns item_data cleanly —
        # replaces _find_item_info_by_id, _is_valid_item_data, and the location guard.
        result = self.state_manager.find_item(item_id, required_location="inventory", required_type="consumable")
        if not result.success:
            return f"Failed to consume: {result.error} {result.message}"

        item_data = result.item_data
        display = self._item_display(item_data)

        uses_left = item_data.get("consume_uses_left", 1)
        if uses_left < uses:
            return f"Failed to consume {display}: Not enough uses left ({uses_left} remaining, {uses} requested)."

        stats_edit = item_data.get("stats_edit", {})

        for stat, amount in stats_edit.items():
            self.state_manager.adjust_stat(stat, amount * uses)

        message_parts = []
        remaining_uses = uses_left - uses

        if remaining_uses <= 0:
            removal_result = self.state_manager.remove_item(item_id)
            message_parts.append(f"Item {display} consumed.")
            if not removal_result.success:
                print(f"Warning: Item {display} consumed but could not be removed: {removal_result.error}")
            else:
                message_parts.append(removal_result.message)
        else:
            attr_result = self.state_manager.set_item_attribute(item_id, "consume_uses_left", remaining_uses)
            if attr_result.success:
                message_parts.append(attr_result.message)

        if stats_edit:
            changes_strings = [
                f"{stat}: {'+'if (amount * uses) >= 0 else ''}{amount * uses:.1f} points"
                for stat, amount in stats_edit.items()
            ]
            message_parts.append(f"Your stats changed: {', '.join(changes_strings)}.")
            stats_response = self.state_manager.get_stats()
            if stats_response.success:
                message_parts.append(stats_response.message)
            else:
                message_parts.append(f"Error: {stats_response.error}")

        effects_text_list = item_data.get("effects", [])
        if isinstance(effects_text_list, list) and all(isinstance(t, str) for t in effects_text_list):
            valid_texts = [t.strip() for t in effects_text_list if t and t.strip()]
            if valid_texts:
                uses_capped = min(uses, 10)
                pool = valid_texts[:]
                random.shuffle(pool)
                selected_text = ""
                for i in range(uses_capped):
                    if i % len(pool) == 0 and i > 0:
                        random.shuffle(pool)
                    selected_text += pool[i % len(pool)]
                message_parts.append(selected_text)

        self._send_signal({
            "type": "show_icon_popup",
            "icon_path": "style/images/action_icons/plate_icon.png",
            "popup_type": 2,
        })
        return "\n".join(p for p in message_parts if p)
    

    def perceive_consumables(self) -> str:

        inventory = self.state_manager.get_inventory_state()

        consumables = [
            item for item in inventory.inventory_items
            if "consumable" in item.item_data.get("type", [])
        ]

        if not consumables:
            return ""
        
        parts = []
        for consumable in consumables:
            item_id = consumable.item_id
            uses_left = consumable.item_data.get("consume_uses_left", 1)
            entry = f"Consumables in your inventory: \n - {item_id}: {self._item_display(consumable.item_data)} (Uses left: {uses_left})\n"
            parts.append(entry)

        return "".join(parts)
