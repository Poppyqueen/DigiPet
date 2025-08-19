
# services/inventory_service.py
import datetime

import json

class InventoryService:
    MAX_INVENTORY_SLOTS = 30
    ALLOWED_ITEM_TYPES = ["tool", "consumable", "misc", "key", "weapon", "armor", "furniture", "book", "seed", "chair"]

    def __init__(self, state_store, signal_callback):
        self._state_store = state_store
        self._signal_callback = signal_callback
        self._room_manager = None # Dependency to be set later

    def _get_item_stacking_key(self, item_data: dict):
        """
        Generates a key for comparing stackable items.
        Attributes that should NOT affect stacking (like ID, quantity, descriptions) are excluded.
        """
        if not item_data.get("stackable", False):
            return None # Only stackable items have a stacking key

        # Create a deep copy to avoid modifying the original item_data if it's a mutable dict
        # then filter out non-stacking attributes.
        stacking_attrs = {}
        for k, v in item_data.items():
            if k not in ["id", "quantity", "static", "stats_edit", "effects"]: # We need to decide what we will ignore
                # last_modified and location_history are examples of other attributes
                # that shouldn't affect stacking. Add or remove as needed.
                stacking_attrs[k] = v
        
        # Use json.dumps with sort_keys=True for a consistent, comparable string
        # for complex nested structures like lists or dictionaries within stacking_attrs.
        return json.dumps(stacking_attrs, sort_keys=True)

    def _find_matching_stack_in_list(self, item_list: list, item_to_match: dict):
        """
        Finds an existing stack in a given list (inventory or room items) that matches
        the item_to_match's stacking key and has space.
        Returns the matching item dictionary (mutable reference) or None.
        """
        if not item_to_match.get("stackable", False):
            return None # Only stackable items can match stacks

        item_stacking_key = self._get_item_stacking_key(item_to_match)
        if item_stacking_key is None:
            return None

        for existing_item in item_list:
            if isinstance(existing_item, dict) and existing_item.get("stackable", False):
                if self._get_item_stacking_key(existing_item) == item_stacking_key:
                    # Check if there's space in the stack
                    current_quantity = existing_item.get("quantity", 0)
                    max_size = existing_item.get("max_stack_size", float('inf')) # Use infinity if no max_stack_size
                    if current_quantity < max_size:
                        return existing_item
        return None

    def set_room_manager(self, room_manager_instance):
        """Sets the RoomManager dependency to resolve circular dependency."""
        self._room_manager = room_manager_instance

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal: {e}")

    # --- Helper Methods (Internal to InventoryService) ---
    def _find_item_info_by_id(self, item_id):
        if not isinstance(item_id, int):
            return None

        inventory_list = self._state_store.get_state_section("inventory")
        if isinstance(inventory_list, list):
            for item in inventory_list:
                if isinstance(item, dict) and item.get("id") == item_id and isinstance(item.get("id"), int):
                    return {
                        "location": "inventory",
                        "location_name": None,
                        "location_id": None,
                        "item_data": item
                    }

        rooms = self._state_store.get_state_section("rooms")
        if isinstance(rooms, list) and self._room_manager: # Ensure room_manager is set
            for room in rooms:
                if isinstance(room, dict) and isinstance(room.get("id"), int) and isinstance(room.get("items"), list):
                    for item in room["items"]:
                        if isinstance(item, dict) and item.get("id") == item_id and isinstance(item.get("id"), int):
                            return {
                                "location": "room",
                                "location_name": room.get("name"),
                                "location_id": room.get("id"),
                                "item_data": item
                            }
        return None

    def _is_valid_item_data(self, item_data, check_id=False):
        if not isinstance(item_data, dict):
            return False, "Item data is not a dictionary."
        if check_id:
            item_id_val = item_data.get('id')
            if item_id_val is None or not isinstance(item_id_val, int):
                return False, f"Item data missing or has invalid 'id' ({item_id_val})."
        required_keys_base = ["name", "descriptions", "static", "type"]
        if not all(key in item_data for key in required_keys_base):
            missing = [key for key in required_keys_base if key not in item_data]
            item_name_for_log = item_data.get('name', 'Unnamed Item')
            item_id_for_log = item_data.get('id', 'unknown')
            return False, f"Item '{item_name_for_log}' (ID:{item_id_for_log}) missing base required keys: {missing}"

        item_name = item_data.get('name', 'Unnamed')
        if not isinstance(item_data["name"], str) or not item_data["name"].strip():
            item_id_for_log = item_data.get('id', 'unknown')
            return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'name' must be a non-empty string."
        descriptions = item_data.get("descriptions", [])
        if not isinstance(descriptions, list) or not all(isinstance(d, str) for d in descriptions):
            item_id_for_log = item_data.get('id', 'unknown')
            return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'descriptions' must be a list of strings."
        if not isinstance(item_data.get("static"), bool):
            item_id_for_log = item_data.get('id', 'unknown')
            return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'static' must be a boolean."
        item_type = item_data.get("type", [])
        item_id_for_log = item_data.get('id', 'unknown')
        if not isinstance(item_type, list):
            return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'type' must be a list, got {type(item_type).__name__}."
        if not item_type:
            return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'type' list cannot be empty."
        for t_val in item_type:
            if t_val not in self.ALLOWED_ITEM_TYPES:
                return False, f"Item '{item_name}' (ID:{item_id_for_log}) has an invalid type '{t_val}' in its type list. Allowed types: {self.ALLOWED_ITEM_TYPES}"

        # --- NEW: Stacking attributes validation for _is_valid_item_data ---
        stackable = item_data.get("stackable", False)
        if not isinstance(stackable, bool): return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'stackable' must be a boolean."
        item_data["stackable"] = stackable # Ensure it's explicitly set if missing

        quantity = item_data.get("quantity", 1)
        if not isinstance(quantity, int) or quantity <= 0: return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'quantity' must be a positive integer."
        item_data["quantity"] = quantity # Ensure it's explicitly set if missing

        max_stack_size = item_data.get("max_stack_size")
        if max_stack_size is not None:
            if not isinstance(max_stack_size, int) or max_stack_size <= 0:
                return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'max_stack_size' must be a positive integer or None."
            if quantity > max_stack_size and stackable:
                print(f"Validation Warning: Item '{item_name}' (ID:{item_id_for_log}) quantity ({quantity}) exceeds max_stack_size ({max_stack_size}). This will be clamped upon creation/transfer.")
                # We'll allow it to pass validation here, but handle clamping in operations.
        # --- END NEW ---

        if "book" in item_type:
            chapters_list = item_data.get("chapters")
            if not isinstance(chapters_list, list):
                item_id_for_log = item_data.get('id', 'unknown')
                return False, f"Book item '{item_name}' (ID:{item_id_for_log}) missing 'chapters' key or 'chapters' is not a list."
            for i, chapter in enumerate(chapters_list):
                if not isinstance(chapter, dict):
                    item_id_for_log = item_data.get('id', 'unknown')
                    return False, f"Book item '{item_name}' (ID:{item_id_for_log}) has invalid chapter entry (not dict) at index {i}."
                chapter_title = chapter.get("title")
                chapter_content = chapter.get("content")
                if chapter_title is None or not isinstance(chapter_title, str) or not chapter_title.strip():
                    item_id_for_log = item_data.get('id', 'unknown')
                    return False, f"Book item '{item_name}' (ID:{item_id_for_log}) has invalid or empty chapter 'title' at index {i}."
                if chapter_content is None or not isinstance(chapter_content, str):
                    item_id_for_log = item_data.get('id', 'unknown')
                    return False, f"Book item '{item_name}' (ID:{item_id_for_log}) has invalid or missing chapter 'content' at index {i}."

        if "consumable" in item_type:
            stats_edit_data = item_data.get("stats_edit")
            item_id_for_log = item_data.get('id', 'unknown')
            if not isinstance(stats_edit_data, dict):
                return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) missing 'stats_edit' key or 'stats_edit' is not a dictionary."
            valid_stats_keys = {"fullness", "hydration", "energy"}
            for key, value in stats_edit_data.items():
                if key not in valid_stats_keys:
                    return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) has unexpected key '{key}' in 'stats_edit'. Valid keys are: {list(valid_stats_keys)}"
                if not isinstance(value, (int, float)):
                    return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) has non-integer or float value for stat '{key}' in 'stats_edit'."
            effects_list = item_data.get("effects")
            if effects_list is None:
                pass
            elif not isinstance(effects_list, list):
                return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) 'effects' key is not a list."
            elif not all(isinstance(effect, str) for effect in effects_list):
                return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) 'effects' list contains non-string values."

        if "seed" in item_type:
            seed_type = item_data.get("plant_type")
            if not isinstance(seed_type, str):
                item_id_for_log = item_data.get('id', 'unknown')
                return False, f"Seed item '{item_name}' (ID:{item_id_for_log}) 'plant_type' key is not a string"

        return True, ""


    def _format_item_for_display(self, item_dict):
        if not isinstance(item_dict, dict):
            return "Invalid Item Data"
        item_id = item_dict.get('id', -1)
        item_name = item_dict.get('name', 'Unnamed Item')
        if not isinstance(item_id, int):
            return f"{item_name} (ID:INVALID)"
        
        # --- NEW: Display quantity for stackable items ---
        quantity = item_dict.get('quantity', 1)
        if item_dict.get('stackable', False) and quantity > 1:
            return f"{item_name} (ID:{item_id:06d}) x{quantity}"
        # --- END NEW ---
        return f"{item_name} (ID:{item_id:06d})"

    # --- Public Inventory Methods ---
    def add_item_description(self, item_id: int, new_description: str) -> str:
        if not isinstance(item_id, int):
            return f"Failed to add description: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."
        if not isinstance(new_description, str) or not new_description.strip():
            return "Failed to add description: New description must be a non-empty string."

        inventory_list = self._state_store.get_state_section("inventory", [])
        if not isinstance(inventory_list, list):
            return "Error: Could not access inventory data to add description."

        found_item = None
        for item_data in inventory_list:
            if isinstance(item_data, dict) and item_data.get("id") == item_id:
                found_item = item_data
                break

        if found_item:
            timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            timed_description = f"{timestamp} {new_description.strip()}"

            descriptions_list = found_item.get("descriptions")
            if not isinstance(descriptions_list, list):
                descriptions_list = []
            descriptions_list.append(timed_description)
            found_item["descriptions"] = descriptions_list

            self._state_store.update_state_section("inventory", inventory_list) # Save updated inventory list
            item_name = found_item.get("name", "Unnamed Item")
            return f"Added description for '{item_name}' (ID: {item_id}) in inventory."
        else:
            return f"Failed to add description: Item with ID {item_id} not found in your inventory."

    def list_items_in_current_room(self, internal=False):
        current_room_id = self._state_store.get_state_section("current_room_id")
        room_data = None
        if self._room_manager:
            room_data = self._room_manager._find_room_by_id(current_room_id)
        else:
            print("Warning: RoomManager not set in InventoryService, cannot list room items.")
            return "Error: Room information not available."

        if room_data:
            room_display = self._room_manager._format_room_for_display(room_data)
            room_items = room_data.get("items", [])
            if isinstance(room_items, list):
                valid_items = [item for item in room_items if self._is_valid_item_data(item, check_id=True)[0]]
                items_display = [self._format_item_for_display(item) for item in valid_items]
                if items_display:
                    if internal:
                        return room_items
                    return f"Items in the {room_display}: {', '.join(items_display)}"
                else:
                    return f"There are no items in the {room_display}."
            else:
                return f"Error: Item list for {room_display} is corrupted."
        else:
            return f"Error: Could not access item list for current room (ID: {current_room_id}). State might be corrupted."

    def get_inventory_items(self, internal=False):
        inventory_list = self._state_store.get_state_section("inventory")
        if isinstance(inventory_list, list):
            valid_items = [item for item in inventory_list if self._is_valid_item_data(item, check_id=True)[0]]
            items_display = [self._format_item_for_display(item) for item in valid_items]
            if items_display:
                if internal:
                    return inventory_list
                return f"Items in your inventory: {', '.join(items_display)}"
            else:
                return "Your inventory is empty."
        else:
            return "Error: Could not access inventory. State might be corrupted."

    def get_item_details(self, item_id: int, internal=False):
        if not isinstance(item_id, int):
            if internal:
                return {"status": "error", "message": f"Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."}
            else:
                return f"Failed to examine: Item ID must be an integer, received '{item_id}'."

        found_item_info = self._find_item_info_by_id(item_id)
        current_room_id = self._state_store.get_state_section("current_room_id")

        if not found_item_info:
            if internal:
                return {"status": "not_found", "message": f"Item with ID '{item_id}' not found anywhere."}
            else:
                return f"You don't see an item with ID '{item_id}' here or in your inventory."

        item_location = found_item_info["location"]
        item_location_id = found_item_info["location_id"]
        item_data = found_item_info["item_data"]

        is_accessible = (item_location == "inventory") or (item_location == "room" and item_location_id == current_room_id)
        is_valid, msg = self._is_valid_item_data(item_data, check_id=True)

        if not is_valid:
            print(f"Warning: Found item ID {item_id} at {item_location} but data is invalid: {msg}. Reporting error.")
            if internal:
                return {"status": "error", "message": f"Found item ID {item_id} but data is corrupted: {msg}", "location": item_location}
            else:
                item_display = self._format_item_for_display(item_data)
                return f"Error: Data for item {item_display} seems corrupted."

        if not is_accessible:
            item_display = self._format_item_for_display(item_data)
            if internal:
                location_desc = "inventory" if item_location == "inventory" else (self._room_manager._format_room_for_display(self._room_manager._find_room_by_id(item_location_id)) if item_location == "room" and self._room_manager else "an unknown location")
                return {"status": "not_accessible", "message": f"Item {item_display} is not in your current location. It is in {location_desc}.", "location": item_location, "location_id": item_location_id}
            else:
                return f"You can only examine items in your current location or inventory. Item {item_display} is not here."

        if internal:
            return {
                "status": "found",
                "details": item_data,
                "location": item_location,
                "location_name": found_item_info["location_name"],
                "location_id": item_location_id
            }
        else:
            item_display = self._format_item_for_display(item_data)
            descriptions = item_data.get("descriptions", [])
            output_string = f"{item_display}\n\n"
            if descriptions and isinstance(descriptions, list) and all(isinstance(d, str) for d in descriptions):
                output_string += "\n".join(descriptions)
            else:
                output_string += "(No description available.)"
            return output_string


    def is_inventory_full(self):
        current_inventory = self._state_store.get_state_section("inventory", [])
        # Inventory is full if the number of distinct item stacks/non-stackable items
        # reaches the maximum limit.
        return len(current_inventory) >= self.MAX_INVENTORY_SLOTS



    def pickup_item(self, item_id: int, quantity_to_pickup: int = 1):
        if not isinstance(item_id, int):
            return f"Failed to pick up: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        item_info = self._find_item_info_by_id(item_id)
        if item_info is None:
            return "Item not found anywhere."

        item_data_in_source = item_info.get("item_data")
        if not item_data_in_source:
            print(f"Warning: item_info for ID {item_id} found but missing 'item_data'. item_info: {item_info}")
            return f"Error: Found item info for ID {item_id} but item data is missing."

        item_display = self._format_item_for_display(item_data_in_source)

        if item_info["location"] == "inventory":
            return f"You already have the {item_display} in your inventory!"

        if item_data_in_source.get("static", False):
            return f"You cannot pick up the {item_display}. It is too big!"

        current_room_id = self._state_store.get_state_section("current_room_id")
        current_room = None
        if self._room_manager:
            current_room = self._room_manager._find_room_by_id(current_room_id)
        else:
            print("Warning: RoomManager not set in InventoryService, cannot pickup from room.")
            return "Error: Room information not available for pickup."

        if not (item_info["location"] == "room" and item_info["location_id"] == current_room_id):
            item_location_room = self._room_manager._find_room_by_id(item_info['location_id']) if self._room_manager else None
            location_display = self._room_manager._format_room_for_display(item_location_room) if item_location_room else f"Unknown Room (ID:{item_info['location_id']})"
            return f"Failed to pick up {item_display}: It is in {location_display}, not here."

        available_in_source = item_data_in_source.get("quantity", 1)
        if quantity_to_pickup <= 0:
             actual_quantity_to_pickup = available_in_source
        else:
            actual_quantity_to_pickup = min(quantity_to_pickup, available_in_source)


        # --- NEW LOGIC: Prepare the item to move and handle splitting ---
        item_to_move = None
        if actual_quantity_to_pickup < available_in_source:
            # This is a partial pickup (splitting a stack)
            # 1. Create the remainder that will be left in the room
            remainder_item = item_data_in_source.copy()
            remainder_item["id"] = self._state_store.get_next_item_id()
            remainder_item["quantity"] = available_in_source - actual_quantity_to_pickup
            
            # 2. Add the new remainder stack to the room
            current_room["items"].append(remainder_item)

            # 3. Modify the original item_data to be the part that is picked up
            item_data_in_source["quantity"] = actual_quantity_to_pickup
            item_to_move = item_data_in_source # This is the original dict, now modified

            # 4. Remove the original item from the room list (it will be added to inventory later)
            current_room["items"][:] = [item for item in current_room["items"] if item.get("id") != item_id]
        else:
            # This is a full pickup (taking the whole stack or non-stackable)
            item_to_move = item_data_in_source
            # Remove the item from the room list completely
            current_room["items"][:] = [item for item in current_room["items"] if item.get("id") != item_id]
        # --- END NEW LOGIC ---

        # Retrieve mutable copy of inventory list
        inventory_list = self._state_store.get_state_section("inventory", [])
        
        # --- MODIFIED: Stacking logic now operates on `item_to_move` ---
        transfer_successful = False
        remaining_to_pickup = item_to_move.get("quantity", 1)
        messages = []

        if item_to_move.get("stackable", False):
            target_stack = self._find_matching_stack_in_list(inventory_list, item_to_move)
            if target_stack:
                space_in_target = target_stack.get("max_stack_size", float('inf')) - target_stack.get("quantity", 0)
                amount_to_transfer = min(remaining_to_pickup, space_in_target)

                if amount_to_transfer > 0:
                    target_stack["quantity"] += amount_to_transfer
                    remaining_to_pickup -= amount_to_transfer
                    messages.append(f"Added {amount_to_transfer} to an existing stack of {self._format_item_for_display(target_stack)}.")
                    transfer_successful = True
            
            # If there's still quantity to add (because the first stack filled up or no stack existed)
            # create a new stack in the inventory.
            if remaining_to_pickup > 0:
                if self.is_inventory_full():
                    messages.append(f"Your inventory is full! Could not pick up the remaining {remaining_to_pickup} items.")
                    # --- NEW LOGIC: Put the item back in the room if it couldn't be placed ---
                    # Note: This is a complex recovery step. For now, we'll let it "drop" on the floor.
                    # A more robust system might try to re-merge it with the remainder stack.
                    current_room["items"].append(item_to_move) # Effectively drops it back
                else:
                    # The item_to_move already has the correct ID and quantity. Just add it.
                    inventory_list.append(item_to_move)
                    messages.append(f"Picked up a new stack of {self._format_item_for_display(item_to_move)}.")
                    remaining_to_pickup = 0 # All of item_to_move is now in inventory
                    transfer_successful = True
        else: # Not stackable
            if self.is_inventory_full():
                messages.append(f"Your inventory is full! You cannot pick up the item.")
                current_room["items"].append(item_to_move) # Put it back
            else:
                inventory_list.append(item_to_move)
                transfer_successful = True
                messages.append(f"Picked up the {self._format_item_for_display(item_to_move)}.")

        # --- MODIFIED: State update and signaling ---
        if transfer_successful:
            rooms_list = self._state_store.get_state_section("rooms", []) # Get latest reference before update
            self._state_store.update_state_section("rooms", rooms_list)
            self._state_store.update_state_section("inventory", inventory_list)

            list_room_items_names, list_inventory_item_names = self.list_inventories(formatted=True)
            self._send_signal({f"type": "room_inventory", "item_list": list_room_items_names})
            self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/hand_up_icon.png"})
            return " ".join(messages)
        else:
            # If the transfer failed for some reason, we need to ensure the state is consistent.
            # The item was already removed from the room, so if it wasn't added to inventory, it's gone.
            # The logic above already puts it back if inventory is full.
            return f"Failed to pick up {item_display}. " + " ".join(messages)
####
    def list_inventories(self, formatted=False):
        current_room_id = self._state_store.get_state_section("current_room_id")
        room_data = None
        if self._room_manager:
            room_data = self._room_manager._find_room_by_id(current_room_id)

        list_room_items_names = []
        if room_data and isinstance(room_data.get("items"), list):
            for item in room_data["items"]:
                if formatted:
                    name=self._format_item_for_display(item)
                    #print(f"DEBUG FORMAT ITEMS {name}")
                else:
                    name = item.get("name")
                if name:
                    list_room_items_names.append(name)
                    

        inventory_list = self._state_store.get_state_section("inventory", [])
        list_inventory_item_names = []
        if isinstance(inventory_list, list):
            for item in inventory_list:
                name = self._format_item_for_display(item)
                if name:
                    list_inventory_item_names.append(name)
        return list_room_items_names, list_inventory_item_names


    def drop_item(self, item_id: int, quantity_to_drop: int = 1):
        if not isinstance(item_id, int):
            return f"Failed to drop: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            return f"Failed to drop: Item with ID '{item_id}' not found anywhere."

        item_data_in_source = item_info["item_data"]
        item_display = self._format_item_for_display(item_data_in_source)

        current_room_id = self._state_store.get_state_section("current_room_id")
        current_room = None
        current_room_display = f"Unknown Room (ID:{current_room_id})"
        if self._room_manager:
            current_room = self._room_manager._find_room_by_id(current_room_id)
            if current_room:
                current_room_display = self._room_manager._format_room_for_display(current_room)

        if item_info["location"] != "inventory":
            return f"Failed to drop {item_display}: It is not in your inventory."

        if item_data_in_source.get("static", False):
            return f"You cannot drop the {item_display}. It is a static item."
        
        if not current_room or not isinstance(current_room.get("items"), list):
             return f"Error: Cannot drop {item_display} here. Current room ({current_room_display}) has corrupted item data."

        available_in_source = item_data_in_source.get("quantity", 1)
        if quantity_to_drop <= 0:
            actual_quantity_to_drop = available_in_source # Drop the whole stack by default
        else:
            actual_quantity_to_drop = min(quantity_to_drop, available_in_source)

        # Retrieve mutable copies of lists
        inventory_list = self._state_store.get_state_section("inventory", [])
        rooms_list = self._state_store.get_state_section("rooms", [])

        # --- NEW LOGIC: Prepare the item to move and handle splitting from inventory ---
        item_to_move = None
        if actual_quantity_to_drop < available_in_source:
            # This is a partial drop (splitting a stack)
            # 1. Create the remainder that will be left in the inventory
            remainder_item = item_data_in_source.copy()
            remainder_item["id"] = self._state_store.get_next_item_id()
            remainder_item["quantity"] = available_in_source - actual_quantity_to_drop
            
            # 2. Add the new remainder stack to the inventory
            inventory_list.append(remainder_item)

            # 3. Modify the original item_data to be the part that is dropped
            item_data_in_source["quantity"] = actual_quantity_to_drop
            item_to_move = item_data_in_source

            # 4. Remove the original item from the inventory list (it will be added to the room later)
            inventory_list[:] = [item for item in inventory_list if item.get("id") != item_id]
        else:
            # This is a full drop (dropping the whole stack or non-stackable)
            item_to_move = item_data_in_source
            # Remove the item from the inventory list completely
            inventory_list[:] = [item for item in inventory_list if item.get("id") != item_id]
        # --- END NEW LOGIC ---

        # --- MODIFIED: Stacking logic in the room now operates on `item_to_move` ---
        transfer_successful = False
        remaining_to_drop = item_to_move.get("quantity", 1)
        messages = []

        if item_to_move.get("stackable", False):
            # Try to add to an existing stack in the room
            target_stack = self._find_matching_stack_in_list(current_room["items"], item_to_move)
            if target_stack:
                space_in_target = target_stack.get("max_stack_size", float('inf')) - target_stack.get("quantity", 0)
                amount_to_transfer = min(remaining_to_drop, space_in_target)

                if amount_to_transfer > 0:
                    target_stack["quantity"] += amount_to_transfer
                    remaining_to_drop -= amount_to_transfer
                    messages.append(f"Added {amount_to_transfer} to an existing stack of {self._format_item_for_display(target_stack)} in {current_room_display}.")
                    # The `item_to_move` has been merged, so it's conceptually gone.
                    item_to_move["quantity"] -= amount_to_transfer # Track what's left
                    transfer_successful = True

            # If there's still quantity to drop, create a new stack in the room
            if remaining_to_drop > 0:
                # The item_to_move already has the correct ID and the remaining quantity. Just add it.
                current_room["items"].append(item_to_move)
                messages.append(f"Dropped a new stack of {self._format_item_for_display(item_to_move)} in {current_room_display}.")
                remaining_to_drop = 0
                transfer_successful = True
        else: # Not stackable, drop as a single item
            # The item_to_move is the single item with the correct ID.
            current_room["items"].append(item_to_move)
            remaining_to_drop = 0
            transfer_successful = True
            messages.append(f"Dropped the {self._format_item_for_display(item_to_move)} in {current_room_display}.")

        # --- MODIFIED: State update is now simpler ---
        if transfer_successful:
            # The inventory and room lists were already modified directly. Now we just save them.
            self._state_store.update_state_section("inventory", inventory_list)
            self._state_store.update_state_section("rooms", rooms_list)

            list_room_items_names, list_inventory_item_names = self.list_inventories(formatted=True)
            self._send_signal({f"type": "room_inventory", "item_list": list_room_items_names})
            self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/hand_down_icon.png"})
            return f"You dropped items. " + " ".join(messages)
        else:
            # If the transfer somehow failed, we need to put the item back in the inventory to prevent item loss.
            inventory_list.append(item_to_move)
            self._state_store.update_state_section("inventory", inventory_list)
            return f"Failed to drop {item_display}. " + " ".join(messages)

    def create_item(self, target_location: str, target_location_id: int | None, item_creation_data: dict | list[dict], internal=False, quantity=1):
        #print(f"DEBUG: Starting create_item. target_location: '{target_location}', target_location_id: '{target_location_id}', quantity: {quantity}, internal: {internal}")

        failed_items_info = []
        messages = []
        overall_successful_creation_count = 0
        
        if not isinstance(quantity, int) or quantity <= 0:
            msg = f"Failed to create item(s): 'quantity' must be a positive integer, received '{quantity}' ({type(quantity).__name__})."
            print(f"DEBUG: Quantity validation failed: {msg}")
            if internal: return [] if isinstance(item_creation_data, list) else False
            return msg

        item_templates_to_create = []
        if isinstance(item_creation_data, dict):
            item_templates_to_create = [item_creation_data]
        elif isinstance(item_creation_data, list):
            item_templates_to_create = item_creation_data
        else:
            msg = f"Failed to create item(s): item_creation_data must be a dict or a list of dicts, received {type(item_creation_data).__name__}."
            print(f"DEBUG: Invalid item_creation_data type: {msg}")
            if internal: return [] if isinstance(item_creation_data, list) else False
            return msg

        if not item_templates_to_create:
             msg = "No valid item data provided after applying quantity."
             print(f"DEBUG: No data list templates after initial processing: {msg}")
             if internal: return [] if isinstance(item_creation_data, list) else []
             return msg

        # Fetch current state lists to modify
        inventory_list = self._state_store.get_state_section("inventory", [])
        rooms_list = self._state_store.get_state_section("rooms", [])

        target_location_lower = target_location.strip().lower()
        target_room = None
        if target_location_lower == "room":
            if not isinstance(target_location_id, int) or not self._room_manager:
                return f"Target room ID must be an integer when creating item(s) in a room, received '{target_location_id}' ({type(target_location_id).__name__})."
            target_room = self._room_manager._find_room_by_id(target_location_id)
            if not target_room or not isinstance(target_room.get("items"), list):
                return f"Target room with ID '{target_location_id}' not found or room data corrupted."
            
        elif target_location_lower == "inventory":
            if not isinstance(inventory_list, list):
                 return "Inventory state corrupted. Cannot create items."
        else:
            return f"Invalid target location '{target_location}'. Must be 'room' or 'inventory'."


        successfully_created_ids = []

        for item_template_idx, original_item_template in enumerate(item_templates_to_create):
            item_data_template = original_item_template.copy()

            # Validate the template before trying to create it
            is_valid, error_msg = self._is_valid_item_data(item_data_template, check_id=False)
            if not is_valid:
                display_name = item_data_template.get('name', 'Unnamed Item') if isinstance(item_data_template, dict) else 'Invalid Data'
                failed_items_info.append((display_name, f"Template validation failed: {error_msg}"))
                continue

            # Check if a static item is trying to be created in inventory (which makes no sense conceptually)
            if item_data_template.get("static", False) and target_location_lower == "inventory":
                 failed_items_info.append((self._format_item_for_display(item_data_template), "Cannot create a static item directly in inventory."))
                 continue

            current_quantity_to_add = quantity # The total quantity for this template type

            while current_quantity_to_add > 0:
                created_this_iteration = False

                if item_data_template.get("stackable", False):
                    # Try to find an existing stack to add to
                    target_list = inventory_list if target_location_lower == "inventory" else (target_room["items"] if target_room else [])
                    existing_stack = self._find_matching_stack_in_list(target_list, item_data_template)

                    if existing_stack:
                        space_in_target = existing_stack.get("max_stack_size", float('inf')) - existing_stack.get("quantity", 0)
                        amount_to_transfer = min(current_quantity_to_add, space_in_target)

                        if amount_to_transfer > 0:
                            # Safely get the current quantity, defaulting to 0 if the key is missing
                            current_qty = existing_stack.get("quantity", 0)
                            # Set the new, updated quantity
                            existing_stack["quantity"] = current_qty + amount_to_transfer
                            
                            current_quantity_to_add -= amount_to_transfer
                            overall_successful_creation_count += amount_to_transfer
                            successfully_created_ids.append(existing_stack["id"]) # Add existing ID to list for tracking
                            created_this_iteration = True
                            messages.append(f"Added {amount_to_transfer} units to existing stack {self._format_item_for_display(existing_stack)}.")

                    if current_quantity_to_add > 0: # If still units left after trying to merge
                        # Check for inventory full only if creating a NEW stack in inventory
                        if target_location_lower == "inventory" and self.is_inventory_full():
                            failed_items_info.append((self._format_item_for_display(item_data_template), f"Inventory full, could not create new stack for {current_quantity_to_add} units."))
                            current_quantity_to_add = 0 # Stop trying to add this template
                            break # Break out of while loop for this template

                        # Create a new stack
                        new_item_id = self._state_store.get_next_item_id()
                        new_stack_item = item_data_template.copy()
                        new_stack_item["id"] = new_item_id
                        new_stack_item["quantity"] = current_quantity_to_add # Add remaining quantity
                        # --- CORRECTED: Retain original static flag ---
                        # new_stack_item["static"] = (target_location_lower == "room") # REMOVED THIS LINE
                        # The 'static' flag is part of the item_data_template already and shouldn't change.
                        # --- END CORRECTED ---

                        # Clamp quantity if it exceeds max_stack_size (should ideally be handled by _is_valid_item_data but as a fallback)
                        max_size = new_stack_item.get("max_stack_size", float('inf'))
                        if new_stack_item["quantity"] > max_size:
                            original_clamped_qty = new_stack_item["quantity"]
                            new_stack_item["quantity"] = max_size
                            failed_items_info.append((self._format_item_for_display(new_stack_item), f"Quantity ({original_clamped_qty}) for new stack exceeded max_stack_size ({max_size}); clamped to {max_size}. Remaining units lost."))
                            
                        if target_location_lower == "inventory":
                            inventory_list.append(new_stack_item)
                        elif target_room:
                            target_room["items"].append(new_stack_item)
                        
                        overall_successful_creation_count += new_stack_item["quantity"]
                        successfully_created_ids.append(new_stack_item["id"])
                        messages.append(f"Created a new stack of {self._format_item_for_display(new_stack_item)}.")
                        current_quantity_to_add = 0 # All handled for this template in this iteration
                        created_this_iteration = True

                else: # Not stackable item
                    if target_location_lower == "inventory" and self.is_inventory_full():
                        failed_items_info.append((self._format_item_for_display(item_data_template), f"Inventory full, could not create new non-stackable item."))
                        current_quantity_to_add = 0 # Stop trying to add this template
                        break # Break out of while loop for this template
                    
                    new_item_id = self._state_store.get_next_item_id()
                    new_single_item = item_data_template.copy()
                    new_single_item["id"] = new_item_id
                    new_single_item["quantity"] = 1 # Non-stackable items always have quantity 1
                    # --- CORRECTED: Retain original static flag ---
                    # new_single_item["static"] = (target_location_lower == "room") # REMOVED THIS LINE
                    # --- END CORRECTED ---

                    if target_location_lower == "inventory":
                        inventory_list.append(new_single_item)
                    elif target_room:
                        target_room["items"].append(new_single_item)
                    
                    overall_successful_creation_count += 1
                    successfully_created_ids.append(new_single_item["id"])
                    messages.append(f"Created {self._format_item_for_display(new_single_item)}.")
                    current_quantity_to_add -= 1 # One unit processed
                    created_this_iteration = True
                
                if not created_this_iteration and current_quantity_to_add > 0:
                    failed_items_info.append((self._format_item_for_display(item_data_template), f"Failed to place remaining {current_quantity_to_add} units (unknown reason)."))
                    current_quantity_to_add = 0 # Prevent infinite loop

        self._state_store.update_state_section("inventory", inventory_list)
        self._state_store.update_state_section("rooms", rooms_list)

        if overall_successful_creation_count > 0:
            list_room_items_names, list_inventory_item_names = self.list_inventories(formatted=True)
            self._send_signal({f"type": "room_inventory", "item_list": list_room_items_names})
            self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})

        final_report_messages = []
        if overall_successful_creation_count > 0:
            item_plural = "item" if overall_successful_creation_count == 1 else "items"
            final_report_messages.append(f"Successfully created {overall_successful_creation_count} {item_plural}.")
        
        if failed_items_info:
            grouped_failures = {}
            for name, reason in failed_items_info:
                key = (name, reason)
                grouped_failures[key] = grouped_failures.get(key, 0) + 1
            
            failure_summaries = []
            for (name, reason), count in grouped_failures.items():
                if count > 1: failure_summaries.append(f"- {count}x {name}: {reason}")
                else: failure_summaries.append(f"- {name}: {reason}")
            
            failed_plural = "item" if len(failed_items_info) == 1 else "items"
            final_report_messages.append(f"{len(failed_items_info)} {failed_plural} failed to be created or placed:\n" + "\n".join(failure_summaries))

        if not final_report_messages:
            return "No item creation attempts were processed."
        
        return "\n".join(final_report_messages)


    def trash_item(self, item_id: int, confirm: bool, quantity_to_trash: int = 1) -> str:
        if confirm:
            if not isinstance(item_id, int):
                return f"Failed to trash: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

            item_info = self._find_item_info_by_id(item_id)
            if not item_info:
                return f"Failed to trash item: Item with ID '{item_id}' not found anywhere."

            item_data = item_info["item_data"]
            item_display = self._format_item_for_display(item_data)
            location = item_info["location"]

            if location != "inventory":
                if location == "room" and self._room_manager:
                    room_name = self._room_manager.get_room_name(item_info['location_id'])
                    return f"Failed to trash {item_display}: It is not in your inventory, it is in the {room_name}."
                else:
                    return f"Failed to trash {item_display}: It is not in your inventory."
            
            # If the item is static (e.g., a non-movable piece of furniture that somehow ended up in inventory),
            # prevent it from being trashed. This is a failsafe.
            if item_data.get("static", False):
                return f"You cannot trash the {item_display}. It is a static item."

            # Determine actual quantity to trash
            available_quantity = item_data.get("quantity", 1)
            if quantity_to_trash <= 0 or quantity_to_trash > available_quantity:
                actual_quantity_to_trash = available_quantity # Trash the whole stack/item by default
            else:
                actual_quantity_to_trash = quantity_to_trash

            removal_result_status, removal_message = self.remove_item(item_id, actual_quantity_to_trash, internal=True)
            
            if removal_result_status: # True indicates success
                self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/trashcan_icon.png"})
                return f"You trashed {actual_quantity_to_trash} unit(s) of {item_display}. {removal_message}"
            else:
                print(f"Warning: trash_item called remove_item for {item_display} (ID:{item_id}) but it failed: {removal_message}")
                return f"Failed to trash {item_display}: {removal_message}"
        else:
            return f"Destruction of item {item_id} cancelled."

    def remove_item(self, item_id: int,  internal=False, quantity_to_remove: int = 1):
        # Returns (success_bool, message_string)
        if not isinstance(item_id, int):
            if internal: return (False, f"Item ID must be an integer, received '{item_id}' ({type(item_id).__name__}).")
            return f"Failed to remove: Item ID must be an integer, received '{item_id}'."

        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            if internal: return (False, f"Item with ID '{item_id}' not found anywhere.")
            return f"Failed to remove item: Item with ID '{item_id}' not found anywhere."

        item_data_to_remove = item_info["item_data"] # This is the actual dict in the list, changes will persist
        item_display = self._format_item_for_display(item_data_to_remove)
        location = item_info["location"]
        location_id = item_info["location_id"]
        
        # If the item is static, it should not be removable by the player through general means.
        # This is a strong failsafe.
        if item_data_to_remove.get("static", False):
            if internal: return (False, f"Cannot remove {item_display}. It is a static item.")
            return f"Failed to remove {item_display}: It is a static item."


        available_quantity = item_data_to_remove.get("quantity", 1)
        if quantity_to_remove <= 0 or quantity_to_remove > available_quantity:
            actual_quantity_to_remove = available_quantity # Remove the whole stack/item by default
        else:
            actual_quantity_to_remove = quantity_to_remove

        message_suffix = f" ({actual_quantity_to_remove} unit(s))" if actual_quantity_to_remove > 1 else ""
        
        location_desc = "an unknown location"
        
        if location == "inventory":
            inventory_list = self._state_store.get_state_section("inventory")
            if isinstance(inventory_list, list):
                if item_data_to_remove.get("stackable", False) and item_data_to_remove["quantity"] > actual_quantity_to_remove:
                    item_data_to_remove["quantity"] -= actual_quantity_to_remove
                    message = f"Removed {actual_quantity_to_remove} unit(s) from {item_display} in your inventory. Remaining quantity: {item_data_to_remove['quantity']}."
                else:
                    inventory_list[:] = [item for item in inventory_list if item.get("id") != item_id] # Remove the entire stack
                    message = f"Removed {item_display} from your inventory."
                
                self._state_store.update_state_section("inventory", inventory_list)
                location_desc = "your inventory"
            else:
                if internal: return (False, "Cannot remove item from inventory, inventory state corrupted.")
                return "Error: Cannot remove item from inventory, inventory state corrupted."

        elif location == "room":
            rooms_list = self._state_store.get_state_section("rooms")
            if not self._room_manager:
                if internal: return (False, "RoomManager not set in InventoryService, cannot remove from room.")
                return "Error: RoomManager not set in InventoryService, cannot remove from room."

            room_data = self._room_manager._find_room_by_id(location_id)
            if room_data and isinstance(room_data.get("items"), list):
                if item_data_to_remove.get("stackable", False) and item_data_to_remove["quantity"] > actual_quantity_to_remove:
                    item_data_to_remove["quantity"] -= actual_quantity_to_remove
                    message = f"Removed {actual_quantity_to_remove} unit(s) from {item_display} in {self._room_manager._format_room_for_display(room_data)}. Remaining quantity: {item_data_to_remove['quantity']}."
                else:
                    room_data["items"][:] = [item for item in room_data["items"] if isinstance(item, dict) and item.get("id") != item_id] # Remove entire stack
                    message = f"Removed {item_display} from {self._room_manager._format_room_for_display(room_data)}."
                
                self._state_store.update_state_section("rooms", rooms_list) # Save the overall rooms list
                location_desc = f"the {self._room_manager._format_room_for_display(room_data)}"
            else:
                if internal: return (False, f"Cannot remove item from room '{location_id}', room data corrupted.")
                return f"Error: Cannot remove item from room '{location_id}', room data corrupted."
        else:
            if internal: return (False, f"Failed to remove item {item_display}: Unknown location type '{location}'.")
            return f"Failed to remove item {item_display}: Unknown location type '{location}'."

        list_room_items_names, list_inventory_item_names = self.list_inventories(formatted=True)
        self._send_signal({f"type": "room_inventory", "item_list": list_room_items_names})
        self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})

        if internal: return (True, message)
        return message