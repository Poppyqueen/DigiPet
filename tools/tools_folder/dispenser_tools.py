# dispenser_tools.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

import random


class DispenserTools:
    def __init__(self, state_manager, signal=None, item_store=None):
        self.state_manager: InventoryHouseManager = state_manager
        self.item_store = item_store
        self._signal_callback = signal

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from DispenserTools: {e}")

    def _get_dispenser_contents(self, item_data: dict) -> dict:
        """Safely extract dispenser contents, always returning a dict."""
        return (item_data.get("dispenser_state") or {}).get("contents") or {}

    def _get_bag_contents(self, item_data: dict) -> dict:
        """Safely extract candy bag contents, always returning a dict."""
        entries = item_data.get("contents") or []
        return {entry["item_name"]: entry["quantity"] for entry in entries}

    def examine_dispenser(self, item_id: int):
        """Examines the dispenser and returns its status."""
        dispenser_result = self.state_manager.find_item(item_id, required_type="dispenser", required_location="room")
        if not dispenser_result.success:
            return dispenser_result.error

        contents = self._get_dispenser_contents(dispenser_result.item_data)
        total_count = sum(contents.values())

        if total_count <= 0:
            return "The dispenser is empty. You need to refill it."

        return f"The dispenser has {total_count} candies left."

    def dispense_candy(self, item_id: int):
        """Dispenses a single candy from the dispenser if it has any left."""
        dispenser_result = self.state_manager.find_item(item_id, required_type="dispenser", required_location="room")
        if not dispenser_result.success:
            return dispenser_result.error

        contents = self._get_dispenser_contents(dispenser_result.item_data)
        total_count = sum(contents.values())

        if total_count <= 0:
            self._send_signal({"type": "show_message_popup", "message": "Click! It's empty."})
            return "The dispenser is empty. You need to refill it."

        selected_candy = random.choices(list(contents.keys()), weights=list(contents.values()), k=1)[0]

        single_candy_blueprint = self.item_store.get_item(selected_candy) or self.item_store.get_item("Single Candy")
        if not single_candy_blueprint:
            return f"Error: Could not find candy definition for '{selected_candy}'."

        creation_result = self.state_manager.create_item("inventory", None, single_candy_blueprint)
        if not creation_result.success:
            return f"Error: Failed to dispense candy. {creation_result.error} {creation_result.message}"

        new_contents = dict(contents)
        new_contents[selected_candy] -= 1
        if new_contents[selected_candy] <= 0:
            del new_contents[selected_candy]
        new_total = sum(new_contents.values())

        self.state_manager.set_item_attribute(
            item_id, "contents", new_contents, path=["dispenser_state"]
        )

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/candy.png", "popup_type": 2})
        return f"You turn the handle. Clatter! A {selected_candy} falls out. You have {new_total} candies left."

    def refill_dispenser(self, dispenser_id: int, bag_id: int):
        """Refills the dispenser using a Candy Refill Bag from inventory."""
        dispenser_result = self.state_manager.find_item(dispenser_id, required_type="dispenser", required_location="room")
        if not dispenser_result.success:
            return dispenser_result.error

        candy_bag_result = self.state_manager.find_item(bag_id, required_type="candy_bag", required_location="inventory")
        if not candy_bag_result.success:
            return candy_bag_result.error

        bag_contents = self._get_bag_contents(candy_bag_result.item_data)
        if not bag_contents:
            return "Error: The refill bag seems to be empty or invalid."

        removal_result = self.state_manager.remove_item(bag_id)
        if not removal_result.success:
            return f"Error: Failed to use the refill bag. {removal_result.error}"

        current_contents = self._get_dispenser_contents(dispenser_result.item_data)
        new_contents = dict(current_contents)
        for candy, qty in bag_contents.items():
            new_contents[candy] = new_contents.get(candy, 0) + qty

        self.state_manager.set_item_attribute(
            dispenser_id, "contents", new_contents, path=["dispenser_state"]
        )

        self._send_signal({"type": "show_message_popup", "message": "Dispenser refilled!"})
        return f"You pour the {candy_bag_result.item_data.get('name')} into the dispenser. It looks full and colorful now!"