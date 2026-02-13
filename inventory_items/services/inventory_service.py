
# services/inventory_service.py
from utils.loc_datetime import datetime

import json


from inventory_items.item_pydantic_models import validate_item_dict, ignore_fingerprint_keys

import copy



class InventoryService:
    MAX_INVENTORY_SLOTS = 30

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
            if k not in ignore_fingerprint_keys: # We need to decide what we will ignore
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

    def _is_valid_item_data(self, item_data: dict, check_id: bool = False) -> tuple[bool, str]:
        _, error = validate_item_dict(item_data, check_id=check_id)
        if error:
            return False, error
        return True, ""


    def _format_item_for_display(self, item_dict, show_quantity=True):
        if not isinstance(item_dict, dict):
            return "Invalid Item Data"
        item_id = item_dict.get('id', -1)
        item_name = item_dict.get('name', 'Unnamed Item')
        if not isinstance(item_id, int):
            return f"{item_name} (ID:INVALID)"
        
        # Only show quantity if requested and conditions are met
        quantity = item_dict.get('quantity', 1)
        if show_quantity and item_dict.get('stackable', False) and quantity > 1:
            return f"{item_name} (ID:{item_id:06d}) x{quantity}"
        
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
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            timed_description = f"{timestamp} {new_description.strip()}"

            descriptions_list_copy = copy.deepcopy(found_item.get("descriptions"))
            if not isinstance(descriptions_list_copy, list):
                descriptions_list_copy = []
            descriptions_list_copy.append(timed_description)

            # Don't touch found_item here — let set_item_attribute handle the write
            message = self.set_item_attribute(item_id, "descriptions", descriptions_list_copy)

            item_name = found_item.get("name", "Unnamed Item")
            return f"Added description for '{item_name}' (ID: {item_id}) in inventory. {message}"
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
                    if internal:
                        return []
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
                if internal:
                    return []
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
            return f"Failed to pick up {item_display}: It is not here."

        available_in_source = item_data_in_source.get("quantity", 1)
        if quantity_to_pickup <= 0:
            actual_quantity_to_pickup = available_in_source
        else:
            actual_quantity_to_pickup = min(quantity_to_pickup, available_in_source)

        # --- UPDATED LOGIC: Keep original ID in room, create new ID for inventory ---
        item_to_move = None
        if actual_quantity_to_pickup < available_in_source:
            # This is a partial pickup (splitting a stack)
            # 1. Keep the original item in the room with reduced quantity
            item_data_in_source["quantity"] = available_in_source - actual_quantity_to_pickup
            
            # 2. Create a NEW item for the inventory with a new ID
            item_to_move = item_data_in_source.copy()
            item_to_move["id"] = self._state_store.get_next_item_id()
            item_to_move["quantity"] = actual_quantity_to_pickup
            
            # Note: The original item stays in the room's items list with its original ID
        else:
            # This is a full pickup (taking the whole stack or non-stackable)
            # Keep the original ID when moving the entire stack
            item_to_move = item_data_in_source
            # Remove the item from the room list completely
            current_room["items"][:] = [item for item in current_room["items"] if item.get("id") != item_id]
        # --- END UPDATED LOGIC ---

        # Retrieve mutable copy of inventory list
        inventory_list = self._state_store.get_state_section("inventory", [])
        
        # --- Stacking logic now operates on `item_to_move` ---
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
                    # Put the item back in the room if it couldn't be placed
                    current_room["items"].append(item_to_move)
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

        # --- State update and signaling ---
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

            # 1. Get the Master Lists (The actual lists we will save back to the store)
            inventory_list = self._state_store.get_state_section("inventory", [])
            rooms_list = self._state_store.get_state_section("rooms", [])
            current_room_id = self._state_store.get_state_section("current_room_id")

            # 2. Find the Source Item DIRECTLY in the inventory_list
            # This prevents "reference disconnects" where we modify a copy but save the original
            source_item = next((item for item in inventory_list if item.get("id") == item_id), None)

            if not source_item:
                # Fallback: check if it's in the room just to give a better error
                return f"Failed to drop: Item with ID '{item_id}' not found in your inventory."

            # 3. Find the Target Room DIRECTLY in the rooms_list
            target_room = next((r for r in rooms_list if r.get("id") == current_room_id), None)
            if not target_room:
                return f"Error: Could not access current room (ID: {current_room_id})."
            
            target_room_name = target_room.get("name", "Unknown Room")
            item_display = self._format_item_for_display(source_item)

            # 4. Calculate Quantities
            available_quantity = source_item.get("quantity", 1)
            if quantity_to_drop <= 0:
                actual_quantity_to_drop = available_quantity
            else:
                actual_quantity_to_drop = min(quantity_to_drop, available_quantity)

            # 5. Handle Splitting / Moving
            item_to_drop = None

            if actual_quantity_to_drop < available_quantity:
                # PARTIAL DROP:
                # A. Modify the item in the inventory IN PLACE (keeping the original ID there)
                source_item["quantity"] -= actual_quantity_to_drop
                
                # B. Create a COPY for the room (giving it a new ID)
                item_to_drop = source_item.copy()
                item_to_drop["id"] = self._state_store.get_next_item_id()
                item_to_drop["quantity"] = actual_quantity_to_drop
            else:
                # FULL DROP:
                # A. Use the original item
                item_to_drop = source_item
                # B. Remove it strictly from the list we are holding
                inventory_list.remove(source_item)

            # 6. Add to Room (Stacking Logic)
            transfer_successful = False
            remaining_to_drop = item_to_drop.get("quantity", 1)
            messages = []

            if item_to_drop.get("stackable", False):
                # Pass target_room["items"] directly so we modify the list inside rooms_list
                target_stack = self._find_matching_stack_in_list(target_room["items"], item_to_drop)
                
                if target_stack:
                    space_in_target = target_stack.get("max_stack_size", float('inf')) - target_stack.get("quantity", 0)
                    amount_to_transfer = min(remaining_to_drop, space_in_target)

                    if amount_to_transfer > 0:
                        target_stack["quantity"] += amount_to_transfer
                        remaining_to_drop -= amount_to_transfer
                        # We don't really need to update item_to_drop['quantity'] here as it merges, 
                        # but it helps for debugging logic if needed.
                        messages.append(f"Added {amount_to_transfer} to an existing stack of {self._format_item_for_display(target_stack)} in {target_room_name}.")
                        transfer_successful = True

                if remaining_to_drop > 0:
                    # Update the quantity if some was merged but not all
                    item_to_drop["quantity"] = remaining_to_drop
                    target_room["items"].append(item_to_drop)
                    messages.append(f"Dropped a new stack of {self._format_item_for_display(item_to_drop)} in {target_room_name}.")
                    transfer_successful = True
            else:
                target_room["items"].append(item_to_drop)
                messages.append(f"Dropped the {self._format_item_for_display(item_to_drop)} in {target_room_name}.")
                transfer_successful = True

            # 7. Persist Changes
            if transfer_successful:
                self._state_store.update_state_section("inventory", inventory_list)
                self._state_store.update_state_section("rooms", rooms_list)

                list_room_items_names, list_inventory_item_names = self.list_inventories(formatted=True)
                self._send_signal({f"type": "room_inventory", "item_list": list_room_items_names})
                self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})
                self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/hand_down_icon.png"})
                return f"You dropped items. " + " ".join(messages)
            else:
                # Recovery: If logic failed (unlikely), restore inventory
                if actual_quantity_to_drop >= available_quantity:
                    inventory_list.append(item_to_drop)
                else:
                    source_item["quantity"] += actual_quantity_to_drop
                return f"Failed to drop {item_display}."
    
    def create_item(self, target_location: str, target_location_id: int | None, item_creation_data: dict | list[dict], internal=False, quantity=1):
        print(f"DEBUG: Starting create_item. target_location: '{target_location}', target_location_id: '{target_location_id}', quantity: {quantity}, internal: {internal}")

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
            item_data_template.setdefault("stackable", False)
            item_data_template.setdefault("quantity", 1)
            # Validate the template before trying to create it
            is_valid, error_msg = self._is_valid_item_data(item_data_template, check_id=False)
            if not is_valid:
                display_name = item_data_template.get('name', 'Unnamed Item') if isinstance(item_data_template, dict) else 'Invalid Data'
                failed_items_info.append((display_name, f"Template validation failed: {error_msg}"))
                continue

            # # Check if a static item is trying to be created in inventory (which makes no sense conceptually) # We now allow it to retain its static flag for items like furniture placed in inventory
            # if item_data_template.get("static", False) and target_location_lower == "inventory":
            #      failed_items_info.append((self._format_item_for_display(item_data_template), "Cannot create a static item directly in inventory."))
            #      continue

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
        
        if internal:
            return successfully_created_ids # Return the list of IDs for internal calls
        
        final_items_list=[]
        for item_id in successfully_created_ids:
            item_info=self._find_item_info_by_id(item_id)
            final_items_list.append(self._format_item_for_display(item_info["item_data"]))

        final_report_messages.append("\n".join(final_items_list))
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
            # if item_data.get("static", False):
            #     return f"You cannot trash the {item_display}. It is a static item."

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
        # if item_data_to_remove.get("static", False):
        #     if internal: return (False, f"Cannot remove {item_display}. It is a static item.")
        #     return f"Failed to remove {item_display}: It is a static item."


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

    def persist_item_changes(self, item_id: int) -> str | None:
        """
        Persists changes made to an item's data to the central state store.
        Finds the item by ID, determines its location, and updates the appropriate state section.
        Returns None on success, or an error message string on failure.
        """
        item_id = int(item_id)
        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            return f"Error: Item {item_id} moved or lost during operation."

        location = item_info["location"]
        
        if location == "inventory":
            inventory_list = self._state_store.get_state_section("inventory", [])
            # The item data in inventory_list is a reference, so it might already be updated if modified in place.
            # We trigger the update on the store to ensure persistence (e.g. writing to file).
            self._state_store.update_state_section("inventory", inventory_list)
        elif location == "room":
            rooms_list = self._state_store.get_state_section("rooms", [])
            self._state_store.update_state_section("rooms", rooms_list)
        else:
            return f"Error: Item in unmanageable location: {location}"
            
        return None

    def get_validated_item_data(self, item_id: int, required_type: str = None) -> tuple[dict | None, str | None]:
        """
        Retrieves item data by ID and validates it.
        Optionally checks if the item has a specific type.
        Returns (item_data, None) on success, or (None, error_message) on failure.
        """
        item_id = int(item_id)
        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            return None, f"Item {item_id} not found."

        item_data = item_info["item_data"]
        
        if required_type:
            if required_type not in item_data.get("type", []):
                return None, f"Item {item_id} is not a {required_type}."
        
        return item_data, None



    def validate_item_data(self, item_id, expected_type, expected_loc): 
        """
        Args:
            expected_loc: STRING, "room", "inventory"

        """
        item_id = int(item_id)
        item_deets=self.get_item_details(item_id, internal=True)

        is_valid=False

        # 3. Check the status and location of the item based on the returned dictionary
        if item_deets["status"] == "found":
            # Item was found, now check its location and type
            item_data = item_deets["details"] # Get the actual item data dict
            item_location = item_deets["location"]

            if item_location == expected_loc:
                item_type_list = item_data.get("type", [])
                
                if expected_type in item_type_list:
                    # Item is found, in the expected location, and of the expected type - looks good!
                    is_valid=True
        
        return is_valid
        

# ── New helper ──────────────────────────────────────────────────────────

    def _apply_nested_set(self, data: dict, path: list[str] | None, key: str, value) -> None:
        """
        Traverse *path* into *data* (creating intermediate dicts as needed),
        then set data[key] = value at that level.

        Examples
        --------
        _apply_nested_set(item, None,                    "name",     "Bob")
          → item["name"] = "Bob"

        _apply_nested_set(item, ["dispenser_state"],     "contents", {...})
          → item["dispenser_state"]["contents"] = {...}

        _apply_nested_set(item, ["a", "b"],              "c",        42)
          → item["a"]["b"]["c"] = 42
        """
        target = data
        for segment in (path or []):
            if not isinstance(target.get(segment), dict):
                target[segment] = {}
            target = target[segment]
        target[key] = value

    # ── Modified method signature ────────────────────────────────────────────

    def set_item_attribute(self, item_id: int, key: str, value, quantity: int = 1,
                           path: list[str] | None = None) -> str:
        """
        Modifies a single attribute (key/value) on one or more units of an item
        stack, then recalculates stacking state.

        If *path* is provided the write is applied at a nested location inside
        the item dict.  For example::

            set_item_attribute(id, "contents", new_dict, path=["dispenser_state"])

        writes ``item_data["dispenser_state"]["contents"] = new_dict`` instead
        of touching the top-level key directly.

        The stacking-fingerprint logic only considers the *top-level* key when
        path is None; when path is provided the fingerprint comparison uses the
        top-level segment (path[0]) so that nested writes on non-stacking keys
        remain fast-pathed correctly.

        Args:
            item_id:  The ID of the item (or stack) to modify.
            key:      The attribute key to set (at the leaf of *path*).
            value:    The new value for that attribute.
            quantity: How many units of the stack to affect.  Defaults to 1.
                      Pass 0 or a value >= available quantity to affect the whole stack.
            path:     Optional list of dict keys to traverse before setting *key*.
                      Intermediate dicts are created automatically if absent.

        Returns:
            A human-readable result string.
        """
        if not isinstance(item_id, int):
            return f"Failed to set attribute: item_id must be an integer, got '{item_id}'."

        # --- 1. Locate the item ---
        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            return f"Failed to set attribute: item with ID {item_id} not found."

        item_data     = item_info["item_data"]
        location      = item_info["location"]
        location_id   = item_info["location_id"]

        item_display  = self._format_item_for_display(item_data)
        is_stackable  = item_data.get("stackable", False)

        # The "effective top-level key" for fingerprint purposes:
        # when a path is given the stacking key is path[0], not key.
        fingerprint_key = path[0] if path else key

        # --- 2. Resolve how many units are affected ---
        available = item_data.get("quantity", 1)
        if quantity <= 0 or quantity >= available:
            actual_qty = available
        else:
            actual_qty = quantity

        # --- 3. Resolve the target list ---
        if location == "inventory":
            target_list = self._state_store.get_state_section("inventory", [])
        elif location == "room":
            if not self._room_manager:
                return "Error: RoomManager not set; cannot modify room item."
            room_data = self._room_manager._find_room_by_id(location_id)
            if not room_data or not isinstance(room_data.get("items"), list):
                return f"Error: Room {location_id} not found or corrupted."
            target_list = room_data["items"]
        else:
            return f"Error: Unknown item location '{location}'."

        # --- 4. Non-stackable: just mutate and persist ---
        if not is_stackable:
            self._apply_nested_set(item_data, path, key, value)
            err = self.persist_item_changes(item_id)
            if err:
                return f"Set '{key}' on {item_display}, but failed to persist: {err}"
            path_str = ".".join(path + [key]) if path else key
            return f"Set '{path_str}' = {value!r} on {item_display}."

        # --- Stackable path ---
        stacking_key_before = self._get_item_stacking_key(item_data)

        modified_preview = item_data.copy()
        self._apply_nested_set(modified_preview, path, key, value)
        stacking_key_after = self._get_item_stacking_key(modified_preview)

        fingerprint_unchanged = (stacking_key_before == stacking_key_after)

        if fingerprint_unchanged:
            self._apply_nested_set(item_data, path, key, value)
            err = self.persist_item_changes(item_id)
            if err:
                return f"Set '{key}' on {item_display}, but failed to persist: {err}"
            path_str = ".".join(path + [key]) if path else key
            return f"Set '{path_str}' = {value!r} on all {available} unit(s) of {item_display}."

        # --- Fingerprint changes: split logic ---
        remaining_in_source = available - actual_qty

        detached_preview = {**item_data, **({path[0]: modified_preview[path[0]]} if path else {key: value}), "quantity": actual_qty}
        existing_target = next(
            (i for i in target_list
            if i.get("id") != item_id
            and i.get("stackable", False)
            and self._get_item_stacking_key(i) == self._get_item_stacking_key(detached_preview)
            and i.get("quantity", 0) < i.get("max_stack_size", float("inf"))),
            None
        )

        if remaining_in_source == 0 and existing_target is None:
            self._apply_nested_set(item_data, path, key, value)
            err = self.persist_item_changes(item_id)
            if err:
                return f"Set '{key}' on {item_display}, but failed to persist: {err}"
            path_str = ".".join(path + [key]) if path else key
            return f"Set '{path_str}' = {value!r} on {item_display} (ID kept, stack updated in place)."

        # --- Reduce or remove source stack ---
        if remaining_in_source > 0:
            item_data["quantity"] = remaining_in_source
        else:
            target_list[:] = [i for i in target_list if i.get("id") != item_id]

        detached = {**item_data}
        self._apply_nested_set(detached, path, key, value)
        detached["quantity"] = actual_qty

        existing_target = self._find_matching_stack_in_list(target_list, detached)

        messages = []
        if existing_target:
            space = existing_target.get("max_stack_size", float("inf")) - existing_target.get("quantity", 0)
            can_merge = min(actual_qty, space)
            existing_target["quantity"] += can_merge
            leftover = actual_qty - can_merge
            messages.append(
                f"Merged {can_merge} unit(s) into existing stack {self._format_item_for_display(existing_target)}."
            )
            if leftover > 0:
                new_id = self._state_store.get_next_item_id()
                overflow_stack = {**detached, "id": new_id, "quantity": leftover}
                target_list.append(overflow_stack)
                messages.append(f"Created new stack (ID:{new_id:06d}) for remaining {leftover} unit(s).")
        else:
            new_id = self._state_store.get_next_item_id()
            new_stack = {**detached, "id": new_id, "quantity": actual_qty}
            target_list.append(new_stack)
            messages.append(f"Created new stack {self._format_item_for_display(new_stack)} with {actual_qty} unit(s).")

        if location == "inventory":
            self._state_store.update_state_section("inventory", target_list)
        else:
            rooms_list = self._state_store.get_state_section("rooms", [])
            self._state_store.update_state_section("rooms", rooms_list)

        list_room_items_names, list_inventory_item_names = self.list_inventories(formatted=True)
        self._send_signal({"type": "room_inventory",    "item_list": list_room_items_names})
        self._send_signal({"type": "player_inventory",  "item_list": list_inventory_item_names})

        split_msg = (
            f"Modified '{key}' on {actual_qty} unit(s) of {item_display} "
            f"(source stack {'reduced to ' + str(remaining_in_source) + ' unit(s)' if remaining_in_source > 0 else 'fully consumed'}). "
        )
        return split_msg + " ".join(messages)

    def examine_consumable(self, item_id: int, internal=False): # TODO: Remove this?
        found_item_info = self._find_item_info_by_id(item_id)
        if not found_item_info:
            if internal:
                return {"status": "not_found", "message": f"Item with ID '{item_id}' not found anywhere."}
            else:
                return f"You don't see an item with ID '{item_id}' here or in your inventory."
        item_location = found_item_info["location"]
        item_location_id = found_item_info["location_id"]
        item_data = found_item_info["item_data"]
        is_accessible = (item_location == "inventory") or (item_location == "room" and item_location_id == self._state_store.get_state_section("current_room_id"))
        is_valid, msg = self._is_valid_item_data(item_data, check_id=True)
        if not is_valid:
            print(f"Warning: Found item ID {item_id} at {item_location} but data is invalid: {msg}. Reporting error.")
            if internal:
                return {"status": "error", "message": f"Found item ID {item_id} but data is corrupted: {msg}", "location": item_location}
            else:
                return f"Found item ID {item_id} but data is corrupted: {msg}."
        if not is_accessible:
            if internal:
                return {"status": "not_accessible", "message": f"Item with ID '{item_id}' is not accessible here."}
            else:
                return f"You don't see an item with ID '{item_id}' here or in your inventory."
        if internal:
            return item_data
        
        
        return self._format_item_for_display(item_data)