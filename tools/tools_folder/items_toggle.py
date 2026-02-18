class ItemToggleTool:
    def __init__(self, state_manager, signal):
        self.state_manager = state_manager
        self._signal_callback = signal


    def _toggle_item_power(self, item_id: str, turn_on: bool):
        item_data, error = self.state_manager.inventory_service.get_validated_item_data(item_id)
        if error:
            return error
        if "power_toggle" not in item_data:
            return f"Error: Item '{item_data.get('name', 'Unknown')}' has no power toggle."
        if item_data.get("power_toggle") == turn_on:
            return f"The {item_data.get('name')} is already {'ON' if turn_on else 'OFF'}."
        self.state_manager.inventory_service.set_item_attribute(item_id, "power_toggle", turn_on)
        state_str = "ON" if turn_on else "OFF"
        self._signal_callback({"type": "show_message_popup", "message": f"Toggled {item_data.get('name')} {state_str}"})
        return f"Successfully turned {state_str} the {item_data.get('name')}."

    
    def toggle_item_power_auto(self, item_id) -> str: 
        """Toggle power for any item — determines on/off from current state."""
        item_data, error = self.state_manager.inventory_service.get_validated_item_data(item_id)
        if error:
            return error
        if "power_toggle" not in item_data:
            return f"'{item_data.get('name', 'That item')}' doesn't have a power switch."
        
        current_state = item_data.get("power_toggle", False)
        turn_on = not current_state  # just flip it
        return self._toggle_item_power(item_id, turn_on)