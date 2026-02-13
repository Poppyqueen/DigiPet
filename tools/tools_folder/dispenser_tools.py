# dispenser_tools.py

from inventory_items.items_provider.item_store import ItemStore
import random


class DispenserTools:
    def __init__(self, state_manager, signal=None):
        self.state = state_manager  # This is InventoryHouseManager
        self.item_store = ItemStore()
        self._signal_callback = signal

    def _send_signal(self, signal_data):
        """Helper method to send signals using the registered callback."""
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from DispenserTools: {e}")

    def examine_dispenser(self, item_id: int):
        """
        Examines the dispenser and returns its status.
        """
        item_data, error = self.state.inventory_service.get_validated_item_data(item_id, required_type="dispenser")
        if error:
            return error

        dispenser_state = item_data.get("dispenser_state", {})
        contents = dispenser_state.get("contents", {})
        total_count = sum(contents.values())

        if total_count <= 0:
            return "The dispenser is empty. You need to refill it."

        return f"The dispenser has {total_count} candies left."

    def dispense_candy(self, item_id: int):
        """
        Dispenses a single candy from the dispenser if it has any left.
        """
        item_data, error = self.state.inventory_service.get_validated_item_data(item_id, required_type="dispenser")
        if error:
            return error

        dispenser_state = item_data.get("dispenser_state", {})
        contents = dispenser_state.get("contents", {})
        total_count = sum(contents.values())

        if total_count <= 0:
            self._send_signal({"type": "show_message_popup", "message": "Click! It's empty."})
            return "The dispenser is empty. You need to refill it."

        # Weighted random selection
        selected_candy = random.choices(list(contents.keys()), weights=list(contents.values()), k=1)[0]

        # Create the dispensed candy item
        single_candy_blueprint = self.item_store.get_item(selected_candy) or self.item_store.get_item("Single Candy")
        if not single_candy_blueprint:
            return f"Error: Could not find candy definition for '{selected_candy}'."

        if not self.state.create_item("inventory", None, single_candy_blueprint, internal=True):
            return "Error: Failed to dispense candy (could not create item)."

        # Build the new contents (copy-on-write)
        new_contents = dict(contents)
        new_contents[selected_candy] -= 1
        if new_contents[selected_candy] <= 0:
            del new_contents[selected_candy]
        new_total = sum(new_contents.values())

        # Single authoritative write
        result = self.state.inventory_service.set_item_attribute(
            item_id, "contents", new_contents, path=["dispenser_state"]
        )
        if result.startswith("Error") or "failed" in result.lower():
            return result

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/candy.png", "popup_type": 2})
        return f"You turn the handle. Clatter! A {selected_candy} falls out. You have {new_total} candies left."

    def refill_dispenser(self, dispenser_id: int, bag_id: int):
        """
        Refills the dispenser using a Candy Refill Bag from inventory.
        """
        dispenser_data, error = self.state.inventory_service.get_validated_item_data(dispenser_id, required_type="dispenser")
        if error:
            return error

        bag_data, error = self.state.inventory_service.get_validated_item_data(bag_id, required_type="candy_bag")
        if error:
            return error

        # Resolve bag contents (from item data, or fall back to blueprint)
        bag_contents = bag_data.get("contents")

        if not bag_contents:
            return "Error: The refill bag seems to be empty or invalid."

        # Consume the refill bag before writing new state
        if not self.state.remove_item(bag_id, internal=True):
            return "Error: Failed to use the refill bag."

        # Build the merged contents (copy-on-write)
        current_contents = dispenser_data.get("dispenser_state", {}).get("contents", {})
        new_contents = dict(current_contents)
        for candy, qty in bag_contents.items():
            new_contents[candy] = new_contents.get(candy, 0) + qty

        # Single authoritative write
        result = self.state.inventory_service.set_item_attribute(
            dispenser_id, "contents", new_contents, path=["dispenser_state"]
        )
        if result.startswith("Error") or "failed" in result.lower():
            return result

        self._send_signal({"type": "show_message_popup", "message": "Dispenser refilled!"})
        return f"You pour the {bag_data.get('name')} into the dispenser. It looks full and colorful now!"