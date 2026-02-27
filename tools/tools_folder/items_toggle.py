# TODO: Think of a better way to do all of this, not only this specific tool, but the whole toggle system.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager # just for typing
    from inventory_items.services.item_lookup_result import ItemLookupResult
    from inventory_items.services.set_item_attribute_result import SetItemAttributeResult

class ItemToggleTool:
    def __init__(self, state_manager, signal):
        self.state_manager : InventoryHouseManager = state_manager
        self._signal_callback = signal


    def _toggle_item_power(self, item_id: str, turn_on: bool):
        item_result : ItemLookupResult = self.state_manager.find_item(item_id)
        if not item_result.success:
            return item_result.error
        item_data = item_result.item_data
        if "power_toggle" not in item_data:
            return f"Error: Item '{item_data.get('name', 'Unknown')}' has no power toggle."
        if item_data.get("power_toggle") == turn_on:
            return f"The {item_data.get('name')} is already {'ON' if turn_on else 'OFF'}."
        self.state_manager.set_item_attribute(item_id, "power_toggle", turn_on)

        state_str = "ON" if turn_on else "OFF"
        self._send_signal({"type": "show_message_popup", "message": f"Toggled {item_data.get('name')} {state_str}"})
        return f"Successfully turned {state_str} the {item_data.get('name')}."

    
    def toggle_item_power_auto(self, item_id) -> str: 
        """Toggle power for any item — determines on/off from current state."""
        item_result : ItemLookupResult = self.state_manager.find_item(item_id)
        if not item_result.success:
            return item_result.error
        item_data = item_result.item_data
        if "power_toggle" not in item_data:
            return f"'{item_data.get('name', 'That item')}' doesn't have a power switch."
        
        current_state = item_data.get("power_toggle", False)
        turn_on = not current_state  # just flip it
        return self._toggle_item_power(item_id, turn_on)