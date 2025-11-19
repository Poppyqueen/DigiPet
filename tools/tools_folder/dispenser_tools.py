# dispenser_tools.py
from inventory_items.items_provider.item_store import ItemStore

class DispenserTools:
    def __init__(self, state_manager, signal=None):
        self.state = state_manager # This is InventoryHouseManager
        self.item_store = ItemStore("inventory_items/items_provider/items_data")
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
        item_data, error = self._get_dispenser_data(item_id)
        if error:
            return error

        # Check candy count (default to 0 if missing)
        candy_count = item_data.get("candy_count", 0)
        
        if candy_count <= 0:
            self._send_signal({"type": "show_message", "message": "Click! It's empty."})
            return "The dispenser is empty. You need to refill it."

        # Create Single Candy
        single_candy_blueprint = self.item_store.get_item("Single Candy")
        if not single_candy_blueprint:
            return "Error: Could not find 'Single Candy' definition."

        # Use InventoryHouseManager's create_item which delegates to InventoryService
        # We need to pass a list or dict. create_item handles quantity.
        creation_result = self.state.create_item("inventory", None, single_candy_blueprint, internal=True)
        
        # create_item returns a list of created items if internal=True and input is list, 
        # or boolean/message if input is dict? 
        # Checking inventory_service.py: 
        # if internal: return [] if isinstance(item_creation_data, list) else False (on failure)
        # if successful: returns list of created items (if list input) or... wait.
        # It seems create_item return value depends on input type.
        # Let's assume it returns truthy on success.

        # It actually returns a list of created items IDs on either input type, 
        # it is fine as is but we should document this behavior.
        
        if not creation_result:
             return "Error: Failed to dispense candy (could not create item)."

        # Update Dispenser State
        new_count = candy_count - 1
        item_data["candy_count"] = new_count
        self._update_description(item_data, new_count)
        
        # Persist
        persist_error = self.state.inventory_service.persist_item_changes(item_id)
        if persist_error:
            return persist_error

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/candy_icon.png"})
        return f"You turn the handle. Clatter! A candy falls out. You have {new_count} candies left."

    def refill_dispenser(self, item_id: int):
        """
        Refills the dispenser using a Candy Refill Bag from inventory.
        """
        # Check for Refill Bag
        inventory_items = self.state.get_inventory_items(internal=True)
        refill_bag_id = None
        for item in inventory_items:
            if item.get("name") == "Candy Refill Bag":
                refill_bag_id = item.get("id")
                break
        
        if not refill_bag_id:
            return "You don't have a Candy Refill Bag in your inventory."

        # Get Dispenser Data
        item_data, error = self.state.inventory_service.get_validated_item_data(item_id, required_type="dispenser")
        if error:
            return error

        # Consume Refill Bag
        if not self.state.remove_item(refill_bag_id, internal=True):
            return "Error: Failed to use the refill bag."

        # Update Dispenser State
        max_capacity = 10
        item_data["candy_count"] = max_capacity
        self._update_description(item_data, max_capacity)

        # Persist
        persist_error = self.state.inventory_service.persist_item_changes(item_id)
        if persist_error:
            return persist_error

        self._send_signal({"type": "show_message", "message": "Dispenser refilled!"})
        return "You pour the bag of candies into the dispenser. It looks full and colorful now!"
