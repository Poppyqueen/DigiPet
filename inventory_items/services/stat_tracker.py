
# services/stat_tracker.py
import random

class StatTracker:
    # Constants for stat ranges (or get from config/state_store if dynamic)
    MAX_STAT_VALUE = 200
    MIN_STAT_VALUE = 0

    def __init__(self, state_store, signal_callback):
        self._state_store = state_store
        self._signal_callback = signal_callback
        self._inventory_service = None # Dependency for consume_item

    def set_inventory_service(self, inventory_service_instance):
        """Sets the InventoryService dependency for consume_item."""
        self._inventory_service = inventory_service_instance

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal: {e}")

    def get_stats(self, internal: bool = False) -> str | dict:
        stats_data = self._state_store.get_state_section("stats")
        if not isinstance(stats_data, dict):
            print("Warning: Stats data is corrupted in state_store.")
            if internal:
                return {"status": "error", "message": "Stats data is corrupted.", "stats_data_raw": stats_data}
            else:
                return "Error: Stats system is corrupted."

        # Ensure all required stats are present, clamp values
        cleaned_stats = {}
        needs_save = False
        required_stats_keys = ["fullness", "hydration", "energy"]
        for stat_key in required_stats_keys:
            value = stats_data.get(stat_key)
            if not isinstance(value, (int, float)):
                # Fallback to default, though _post_init_state_validation should fix
                default_val = self._state_store._default_state.get("stats", {}).get(stat_key, 200)
                cleaned_stats[stat_key] = default_val
                needs_save = True
                print(f"Warning: Stat '{stat_key}' invalid ({value}), resetting to default ({default_val}).")
            else:
                clamped_value = max(self.MIN_STAT_VALUE, min(self.MAX_STAT_VALUE, value))
                if clamped_value != value:
                    needs_save = True
                    print(f"Warning: Stat '{stat_key}' ({value}) out of range, clamped to {clamped_value}.")
                cleaned_stats[stat_key] = clamped_value

        if needs_save:
            self._state_store.update_state_section("stats", cleaned_stats) # Save corrected stats

        if internal:
            return cleaned_stats
        else:
            return (f"Current Stats: "
                    f"Fullness: {cleaned_stats.get('fullness', 'N/A'):.1f}/{self.MAX_STAT_VALUE}, "
                    f"Hydration: {cleaned_stats.get('hydration', 'N/A'):.1f}/{self.MAX_STAT_VALUE}, "
                    f"Energy: {cleaned_stats.get('energy', 'N/A'):.1f}/{self.MAX_STAT_VALUE}")

    def adjust_stat(self, stat_name: str, amount: int|float) -> str:
        stat_name = stat_name.lower().strip()
        stats_data = self._state_store.get_state_section("stats")

        if not isinstance(stats_data, dict):
            return "Error: Stats data is corrupted, cannot adjust stat."

        if stat_name not in stats_data:
            return f"Error: Stat '{stat_name}' does not exist."
        if not isinstance(amount, (int, float)):
            return f"Error: Adjustment amount must be a number, received '{amount}' ({type(amount).__name__})."

        current_value = stats_data[stat_name]
        new_value = current_value + amount
        clamped_value = max(self.MIN_STAT_VALUE, min(self.MAX_STAT_VALUE, new_value))

        if clamped_value == current_value:
            return f"Stat '{stat_name}' remains at {int(clamped_value)}. No change needed or possible."

        stats_data[stat_name] = clamped_value
        self._state_store.update_state_section("stats", stats_data) # Save updated stats

        change_msg = "increased" if amount > 0 else "decreased"
        if amount == 0: change_msg = "changed by 0 (no effect)"

        self._send_signal({"type": "stat_changed", "stat_name": stat_name, "new_value": clamped_value, "change_amount": amount})

        return (f"Stat '{stat_name}' {change_msg} by {abs(amount):.1f} to {int(clamped_value)}.\n"
                f"{self.get_stats(internal=False).replace('Current Stats: ', '')}")

    def apply_consumable_effects(self, stats_edit_dict: dict) -> dict | None:
        """
        Applies stat changes from a consumable item.
        Returns a dictionary of actual changes or None if stats data is corrupted.
        """
        stats_data = self._state_store.get_state_section("stats")
        if not isinstance(stats_data, dict):
            return None # Indicate corrupted stats data

        actual_changes = {}
        for stat, amount in stats_edit_dict.items():
            if stat in stats_data: # Only apply to valid stats
                current_value = stats_data[stat]
                new_value = current_value + amount
                clamped_value = max(self.MIN_STAT_VALUE, min(self.MAX_STAT_VALUE, new_value))
                if clamped_value != current_value: # Only record if there was an actual change
                    stats_data[stat] = clamped_value
                    actual_changes[stat] = clamped_value - current_value # Record actual change amount

        if actual_changes: # Only save if any stats actually changed
            self._state_store.update_state_section("stats", stats_data)
        return actual_changes

    def consume_item(self, item_id: int) -> str:
        if not isinstance(item_id, int):
            return f"Failed to consume: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        if not self._inventory_service:
            return "Error: Inventory service not available for consumption."

        item_info = self._inventory_service._find_item_info_by_id(item_id)
        if not item_info:
            return f"Failed to consume: Item with ID '{item_id}' not found anywhere."

        item_data = item_info["item_data"]
        item_display = self._inventory_service._format_item_for_display(item_data, False)

        if item_info["location"] != "inventory":
            return f"Failed to consume {item_display}: You can only consume items from your inventory. It is in {item_info['location']}."

        is_valid, msg = self._inventory_service._is_valid_item_data(item_data, check_id=True)
        if not is_valid:
            print(f"Warning: Attempted to consume invalid item ID {item_id}: {msg}. Removing from inventory due to corruption.")
            remove_result = self._inventory_service.remove_item(item_id, internal=True)
            return f"Failed to consume {item_display}: Item data is corrupted. It has been removed from your inventory. ({msg})"

        if "consumable" not in item_data.get("type", []):
            return f"Failed to consume {item_display}: This item is not a consumable type (types found: {item_data.get('type', ['unknown type'])})."

        stats_edit = item_data.get("stats_edit", {})
        effects_text_list = item_data.get("effects", [])

        stat_changes_summary = self.apply_consumable_effects(stats_edit)

        if stat_changes_summary is None:
            return f"Failed to consume {item_display}: Error applying effects, stats data is corrupted."

        # Remove the item from inventory using InventoryService
        removal_success = self._inventory_service.remove_item(item_id, internal=True)
        removal_status = f"Item {item_display} consumed."
        if not removal_success:
            removal_status = f"Warning: Item {item_display} consumed but could not be removed from inventory list."
            print(removal_status)

        selected_effect_text = ""
        if isinstance(effects_text_list, list) and all(isinstance(text, str) for text in effects_text_list):
            valid_effect_texts = [text.strip() for text in effects_text_list if text and text.strip()]
            if valid_effect_texts:
                selected_effect_text = random.choice(valid_effect_texts)

        message = removal_status
        if stat_changes_summary:
            changes_strings = []
            for stat, change in stat_changes_summary.items():
                sign = "+" if change >= 0 else ""
                changes_strings.append(f"{stat}: {sign}{change:.1f} points")
            message += f"\nYour stats changed: {', '.join(changes_strings)}."
            current_stats_msg = self.get_stats(internal=False)
            if not current_stats_msg.startswith("Error:"):
                message += f"\n{current_stats_msg.replace('Current Stats: ', '')}"

        if selected_effect_text:
            message += f"\n{selected_effect_text}"

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/plate_icon.png", "popup_type": 2})
        return message
