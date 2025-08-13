
# services/inventory_service.py
import datetime

class InventoryService:
    MAX_INVENTORY_SLOTS = 30
    ALLOWED_ITEM_TYPES = ["tool", "consumable", "misc", "key", "weapon", "armor", "furniture", "book", "seed"]

    def __init__(self, state_store, signal_callback):
        self._state_store = state_store
        self._signal_callback = signal_callback
        self._room_manager = None # Dependency to be set later

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
        return len(current_inventory) >= self.MAX_INVENTORY_SLOTS

    def pickup_item(self, item_id: int):
        if not isinstance(item_id, int):
            return f"Failed to pick up: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        item_info = self._find_item_info_by_id(item_id)
        if item_info is None:
            return "Item not found anywhere."

        item_data = item_info.get("item_data")
        if not item_data:
            print(f"Warning: item_info for ID {item_id} found but missing 'item_data'. item_info: {item_info}")
            return f"Error: Found item info for ID {item_id} but item data is missing."

        item_display = self._format_item_for_display(item_data)

        if item_info["location"] == "inventory":
            return f"You already have the {item_display} in your inventory!"

        if self.is_inventory_full():
            return f"Your inventory is full! You cannot pick up the item. Drop something first. (Max items: {self.MAX_INVENTORY_SLOTS})"

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

        if item_data.get("static", False):
            return f"You cannot pick up the {item_display}. It is too big!"

        # Retrieve mutable copies of lists to modify
        rooms_list = self._state_store.get_state_section("rooms", [])
        inventory_list = self._state_store.get_state_section("inventory", [])

        # Remove from room
        if current_room and isinstance(current_room.get("items"), list):
            initial_count = len(current_room["items"])
            current_room["items"] = [
                item for item in current_room["items"]
                if not (isinstance(item, dict) and item.get("id") == item_id)
            ]
            if len(current_room["items"]) == initial_count:
                print(f"Warning: Item ID '{item_id}' in room '{current_room_id}' not removed by filter during pickup.")
                return f"Error: Could not find item ID '{item_id}' in current room list for removal during pickup."
            self._state_store.update_state_section("rooms", rooms_list) # Save modified rooms
        else:
            return f"Error: Cannot access items in current room (ID:{current_room_id}) during pickup. State might be corrupted."

        # Add to inventory
        if not isinstance(inventory_list, list):
            print("Warning: Inventory state corrupted during item pickup, resetting to empty list.")
            inventory_list = []
        inventory_list.append(item_data)
        self._state_store.update_state_section("inventory", inventory_list) # Save modified inventory

        list_room_items_names, list_inventory_item_names = self.list_inventories()
        self._send_signal({f"type": "room_inventory", "item_list": list_room_items_names})
        self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/hand_up_icon.png"})
        return f"You picked up the {item_display}. It has been correctly placed into your inventory."

    def list_inventories(self):
        current_room_id = self._state_store.get_state_section("current_room_id")
        room_data = None
        if self._room_manager:
            room_data = self._room_manager._find_room_by_id(current_room_id)

        list_room_items_names = []
        if room_data and isinstance(room_data.get("items"), list):
            for item in room_data["items"]:
                name = item.get("name")
                if name:
                    list_room_items_names.append(name)

        inventory_list = self._state_store.get_state_section("inventory", [])
        list_inventory_item_names = []
        if isinstance(inventory_list, list):
            for item in inventory_list:
                name = item.get("name")
                if name:
                    list_inventory_item_names.append(name)
        return list_room_items_names, list_inventory_item_names

    def drop_item(self, item_id: int):
        if not isinstance(item_id, int):
            return f"Failed to drop: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            return f"Failed to drop: Item with ID '{item_id}' not found anywhere."

        item_data = item_info["item_data"]
        item_display = self._format_item_for_display(item_data)
        current_room_id = self._state_store.get_state_section("current_room_id")
        current_room = None
        current_room_display = f"Unknown Room (ID:{current_room_id})"
        if self._room_manager:
            current_room = self._room_manager._find_room_by_id(current_room_id)
            if current_room:
                current_room_display = self._room_manager._format_room_for_display(current_room)

        if item_info["location"] != "inventory":
            if item_info["location"] == "room" and self._room_manager:
                item_location_room = self._room_manager._find_room_by_id(item_info['location_id'])
                location_display = self._room_manager._format_room_for_display(item_location_room) if item_location_room else f"Unknown Room (ID:{item_info['location_id']})"
                return f"Failed to drop {item_display}: It is not in your inventory, it is in {location_display}."
            else:
                return f"Failed to drop {item_display}: It is not in your inventory."

        # Retrieve mutable copies of lists
        inventory_list = self._state_store.get_state_section("inventory", [])
        rooms_list = self._state_store.get_state_section("rooms", [])

        if not isinstance(inventory_list, list):
            return "Error: Cannot access inventory during drop. State might be corrupted."

        initial_count = len(inventory_list)
        inventory_list = [item for item in inventory_list if isinstance(item, dict) and item.get("id") != item_id]
        if len(inventory_list) == initial_count:
            print(f"Warning: Item ID '{item_id}' not removed by filter during drop from inventory.")
            return f"Error: Could not find item ID '{item_id}' in inventory list for removal during drop."
        self._state_store.update_state_section("inventory", inventory_list) # Save modified inventory

        if current_room and isinstance(current_room.get("items"), list):
            current_room["items"].append(item_data)
            self._state_store.update_state_section("rooms", rooms_list) # Save modified rooms
        else:
            print(f"CRITICAL ERROR: Item {item_display} removed from inventory but could not be added to current room (ID:{current_room_id}). Item is potentially LOST.")
            if isinstance(inventory_list, list): # Check against the already modified list
                inventory_list.append(item_data) # Re-add to inventory
                self._state_store.update_state_section("inventory", inventory_list)
                print("Item restored to inventory.")
            else:
                print("Failed to restore item to inventory, state corrupted.")
            return f"Error: Failed to drop {item_display} in the {current_room_display}. Could not access the room's item list. Item remains in inventory."

        list_room_items_names, list_inventory_item_names = self.list_inventories()
        self._send_signal({f"type": "room_inventory", "item_list": list_room_items_names})
        self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/hand_down_icon.png"})
        return f"You dropped the {item_display} in the {current_room_display}."

    def create_item(self, target_location: str, target_location_id: int | None, item_creation_data: dict | list[dict], internal=False, quantity=1):
        # This method is quite long. Adapt it to use self._state_store for all state accesses
        # and self._state_store.get_next_item_id() for ID generation.
        # When modifying rooms or inventory lists, fetch the list, modify it, then use
        # self._state_store.update_state_section("key", modified_list) to save.
        print(f"DEBUG: Starting create_item. target_location: '{target_location}', target_location_id: '{target_location_id}', internal: {internal}, quantity: {quantity}")

        items_to_process = []
        failed_items_info = []

        if not isinstance(quantity, int) or quantity <= 0:
            msg = f"Failed to create item(s): 'quantity' must be a positive integer, received '{quantity}' ({type(quantity).__name__})."
            print(f"DEBUG: Quantity validation failed: {msg}")
            if internal: return False
            return msg

        data_list_templates = []
        if isinstance(item_creation_data, dict):
            data_list_templates = [item_creation_data] * quantity
        elif isinstance(item_creation_data, list):
            for item_template in item_creation_data:
                data_list_templates.extend([item_template] * quantity)
        else:
            msg = f"Failed to create item(s): item_creation_data must be a dict or a list of dicts, received {type(item_creation_data).__name__}."
            print(f"DEBUG: Invalid item_creation_data type: {msg}")
            if internal: return False
            return msg

        if not data_list_templates:
             msg = "No valid item data provided after applying quantity."
             print(f"DEBUG: No data list templates after initial processing: {msg}")
             if internal: return []
             return msg

        print(f"DEBUG: Prepared {len(data_list_templates)} item templates for processing.")

        for idx, item_data in enumerate(data_list_templates):
            if not isinstance(item_data, dict):
                 failed_items_info.append((f"Malformed item data (expected dict, got {type(item_data).__name__})", "Invalid item data format"))
                 continue

            is_valid, error_msg = self._is_valid_item_data(item_data, check_id=False)
            if not is_valid:
                display = item_data.get('name', 'Unnamed Item') if isinstance(item_data, dict) else 'Invalid Data'
                failed_items_info.append((display, f"Invalid input data: {error_msg}"))
                continue

            new_item_id = self._state_store.get_next_item_id() # Use StateStore's ID generator
            new_item_data = item_data.copy()
            new_item_data["id"] = new_item_id

            is_valid_final, error_msg_final = self._is_valid_item_data(new_item_data, check_id=True)
            if not is_valid_final:
                 display = self._format_item_for_display(new_item_data)
                 failed_items_info.append((display, f"Internal validation error after ID generation: {error_msg_final}"))
                 continue
            items_to_process.append(new_item_data)

        if not items_to_process:
             if not failed_items_info:
                 msg = "No valid item data processed."
             else:
                 grouped_failures = {}
                 for name, reason in failed_items_info:
                     key = (name, reason)
                     grouped_failures[key] = grouped_failures.get(key, 0) + 1
                 failure_messages = []
                 for (name, reason), count in grouped_failures.items():
                     if count > 1: failure_messages.append(f"- {count}x {name}: {reason}")
                     else: failure_messages.append(f"- {name}: {reason}")
                 msg = "Failed to create any items due to validation errors:\n" + "\n".join(failure_messages)
             if internal: return []
             return msg

        added_count = 0
        location_desc = "an unknown location"
        successfully_created_ids = []
        placement_successful = False

        target_location_lower = target_location.strip().lower()

        if target_location_lower == "inventory":
            inventory_list = self._state_store.get_state_section("inventory", [])
            for item_data in items_to_process:
                if item_data.get("static", False):
                    item_data["static"] = False
            if not isinstance(inventory_list, list):
                for item_data in items_to_process: failed_items_info.append((self._format_item_for_display(item_data), "Inventory state corrupted."))
                items_to_process = []
            elif (len(inventory_list) + len(items_to_process)) > self.MAX_INVENTORY_SLOTS:
                 for item_data in items_to_process: failed_items_info.append((self._format_item_for_display(item_data), f"Inventory full (Max {self.MAX_INVENTORY_SLOTS})."))
                 items_to_process = []
            if items_to_process:
                 inventory_list.extend(items_to_process)
                 self._state_store.update_state_section("inventory", inventory_list)
                 added_count = len(items_to_process)
                 successfully_created_ids.extend([item["id"] for item in items_to_process])
                 location_desc = "your inventory"
                 placement_successful = True

        elif target_location_lower == "room":
            if not isinstance(target_location_id, int) or not self._room_manager:
                 for item_data in items_to_process: failed_items_info.append((self._format_item_for_display(item_data), f"Target room ID must be an integer when creating item(s) in a room, received '{target_location_id}' ({type(target_location_id).__name__})."))
                 items_to_process = []
            else:
                 rooms_list = self._state_store.get_state_section("rooms", []) # Get the mutable list
                 target_room = self._room_manager._find_room_by_id(target_location_id)

                 if target_room and isinstance(target_room.get("items"), list):
                     target_room["items"].extend(items_to_process)
                     self._state_store.update_state_section("rooms", rooms_list) # Save the modified rooms list
                     added_count = len(items_to_process)
                     successfully_created_ids.extend([item["id"] for item in items_to_process])
                     location_desc = f"the {self._room_manager._format_room_for_display(target_room)}"
                     placement_successful = True
                 else:
                     for item_data in items_to_process: failed_items_info.append((self._format_item_for_display(item_data), f"Target room with ID '{target_location_id}' not found or room data corrupted."))
                     items_to_process = []

        else:
            for item_data in items_to_process: failed_items_info.append((self._format_item_for_display(item_data), f"Invalid target location '{target_location}'. Must be 'room' or 'inventory'."))
            items_to_process = []

        if placement_successful:
            list_room_items_names, list_inventory_item_names = self.list_inventories()
            self._send_signal({f"type": "room_inventory", "item_list": list_room_items_names})
            self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})

        messages = []
        if added_count > 0:
            item_plural = "item" if added_count == 1 else "items"
            messages.append(f"Successfully created {added_count} {item_plural} and placed in {location_desc} with IDs {', '.join(map(str, successfully_created_ids))}.")
        if failed_items_info:
            grouped_failures = {}
            for name, reason in failed_items_info:
                key = (name, reason)
                grouped_failures[key] = grouped_failures.get(key, 0) + 1
            failure_messages = []
            for (name, reason), count in grouped_failures.items():
                if count > 1: failure_messages.append(f"- {count}x {name}: {reason}")
                else: failure_messages.append(f"- {name}: {reason}")
            failed_plural = "item" if len(failed_items_info) == 1 else "items"
            if added_count > 0: messages.append(f"{len(failed_items_info)} {failed_plural} failed to be created or placed:")
            else: messages.append(f"Failed to create any items. {len(failed_items_info)} {failed_plural} failed:")
            messages.append("\n".join(failure_messages))
        if not messages: return "No item creation attempts were processed."
        return "\n".join(messages)

    def trash_item(self, item_id: int, confirm: bool) -> str:
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

            removal_result = self.remove_item(item_id)
            if not removal_result.startswith("Error:"):
                self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/trashcan_icon.png"})
                return f"You trashed the {item_display}."
            else:
                print(f"Warning: trash_item called remove_item for {item_display} (ID:{item_id}) but it failed: {removal_result}")
                return f"Failed to trash {item_display}: {removal_result}"
        else:
            return f"Destruction of item {item_id} cancelled"

    def remove_item(self, item_id: int, internal=False):
        if not isinstance(item_id, int):
            if internal: return False
            return f"Failed to remove: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            if internal: return False
            return f"Failed to remove item: Item with ID '{item_id}' not found anywhere."

        item_data = item_info["item_data"]
        item_display = self._format_item_for_display(item_data)
        location = item_info["location"]
        location_id = item_info["location_id"]
        removed = False
        location_desc = "an unknown location"

        if location == "inventory":
            inventory_list = self._state_store.get_state_section("inventory")
            if isinstance(inventory_list, list):
                initial_count = len(inventory_list)
                inventory_list[:] = [item for item in inventory_list if isinstance(item, dict) and item.get("id") != item_id] # Use slice assignment
                if len(inventory_list) < initial_count:
                    removed = True
                    location_desc = "your inventory"
                self._state_store.update_state_section("inventory", inventory_list)
            else:
                if internal: return False
                return "Error: Cannot remove item from inventory, inventory state corrupted."

        elif location == "room":
            rooms_list = self._state_store.get_state_section("rooms")
            if not self._room_manager:
                if internal: return False
                return "Error: RoomManager not set in InventoryService, cannot remove from room."

            room_data = self._room_manager._find_room_by_id(location_id)
            if room_data and isinstance(room_data.get("items"), list):
                initial_count = len(room_data["items"])
                room_data["items"][:] = [item for item in room_data["items"] if isinstance(item, dict) and item.get("id") != item_id] # Use slice assignment
                if len(room_data["items"]) < initial_count:
                    removed = True
                    location_desc = f"the {self._room_manager._format_room_for_display(room_data)}"
                self._state_store.update_state_section("rooms", rooms_list) # Save the overall rooms list
            else:
                if internal: return False
                return f"Error: Cannot remove item from room '{location_id}', room data corrupted."
        else:
            if internal: return False
            return f"Failed to remove item {item_display}: Unknown location type '{location}'."

        if removed:
            list_room_items_names, list_inventory_item_names = self.list_inventories()
            self._send_signal({f"type": "room_inventory", "item_list": list_room_items_names})
            self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})
            if internal: return True
            return f"Item {item_display} removed from {location_desc}."
        else:
            return f"Failed to remove item {item_display} from {location_desc}: Could not remove from list."
