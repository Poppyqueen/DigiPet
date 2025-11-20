# dispenser_tools.py

from inventory_items.items_provider.item_store import ItemStore
import random

class DispenserTools:
    def __init__(self, state_manager, signal=None):
        self.state = state_manager # This is InventoryHouseManager
        self.item_store = ItemStore()
        self._signal_callback = signal

    def _send_signal(self, signal_data):
        """Helper method to send signals using the registered callback."""
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from DispenserTools: {e}")


    def _update_description(self, item_data, count):
        """Updates the visible description of the dispenser."""
        descriptions = item_data.get("descriptions", [])
        new_status = f"Status: {count} candies left"
        updated = False
        
        for i, line in enumerate(descriptions):
            if line.startswith("Status:"):
                descriptions[i] = new_status
                updated = True
                break
        
        if not updated:
            descriptions.append(new_status)
            
        item_data["descriptions"] = descriptions

    def dispense_candy(self, item_id: int):
        """
        Dispenses a single candy from the dispenser if it has any left.
        """
        item_data, error = self.state.inventory_service.get_validated_item_data(item_id, required_type="dispenser")
        if error:
            return error

        # Check dispenser state (default to empty dict if missing)
        dispenser_state = item_data.get("dispenser_state", {})
        
        contents = dispenser_state.get("contents", {})
        total_count = sum(contents.values())
        
        if total_count <= 0:
            self._send_signal({"type": "show_message", "message": "Click! It's empty."})
            return "The dispenser is empty. You need to refill it."

        # Weighted Random Selection
        candy_types = list(contents.keys())
        counts = list(contents.values())
        selected_candy = random.choices(candy_types, weights=counts, k=1)[0]
        
        # Create Single Candy
        single_candy_blueprint = self.item_store.get_item(selected_candy)
        if not single_candy_blueprint:
             # Fallback
             single_candy_blueprint = self.item_store.get_item("Single Candy")
             if not single_candy_blueprint:
                return f"Error: Could not find candy definition for '{selected_candy}'."

        creation_result = self.state.create_item("inventory", None, single_candy_blueprint, internal=True)
        
        if not creation_result:
             return "Error: Failed to dispense candy (could not create item)."

        # Update Dispenser State
        contents[selected_candy] -= 1
        if contents[selected_candy] <= 0:
            del contents[selected_candy]
            
        dispenser_state["contents"] = contents
        # Update total count for description
        new_total = sum(contents.values())
        
        item_data["dispenser_state"] = dispenser_state
        self._update_description(item_data, new_total)
        
        # Persist
        persist_error = self.state.inventory_service.persist_item_changes(item_id)
        if persist_error:
            return persist_error

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/candy_icon.png"})
        return f"You turn the handle. Clatter! A {selected_candy} falls out. You have {new_total} candies left."

    def refill_dispenser(self, item_id: int):
        """
        Refills the dispenser using a Candy Refill Bag from inventory.
        """
        # Check for Refill Bag
        inventory_items = self.state.get_inventory_items(internal=True)
        refill_bag = None
        
        for item in inventory_items:
            # Check for new candy_bag type
            if "candy_bag" in item.get("type", []):
                refill_bag = item
                break
        
        if not refill_bag:
            return "You don't have any candy refill bags in your inventory."

        # Get Dispenser Data
        item_data, error = self.state.inventory_service.get_validated_item_data(item_id, required_type="dispenser")
        if error:
            return error

        # Consume Refill Bag
        if not self.state.remove_item(refill_bag.get("id"), internal=True):
            return "Error: Failed to use the refill bag."

        # Determine Contents
        bag_contents = refill_bag.get("contents")
        if not bag_contents:
            # Try looking up blueprint by name
            blueprint = self.item_store.get_item(refill_bag.get("name"))
            if blueprint:
                bag_contents = blueprint.get("contents")
        
        if not bag_contents:
            return "Error: The refill bag seems to be empty or invalid."

        # Update Dispenser State
        dispenser_state = item_data.get("dispenser_state", {"contents": {}})
        current_contents = dispenser_state.get("contents", {})
        
        # Additive update
        for candy, qty in bag_contents.items():
            current_contents[candy] = current_contents.get(candy, 0) + qty
            
        dispenser_state["contents"] = current_contents
        
        total_count = sum(current_contents.values())
        self._update_description(item_data, total_count)

        # Persist
        persist_error = self.state.inventory_service.persist_item_changes(item_id)
        if persist_error:
            return persist_error

        self._send_signal({"type": "show_message", "message": "Dispenser refilled!"})
        return f"You pour the {refill_bag.get('name')} into the dispenser. It looks full and colorful now!"
