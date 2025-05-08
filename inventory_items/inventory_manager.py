# inventory_house_manager_id.py
# Manages rooms, items, inventory, and emotes using GenericJsonTool with unique IDs.
# Delegates book-specific logic to BookComponent.

import os
import json
import sys
import random
import math

from inventory_items.items_init import custom_state
# Assuming generic_json_tool.py is in the same directory or accessible in the path
try:
    from utils.generic_json_tool import GenericJsonTool
except ImportError:
    print("Error: generic_json_tool.py not found. Make sure it's in the same directory or PYTHONPATH.")
    sys.exit(1)

# Import the BookComponent
try:
    from inventory_items.book_component import BookComponent
except ImportError:
    print("Error: book_component.py not found. Make sure it's in the same directory or PYTHONPATH.")
    sys.exit(1)

# Import the stats component
try:
    from inventory_items.stats_component import StatsComponent
except ImportError:
    print("Error: stats_component.py not found. Make sure it's in the same directory or PYTHONPATH.")
    sys.exit(1)

class InventoryHouseManager(GenericJsonTool):
    """
    Manages locations (rooms), items, inventory, and AI emotes using unique numerical IDs
    for persistence in a single JSON file. Uses BookComponent for book-specific operations.
    """

    # Define allowed item types, now including "book"
    ALLOWED_ITEM_TYPES = ["tool", "consumable", "misc", "key", "weapon", "armor", "furniture", "book", "plant"]

    # Define starting IDs for generation.
    ITEM_ID_START_COUNTER = 0
    ROOM_ID_START_COUNTER = 0
    MAX_INVENTORY_SLOTS = 20 # You can set this number to whatever you like

    def __init__(self, base_path, signal=None, memory=None):
        """
        Initializes the InventoryHouseManager, integrating state for inventory,
        rooms, and emotes using IDs and a single JSON file.

        Args:
            base_path (str): The base directory path for the state JSON file.
            signal (callable, optional): A callback function to send signals.
                                         Expected signature: `signal(data_dict)`.
        """
        # --- IMPORTANT: Override attributes BEFORE calling super().__init__() ---
        self.json_filename = 'house_inventory_state_id.json'
        self.memory=memory
        # Define the default state structure, now moved to items_init
        self._default_state = custom_state
        # --- End of override ---

        # Call the parent constructor to load/create state using the defined filename and default_state
        super().__init__(base_path)

        # Store the signal callback provided during initialization
        self._signal_callback = signal

        # Instantiate the BookComponent AFTER the state is loaded/initialized by super()
        self._book_component = BookComponent(self)
        try:
             self._stats_component = StatsComponent(self) # Pass self reference
        except TypeError as e:
             print(f"Error initializing StatsComponent: {e}")
             # Decide if this is a fatal error for your application.
             # If stats are non-critical, just log and continue with _stats_component = None.
             # If critical, you might re-raise the error or sys.exit(1).
             # For now, just log and keep it None.
        # Perform validation after loading or using default state


        self._post_init_state_validation()

    def _send_signal(self, signal_data):
        """Helper method to send signals using the registered callback."""
        if self._signal_callback:
            # print(f"InventoryHouseManager signaling: {signal_data}") # Optional: uncomment for debug
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal: {e}")
        else:
            # print(f"InventoryHouseManager attempted to signal, but no callback registered: {signal_data}") # Optional: uncomment for debug
            pass # Silently fail if no callback is registered, or log loudly

    # --- ID Generation Methods (STAY here) ---
    def _generate_next_item_id(self):
        """Generates and increments the next unique item ID."""
        next_id = self._state.get("next_item_id", self.ITEM_ID_START_COUNTER) # Use .get() for robustness
        if not isinstance(next_id, int) or next_id < self.ITEM_ID_START_COUNTER:
             next_id = self.ITEM_ID_START_COUNTER
             print(f"Warning: Resetting next_item_id counter due to invalid value: {self._state.get('next_item_id')}")
             self._state["next_item_id"] = next_id # Correct the state if invalid
             # Note: This correction isn't saved until the next write_json

        self._state["next_item_id"] = next_id + 1 # Increment the counter for next time
        if next_id + 1 > 999999: # Check the *new* value after increment
            print(f"Warning: Item ID counter exceeds 6 digits ({next_id + 1}). Consider implementing ID reuse or expansion.")
        return next_id

    def _generate_next_room_id(self):
        """Generates and increments the next unique room ID."""
        next_id = self._state.get("next_room_id", self.ROOM_ID_START_COUNTER) # Use .get() for robustness
        if not isinstance(next_id, int) or next_id < self.ROOM_ID_START_COUNTER:
             next_id = self.ROOM_ID_START_COUNTER
             print(f"Warning: Resetting next_room_id counter due to invalid value: {self._state.get('next_room_id')}")
             self._state["next_room_id"] = next_id # Correct the state if invalid

        self._state["next_room_id"] = next_id + 1 # Increment the counter for next time
        if next_id + 1 > 999999: # Check the *new* value after increment
             print(f"Warning: Room ID counter exceeds 6 digits ({next_id + 1}). Consider implementing ID reuse or expansion.")
        return next_id

    # --- Post-Init Validation (Updated to include Emote State) ---
    def _post_init_state_validation(self):
            # ... (existing _post_init_state_validation code, which now uses the updated _is_valid_item_data internally) ...
            """
            Performs validation on the loaded or default state to ensure structural integrity
            and ID consistency for inventory, rooms, emotes, and stats. Corrects common issues
            if possible and persists changes.
            This method implicitly validates consumable structure because it calls
            _is_valid_item_data for every item.
            """
            needs_save = False

            # --- Validate ID counters ---
            # Check and correct next_item_id
            if not isinstance(self._state.get("next_item_id"), int) or self._state.get("next_item_id", 0) < self.ITEM_ID_START_COUNTER:
                print(f"Validation Warning: 'next_item_id' invalid ({self._state.get('next_item_id')}). Resetting to start counter {self.ITEM_ID_START_COUNTER}.")
                self._state["next_item_id"] = self.ITEM_ID_START_COUNTER
                needs_save = True
            # Check and correct next_room_id
            if not isinstance(self._state.get("next_room_id"), int) or self._state.get("next_room_id", 0) < self.ROOM_ID_START_COUNTER:
                print(f"Validation Warning: 'next_room_id' invalid ({self._state.get('next_room_id')}). Resetting to start counter {self.ROOM_ID_START_COUNTER}.")
                self._state["next_room_id"] = self.ROOM_ID_START_COUNTER
                needs_save = True

            # --- Validate basic structure keys and types ---
            if not isinstance(self._state.get("current_room_id"), int):
                print("Validation Warning: 'current_room_id' missing or not integer. Setting to default from _default_state.")
                self._state["current_room_id"] = self._default_state.get("current_room_id", -1) # Use default, fallback to -1
                needs_save = True

            if not isinstance(self._state.get("rooms"), list):
                print("Validation Warning: 'rooms' missing or not list. Resetting to default.")
                # Use deepcopy or json dump/load for mutable defaults
                self._state["rooms"] = json.loads(json.dumps(self._default_state["rooms"]))
                needs_save = True

            if not isinstance(self._state.get("inventory"), list):
                print("Validation Warning: 'inventory' missing or not list. Resetting to default.")
                self._state["inventory"] = json.loads(json.dumps(self._default_state["inventory"]))
                needs_save = True

            # --- Validate Emote State ---
            possible_emotes = self._state.get("possible_emotes")
            default_possible_emotes = self._default_state.get("possible_emotes", {})

            if not isinstance(possible_emotes, dict):
                print(f"Validation Warning: 'possible_emotes' in state is not a dict ({type(possible_emotes).__name__}). Resetting to default possible emotes.")
                self._state["possible_emotes"] = json.loads(json.dumps(default_possible_emotes))
                possible_emotes = self._state["possible_emotes"]
                needs_save = True

            current_emote = self._state.get("current_emote")
            if current_emote is None or current_emote not in possible_emotes:
                default_current_emote = self._default_state.get("current_emote", "unknown")
                print(f"Validation Warning: current_emote '{current_emote}' not found or invalid in possible_emotes. Setting to default.")
                new_current = default_current_emote
                if new_current not in possible_emotes:
                    print(f"Validation Warning: Default current_emote '{new_current}' not available. Falling back to first available or 'unknown'.")
                    new_current = next(iter(possible_emotes), "unknown")
                self._state["current_emote"] = new_current
                needs_save = True
            # --- End Emote State Validation ---

            # --- Validate Stats State ---
            stats_data = self._state.get("stats")
            default_stats_data = self._default_state.get("stats", {})
            required_stats_keys = ["fullness", "hydration", "energy"]

            if not isinstance(stats_data, dict):
                print(f"Validation Warning: 'stats' missing or not a dictionary ({type(stats_data).__name__}). Resetting to default stats.")
                self._state["stats"] = json.loads(json.dumps(default_stats_data))
                stats_data = self._state["stats"]
                needs_save = True

            for stat_key in required_stats_keys:
                stat_value = stats_data.get(stat_key)
                default_value = default_stats_data.get(stat_key, 200)

                if stat_value is None or not isinstance(stat_value, (int, float)):
                    print(f"Validation Warning: Stat '{stat_key}' missing or invalid value ({stat_value}). Setting to default ({default_value}).")
                    stats_data[stat_key] = default_value
                    needs_save = True
                elif not (0 <= stat_value <= 200):
                    print(f"Validation Warning: Stat '{stat_key}' value ({stat_value}) is outside expected range (0-200). Clamping.")
                    stats_data[stat_key] = max(0, min(200, stat_value))
                    needs_save = True
            # --- End Stats State Validation ---

            # --- Validate Rooms ---
            room_ids_seen = set()
            valid_rooms = []
            for room in self._state.get("rooms", []):
                if not isinstance(room, dict):
                    print(f"Validation Warning: Found non-dict entry in rooms list: {room}. Removing.")
                    needs_save = True
                    continue
                required_room_keys = ["id", "name", "descriptions", "items"]
                if not all(key in room for key in required_room_keys):
                    print(f"Validation Warning: Room missing required keys ({required_room_keys}): ID {room.get('id', 'unknown')}. Removing.")
                    needs_save = True
                    continue

                if not isinstance(room.get("id"), int):
                    print(f"Validation Warning: Room '{room.get('name', 'Unnamed Room')}' has non-integer ID: {room.get('id')}. Removing.")
                    needs_save = True
                    continue
                if room["id"] in room_ids_seen:
                    print(f"Validation Warning: Duplicate room ID found: {room['id']}. Removing this instance.")
                    needs_save = True
                    continue
                if not isinstance(room.get("name"), str) or not room.get("name", "").strip():
                    print(f"Validation Warning: Room ID {room['id']} has invalid or empty name. Setting to 'Unnamed Room'.")
                    room["name"] = "Unnamed Room"
                    needs_save = True
                if not isinstance(room.get("descriptions"), list) or not all(isinstance(d, str) for d in room.get("descriptions", [])):
                    print(f"Validation Warning: Room '{room['name']}' (ID:{room['id']}) has invalid descriptions (not list of strings). Correcting to empty list.")
                    room["descriptions"] = []
                    needs_save = True
                # Ensure items is a list before processing
                if not isinstance(room.get("items"), list):
                    print(f"Validation Warning: Room '{room['name']}' (ID:{room['id']}) has invalid 'items' (not list). Correcting to empty list.")
                    room["items"] = []
                    needs_save = True # Need to re-validate items in this corrected list

                # Validate items within the room using _is_valid_item_data (which now includes consumable checks)
                # Filter out invalid ones and collect unique IDs
                original_item_count_in_room = len(room.get("items", []))
                valid_room_items_list = []
                if isinstance(room.get("items"), list): # Double check it's a list before iterating
                    for item in room["items"]:
                        # _is_valid_item_data now checks for ID and structure including consumable/book specifics
                        is_valid, msg = self._is_valid_item_data(item, check_id=True)
                        if not is_valid:
                            print(f"Validation Warning: Invalid item found in room ID {room.get('id', 'unknown')}: {msg}. Removing.")
                            needs_save = True
                            continue
                        # Add valid item to temp list
                        valid_room_items_list.append(item)

                room["items"] = valid_room_items_list # Update room's item list with valid items
                if len(room["items"]) < original_item_count_in_room:
                    needs_save = True # Items were removed due to validation

                room_ids_seen.add(room["id"])
                valid_rooms.append(room)

            self._state["rooms"] = valid_rooms

            # Validate current_room_id against validated rooms
            room_id_exists = any(r['id'] == self._state.get("current_room_id") for r in self._state.get("rooms", []))
            if not room_id_exists and self._state.get("rooms"):
                print(f"Validation Warning: current_room_id '{self._state.get('current_room_id')}' not found in valid rooms. Setting to first available room ID ({self._state['rooms'][0]['id']}).")
                self._state["current_room_id"] = self._state["rooms"][0]["id"]
                needs_save = True
            elif not room_id_exists and not self._state.get("rooms"):
                print("FATAL Error: No valid rooms defined in state or default state. Cannot set current_room_id. Setting to -1.")
                self._state["current_room_id"] = -1
                needs_save = True

            # --- Validate Inventory and collect ALL valid item IDs seen ---
            item_ids_seen = set()
            # First, collect valid item IDs from rooms
            for room in self._state.get("rooms", []):
                if isinstance(room, dict) and isinstance(room.get("items"), list):
                    # Iterate through the list that was just validated/filtered above
                    for item in room["items"]:
                        # At this point, items in room["items"] should be valid based on _is_valid_item_data
                        # But we still need to check for duplicates across ALL locations
                        if isinstance(item, dict) and isinstance(item.get('id'), int):
                                if item['id'] in item_ids_seen:
                                    print(f"Validation Warning: Duplicate item ID found ({item['id']}) in room ID {room.get('id', 'unknown')}. Item '{item.get('name', 'Unnamed')}'. This instance will be removed during final item list construction.")
                                    needs_save = True # Duplicate found, will need saving
                                item_ids_seen.add(item['id'])


            # Now process inventory, filtering invalid items and duplicates against items_ids_seen
            valid_inventory_items_list = []
            if isinstance(self._state.get("inventory"), list):
                original_inventory_count = len(self._state["inventory"])
                for item in self._state["inventory"]:
                    # _is_valid_item_data now checks for ID and structure including consumable/book specifics
                    is_valid, msg = self._is_valid_item_data(item, check_id=True)
                    if not is_valid:
                        print(f"Validation Warning: Invalid item found in inventory: {msg}. Removing.")
                        needs_save = True
                        continue
                    if isinstance(item, dict) and isinstance(item.get('id'), int):
                        if item['id'] in item_ids_seen: # Check against IDs seen in rooms *and* previous inventory items
                                print(f"Validation Warning: Duplicate item ID found ({item['id']}) in inventory. Item '{item.get('name', 'Unnamed')}'. Removing this instance.")
                                needs_save = True
                                continue
                        item_ids_seen.add(item['id'])
                        valid_inventory_items_list.append(item)
                    else: # Item is valid structure but ID is not int (should be caught by _is_valid_item_data, but defensive)
                        print(f"Validation Warning: Item passed basic validation but ID invalid: {item}. Removing.")
                        needs_save = True
                        continue # Skip adding it

                self._state["inventory"] = valid_inventory_items_list # Update inventory list
                if len(self._state["inventory"]) < original_inventory_count:
                    needs_save = True # Items were removed due to validation or duplicates


            # Ensure all existing item IDs are below the next_item_id counter
            # Use the item_ids_seen set which contains IDs of all valid, non-duplicate items now
            max_existing_item_id = max(list(item_ids_seen) + [self.ITEM_ID_START_COUNTER - 1])
            if self._state.get("next_item_id", 0) <= max_existing_item_id:
                print(f"Validation Warning: 'next_item_id' ({self._state.get('next_item_id')}) is not greater than the highest existing item ID ({max_existing_item_id}). Adjusting.")
                self._state["next_item_id"] = max_existing_item_id + 1
                needs_save = True

            # Ensure all existing room IDs are below the next_room_id counter
            max_existing_room_id = max(list(room_ids_seen) + [self.ROOM_ID_START_COUNTER - 1])
            if self._state.get("next_room_id", 0) <= max_existing_room_id:
                print(f"Validation Warning: 'next_room_id' ({self._state.get('next_room_id')}) is not greater than the highest existing room ID ({max_existing_room_id}). Adjusting.")
                self._state["next_room_id"] = max_existing_room_id + 1
                needs_save = True

            if needs_save:
                print(f"Correcting state based on validation warnings for {self.__class__.__name__}. Saving state.")
                self._write_json(self._state)


    # --- Helper Methods (Internal Use - STAY here) ---

    # _find_item_info_by_id (STAY)
    # _find_room_by_id (STAY)
    # _find_room_id_by_name (STAY)
    # _is_valid_item_data (STAY, already includes book validation)
    # _format_item_for_display (STAY)
    # _format_room_for_display (STAY)

    def _find_item_info_by_id(self, item_id):
        """
        Internal helper to find an item by its ID and return its location info.

        Args:
            item_id (int): The ID of the item to find.

        Returns:
            dict or None: A dictionary like {'location': 'room'|'inventory',
                          'location_name': room_name_or_None, 'location_id': room_id_or_None,
                          'item_data': item_dict}
                          if found, otherwise None.
        """
        if not isinstance(item_id, int):
             # print(f"Debug: _find_item_info_by_id received non-int ID: {item_id}") # Optional debug
             return None # Cannot search for non-integer ID

        # Check Inventory
        # Ensure inventory is a list before iterating
        if isinstance(self._state.get("inventory"), list):
            for item in self._state["inventory"]:
                # Robust check for item dictionary and ID key/type
                if isinstance(item, dict) and item.get("id") == item_id and isinstance(item.get("id"), int):
                    return {
                        "location": "inventory",
                        "location_name": None, # Inventory doesn't have a specific 'name' for location
                        "location_id": None,
                        "item_data": item
                    }

        # Check Rooms
        # Ensure rooms is a list before iterating
        if isinstance(self._state.get("rooms"), list):
            for room in self._state["rooms"]:
                # Robust check for room dictionary, ID, and items list
                if isinstance(room, dict) and isinstance(room.get("id"), int) and isinstance(room.get("items"), list):
                    for item in room["items"]:
                         # Robust check for item dictionary and ID key/type
                         if isinstance(item, dict) and item.get("id") == item_id and isinstance(item.get("id"), int):
                            return {
                                "location": "room",
                                "location_name": room.get("name"),
                                "location_id": room.get("id"),
                                "item_data": item
                            }

        return None # Item not found anywhere

    def _find_room_by_id(self, room_id):
        """Internal helper to find a room dictionary by its ID, returning None if not found."""
        if not isinstance(room_id, int):
             return None
        if isinstance(self._state.get("rooms"), list): # Ensure rooms is a list
            for room in self._state["rooms"]:
                 if isinstance(room, dict) and room.get("id") == room_id and isinstance(room.get("id"), int):
                      return room
        return None

    def _find_room_id_by_name(self, room_name):
         """Internal helper to find a room ID by its name (case-insensitive), returning None if not found."""
         if not isinstance(room_name, str) or not room_name.strip():
              return None
         name_lower = room_name.strip().lower()
         if isinstance(self._state.get("rooms"), list): # Ensure rooms is a list
             for room in self._state["rooms"]:
                  if isinstance(room, dict) and isinstance(room.get("name"), str) and room["name"].lower() == name_lower:
                       return room.get("id") # Return the ID if found
         return None

    def _is_valid_item_data(self, item_data, check_id=False):
         """
         Internal helper to validate the structure and content of an item dictionary.
         Optionally checks for the 'id' key's presence and type.
         Includes book-specific and consumable-specific validation.
         """
         if not isinstance(item_data, dict):
              return False, "Item data is not a dictionary."

         if check_id:
              # Use .get() for safety before checking isinstance
              item_id_val = item_data.get('id')
              if item_id_val is None or not isinstance(item_id_val, int):
                   return False, f"Item data missing or has invalid 'id' ({item_id_val})."

         # Required keys for ALL item types (excluding ID if check_id=False)
         # Note: 'stats_edit' and 'effects' are specific to 'consumable', 'chapters' to 'book'
         # We check for type-specific keys below.
         required_keys_base = ["name", "descriptions", "static", "type"]
         if not all(key in item_data for key in required_keys_base):
              missing = [key for key in required_keys_base if key not in item_data]
              # Attempt to include item name if available for better logging
              item_name_for_log = item_data.get('name', 'Unnamed Item')
              item_id_for_log = item_data.get('id', 'unknown')
              return False, f"Item '{item_name_for_log}' (ID:{item_id_for_log}) missing base required keys: {missing}"

         # Basic type checks for required keys
         item_name = item_data.get('name', 'Unnamed') # Use get for safety
         if not isinstance(item_data["name"], str) or not item_data["name"].strip():
              item_id_for_log = item_data.get('id', 'unknown')
              return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'name' must be a non-empty string."

         # Descriptions validation also checks if it's a list of strings
         descriptions = item_data.get("descriptions", []) # Use get
         if not isinstance(descriptions, list) or not all(isinstance(d, str) for d in descriptions):
              item_id_for_log = item_data.get('id', 'unknown')
              return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'descriptions' must be a list of strings."

         if not isinstance(item_data.get("static"), bool): # Use get
              item_id_for_log = item_data.get('id', 'unknown')
              return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'static' must be a boolean."

         item_type = item_data.get("type")
         if item_type not in self.ALLOWED_ITEM_TYPES:
              item_id_for_log = item_data.get('id', 'unknown')
              return False, f"Item '{item_name}' (ID:{item_id_for_log}) 'type' '{item_type}' is not allowed. Allowed types: {self.ALLOWED_ITEM_TYPES}"

         # --- Type-specific validation ---

         # --- Book-specific validation ---
         if item_type == "book":
              # Use .get() for 'chapters' key
              chapters_list = item_data.get("chapters")
              if not isinstance(chapters_list, list):
                   item_id_for_log = item_data.get('id', 'unknown')
                   return False, f"Book item '{item_name}' (ID:{item_id_for_log}) missing 'chapters' key or 'chapters' is not a list."
              # Validate structure of each chapter in the list
              for i, chapter in enumerate(chapters_list):
                   if not isinstance(chapter, dict):
                        item_id_for_log = item_data.get('id', 'unknown')
                        return False, f"Book item '{item_name}' (ID:{item_id_for_log}) has invalid chapter entry (not dict) at index {i}."
                   # Use .get() for chapter keys
                   chapter_title = chapter.get("title")
                   chapter_content = chapter.get("content")
                   if chapter_title is None or not isinstance(chapter_title, str) or not chapter_title.strip():
                        item_id_for_log = item_data.get('id', 'unknown')
                        return False, f"Book item '{item_name}' (ID:{item_id_for_log}) has invalid or empty chapter 'title' at index {i}."
                   if chapter_content is None or not isinstance(chapter_content, str):
                        item_id_for_log = item_data.get('id', 'unknown')
                        return False, f"Book item '{item_name}' (ID:{item_id_for_log}) has invalid or missing chapter 'content' at index {i}."
              # Note: We don't enforce chapter title uniqueness here, could add if needed.

         # --- Consumable-specific validation (NEW/UPDATED) ---
         elif item_type == "consumable":
              # Validate stats_edit
              stats_edit_data = item_data.get("stats_edit")
              item_id_for_log = item_data.get('id', 'unknown') # Get ID for logging
              if not isinstance(stats_edit_data, dict):
                   return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) missing 'stats_edit' key or 'stats_edit' is not a dictionary."

              valid_stats_keys = {"fullness", "hydration", "energy"}
              # Check that stats_edit only contains expected keys and values are integers
              for key, value in stats_edit_data.items():
                   if key not in valid_stats_keys:
                        return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) has unexpected key '{key}' in 'stats_edit'. Valid keys are: {list(valid_stats_keys)}"
                   if not isinstance(value, (int, float)):
                        return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) has non-integer or float value for stat '{key}' in 'stats_edit'."

              # Validate effects list (NEW)
              effects_list = item_data.get("effects")
              if effects_list is None: # Allow effects to be optional, but warn if missing for consumable? Or make required? Let's make it optional for now.
                   # print(f"Validation Info: Consumable item '{item_name}' (ID:{item_id_for_log}) is missing optional 'effects' list.") # Optional info log
                   pass # Effects list is optional
              elif not isinstance(effects_list, list):
                   return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) 'effects' key is not a list."
              elif not all(isinstance(effect, str) for effect in effects_list):
                   return False, f"Consumable item '{item_name}' (ID:{item_id_for_log}) 'effects' list contains non-string values."


         # Add validation for other types if they have specific requirements


# -------- Plant validation (NEW)

         # --- Plant-specific validation ---
         if item_type == "plant":
              item_id_for_log = item_data.get('id', 'unknown') # Get ID once for logging

              # Use .get() for required keys and check types
              timestamp_of_creation = item_data.get("timestamp_of_creation")
              if timestamp_of_creation is None or not isinstance(timestamp_of_creation, (int, float)): # Assuming timestamp is a number (Unix epoch, etc.)
                   return False, f"Plant item '{item_name}' (ID:{item_id_for_log}) missing 'timestamp_of_creation' or it's not a number (int or float)."

              last_watered = item_data.get("last_watered")
              if last_watered is None or not isinstance(last_watered, (int, float)): # Assuming timestamp is a number
                   return False, f"Plant item '{item_name}' (ID:{item_id_for_log}) missing 'last_watered' or it's not a number (int or float)."

              current_stage = item_data.get("current_stage")
              if current_stage is None or not isinstance(current_stage, float):
                   return False, f"Plant item '{item_name}' (ID:{item_id_for_log}) missing 'current_stage' or it's not a float."

              total_stages = item_data.get("total_stages")
              if total_stages is None or not isinstance(total_stages, float):
                   return False, f"Plant item '{item_name}' (ID:{item_id_for_log}) missing 'total_stages' or it's not a float."

              # Note: You might want to add checks like current_stage <= total_stages and total_stages > 0
              # but the request was just for type validation.
         return True, "" # Item is valid


    def _format_item_for_display(self, item_dict):
        """Formats an item dictionary into a readable string including name and ID."""
        if not isinstance(item_dict, dict):
             return "Invalid Item Data" # Handle cases where dict is expected but not received

        item_id = item_dict.get('id', -1)
        item_name = item_dict.get('name', 'Unnamed Item')

        # Ensure ID is an integer before formatting
        if not isinstance(item_id, int):
             return f"{item_name} (ID:INVALID)"

        return f"{item_name} (ID:{item_id:06d})" # Format ID to be 6 digits with leading zeros


    def _format_room_for_display(self, room_dict):
         """Formats a room dictionary into a readable string including name and ID."""
         if not isinstance(room_dict, dict):
              return "Invalid Room Data"

         room_id = room_dict.get('id', -1)
         room_name = room_dict.get('name', 'Unnamed Room')

         if not isinstance(room_id, int):
              return f"{room_name} (ID:INVALID)"

         return f"{room_name} (ID:{room_id:06d})"


    # --- Public Methods (Core Inventory/House - MOST STAY here) ---

    # get_current_room_id (STAY)
    # get_current_room_name (STAY)
    # set_current_room (STAY, includes signal for background change)
    # get_current_room_description (STAY)
    # get_items_in_current_room (STAY)
    # get_inventory_items (STAY)
    # get_all_rooms (STAY)
    # get_item_details (STAY)
    # pickup_item (STAY)
    # drop_item (STAY)
    # create_item (STAY, used for all item types including books)
    # remove_item (STAY)

    def get_room_name(self, room_id: int) -> str:
        """
        Returns the name of a room based on its ID.

        Args:
            room_id (int): The ID of the room.

        Returns:
            str: The name of the room, or "Unknown Room" if not found.
        """
        room = self._find_room_by_id(room_id)
        if room:
            return room.get("name", "Unknown Room")
        return "Unknown Room"

    def get_current_room_id(self):
        """
        Gets the ID of the player's current room.

        Returns:
            int: The ID of the current room, or -1 if current room is invalid.
        """
        return self._state.get("current_room_id", -1) # Use .get() for safety


    def get_current_room_name(self):
        """
        Gets the name of the player's current room.

        Returns:
            str: The name of the current room, or an error string if current room is invalid.
        """
        current_room = self._find_room_by_id(self._state.get("current_room_id")) # Use .get()
        if current_room:
             return current_room.get("name", "Unnamed Room") # Use .get()
        else:
             return f"Error: Current room ID '{self._state.get('current_room_id')}' is invalid or room not found." # Use .get()


    def set_current_room(self, room_id: int):
        """
        Attempts to move the player to a different room using its ID.
        Sends a 'change_background' signal on successful move.

        Args:
            room_id (int): The ID of the room to move to.

        Returns:
            str: A message indicating success or failure.
        """
        if not isinstance(room_id, int):
             return f"Failed to move: Room ID must be an integer, received '{room_id}' ({type(room_id).__name__})."

        target_room = self._find_room_by_id(room_id)

        if target_room:
            if self._state.get("current_room_id") == room_id: # Use .get() for safety
                 return f"You are already in the {self._format_room_for_display(target_room)}."
            else:
                self._state["current_room_id"] = room_id
                self._write_json(self._state)
                # Retrieve updated current room info for signal
                current_room = self._find_room_by_id(self._state.get("current_room_id")) # Use .get()
                if current_room:
                    c_name = current_room.get("name", "unnamed_room") # Use .get(), lowercase for path convention
                    # Send signal for background change
                    self._send_signal({"type": "change_background", "image_path": f"{c_name}"}) # Assuming .png extension

                descriptions = target_room.get("descriptions", []) # Use .get(), default to empty list
                # Ensure descriptions is a list of strings before joining
                if not isinstance(descriptions, list) or not all(isinstance(d, str) for d in descriptions):
                     descriptions = [] # Reset if invalid type
                     desc_str = "(No description available.)"
                else:
                     desc_str = ", ".join(descriptions)
                     if not desc_str: # If list was empty
                         desc_str = "(No description available.)"

                list_room_items_names, list_inventory_item_names = self.list_inventories()
                # list_inventory_item_names would now be ['old_key', 'Mysteries of the Cozy House']
                # based on your base_state example

                self._send_signal({f"type": "room_inventory", "item_list":list_room_items_names})

                return f"You move to the {self._format_room_for_display(target_room)}. {desc_str}"
        else:
            return f"There is no room with ID '{room_id}'. The existing rooms are: {self.get_all_rooms()}"


    def get_current_room_description(self):
        """
        Gets the description(s) of the current room.

        Returns:
            str: A combined string of the room descriptions, or an error message.
        """
        current_room_id = self._state.get("current_room_id") # Use .get()
        room_data = self._find_room_by_id(current_room_id)

        if room_data: # Check if room_data is not None
            room_display = self._format_room_for_display(room_data)
            descriptions = room_data.get("descriptions", []) # Use .get(), default to empty list

            if isinstance(descriptions, list) and all(isinstance(d, str) for d in descriptions):
                 if descriptions:
                     return f"Description for {room_display}:\n" + "\n".join(descriptions)
                 else:
                     return f"The {room_display} has no specific description."
            else:
                 # This case should ideally be caught by validation, but defensive
                 return f"Error: Descriptions for {room_display} are corrupted."
        else:
            # This case means _find_room_by_id returned None, current_room_id is invalid
            return f"Error: Could not find description for current room (ID: {current_room_id}). State might be corrupted."


    def get_items_in_current_room(self, internal=False):
        """
        Lists the names and IDs of items currently in the player's current room.

        Returns:
            str: A comma-separated string of item descriptions (Name (ID:XXXXXX)),
                 or a message if the room is empty or not found.
        """

        current_room_id = self._state.get("current_room_id") # Use .get()
        room_data = self._find_room_by_id(current_room_id)

        if room_data: # Check if room_data is not None
            room_display = self._format_room_for_display(room_data)
            room_items = room_data.get("items", []) # Use .get(), default to empty list

            if isinstance(room_items, list): # Ensure it's a list before processing
                # Filter out invalid item data before formatting
                valid_items = [item for item in room_items if self._is_valid_item_data(item, check_id=True)[0]]
                items_display = [self._format_item_for_display(item) for item in valid_items]

                if items_display:
                    if internal:
                        return room_items
                    return f"Items in the {room_display}: {', '.join(items_display)}"
                else:
                    return f"There are no items in the {room_display}."
            else:
                 # This case should ideally be caught by validation, but defensive
                 return f"Error: Item list for {room_display} is corrupted."
        else:
            # This case means _find_room_by_id returned None
            return f"Error: Could not access item list for current room (ID: {current_room_id}). State might be corrupted."


    def get_inventory_items(self, internal=False):
        """
        Lists the names and IDs of items currently in the player's inventory.

        Returns:
            str: A comma-separated string of item descriptions (Name (ID:XXXXXX)),
                 or a message if the inventory is empty or not found.
        """
        inventory_list = self._state.get("inventory") # Use .get()

        if isinstance(inventory_list, list): # Ensure it's a list before processing
            # Filter out invalid item data before formatting
            valid_items = [item for item in inventory_list if self._is_valid_item_data(item, check_id=True)[0]]
            items_display = [self._format_item_for_display(item) for item in valid_items]

            if items_display:
                if internal:
                    return inventory_list
                return f"Items in your inventory: {', '.join(items_display)}"
            else:
                return "Your inventory is empty."
        else:
             # This case should ideally be caught by validation, but defensive
             return "Error: Could not access inventory. State might be corrupted."
    def get_item_details(self, item_id: int, internal=False):
        """
        Provides detailed information about an item by its ID.
        If internal=False, returns a formatted string for user display (name/ID + descriptions)
        only if the item is in the current room or inventory.
        If internal=True, returns a dictionary structure including location info
        regardless of accessibility, or a status dict if not found or corrupted.

        Args:
            item_id (int): The ID of the item to look up.
            internal (bool): If True, returns a dictionary structure for internal use;
                            if False, returns a formatted string for user display (if accessible).

        Returns:
            str or dict: A formatted string if internal is False and item is accessible/valid.
                        A dictionary structure (including status) if internal is True.
                        A string error message if internal is False and item is not found/accessible/valid.
        """
        if not isinstance(item_id, int):
            # Return type depends on 'internal' flag
            if internal:
                return {"status": "error", "message": f"Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."}
            else:
                return f"Failed to examine: Item ID must be an integer, received '{item_id}'."


        found_item_info = self._find_item_info_by_id(item_id)
        current_room_id = self._state.get("current_room_id")

        if not found_item_info:
            # Item not found anywhere
            if internal:
                return {"status": "not_found", "message": f"Item with ID '{item_id}' not found anywhere."}
            else:
                return f"You don't see an item with ID '{item_id}' here or in your inventory."

        # Item was found somewhere. Check if it's accessible (in current room or inventory).
        item_location = found_item_info["location"]
        item_location_id = found_item_info["location_id"] # Will be None for inventory
        item_data = found_item_info["item_data"] # Get the found item data

        is_accessible = (item_location == "inventory") or (item_location == "room" and item_location_id == current_room_id)

        # Perform validation on the found item data
        is_valid, msg = self._is_valid_item_data(item_data, check_id=True)

        if not is_valid:
            # Item found but data is corrupted
            print(f"Warning: Found item ID {item_id} at {item_location} but data is invalid: {msg}. Reporting error.")
            if internal:
                return {"status": "error", "message": f"Found item ID {item_id} but data is corrupted: {msg}", "location": item_location}
            else:
                # For user, just report corruption if item was found at all
                item_display = self._format_item_for_display(item_data) # Attempt to format name/ID
                return f"Error: Data for item {item_display} seems corrupted."

        # Data is valid. Now handle accessibility and output format.
        if not is_accessible:
            # Item found and valid, but not accessible for examination (not in current room/inventory)
            item_display = self._format_item_for_display(item_data) # Format even if not accessible

            if internal:
                location_desc = "inventory" if item_location == "inventory" else (self._format_room_for_display(self._find_room_by_id(item_location_id)) if item_location == "room" else "an unknown location")
                return {"status": "not_accessible", "message": f"Item {item_display} is not in your current location. It is in {location_desc}.", "location": item_location, "location_id": item_location_id}
            else:
                return f"You can only examine items in your current location or inventory. Item {item_display} is not here." # Simpler message for user

        # Item found, valid, and accessible.
        if internal:
            # Return the full item_data dictionary for internal use
            return {
                "status": "found",
                "details": item_data, # Return the full dictionary
                "location": item_location,
                "location_name": found_item_info["location_name"], # Name is None for inventory, Name for room
                "location_id": item_location_id # ID is None for inventory, ID for room
            }
        else:
            # Format for external user display (name/ID + descriptions)
            item_display = self._format_item_for_display(item_data)
            descriptions = item_data.get("descriptions", []) # Get descriptions list

            output_string = f"{item_display}\n\n" # Start with name (ID:...) and add blank line

            # Ensure descriptions is a list of strings before joining
            if descriptions and isinstance(descriptions, list) and all(isinstance(d, str) for d in descriptions):
                output_string += "\n".join(descriptions)
            else:
                output_string += "(No description available.)" # Handle missing or invalid descriptions structure

            return output_string


    def pickup_item(self, item_id: int):
        """
        Attempts to move an item from the current room into the inventory using its ID.
        Checks if the inventory is full before picking up.

        Args:
            item_id (int): The ID of the item to pick up.

        Returns:
            str: A message indicating success or failure (including inventory full).
        """
        if not isinstance(item_id, int):
            return f"Failed to pick up: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        item_info = self._find_item_info_by_id(item_id)
        
        if item_info == None:
            return "Item not found anywhere."

        # Check if the item is already on inventory first of all

        if item_info["location"] == "inventory":
            return f"You already have the {item_display} in your inventory!"


        # Check if inventory is full BEFORE attempting to pick up (NEW)
        current_inventory = self._state.get("inventory", [])
        if not isinstance(current_inventory, list): # Defensive check, though validation should handle this
             print("Warning: Inventory state corrupted during pickup, treating as full for safety.")
             return "Error: Cannot pick up item, inventory state is corrupted."

        if len(current_inventory) >= self.MAX_INVENTORY_SLOTS:
            return f"Your inventory is full! You cannot pick up the item. Drop something first. (Max items: {self.MAX_INVENTORY_SLOTS})"
        # End of NEW check


        if not item_info:
            return f"Failed to pick up: Item with ID '{item_id}' not found anywhere."

        item_data = item_info["item_data"]
        item_display = self._format_item_for_display(item_data)
        current_room_id = self._state.get("current_room_id")
        current_room = self._find_room_by_id(current_room_id)
        current_room_display = self._format_room_for_display(current_room) if current_room else f"Unknown Room (ID:{current_room_id})"




        # Check if item is in the current room
        if not (item_info["location"] == "room" and item_info["location_id"] == current_room_id):
            # Item is found, but not in the current room (it's in another room)
            item_location_room = self._find_room_by_id(item_info['location_id'])
            location_display = self._format_room_for_display(item_location_room) if item_location_room else f"Unknown Room (ID:{item_info['location_id']})"
            return f"Failed to pick up {item_display}: It is in {location_display}, not here."


        # Item is confirmed to be in the current room
        if item_data.get("static", False):
            return f"You cannot pick up the {item_display}. It is too big!"

        # Remove from room
        if current_room and isinstance(current_room.get("items"), list):
            initial_count = len(current_room["items"])
            current_room["items"] = [item for item in current_room["items"] if isinstance(item, dict) and item.get("id") != item_id]
            if len(current_room["items"]) == initial_count:
                # Item not removed, indicates inconsistency
                print(f"Warning: Item ID '{item_id}' in room '{current_room_id}' not removed by filter during pickup.")
                # Attempt fallback index removal if necessary, or return error
                return f"Error: Could not find item ID '{item_id}' in current room list for removal during pickup." # Report failure


        else: # current_room or its items list is invalid
            return f"Error: Cannot access items in current room (ID:{current_room_id}) during pickup. State might be corrupted."

        # Add to inventory
        # The inventory full check was done earlier, so we assume there is space here
        # Ensure inventory is a list before appending
        if not isinstance(self._state.get("inventory"), list):
            print("Warning: Inventory state corrupted during item pickup, resetting to empty list.")
            self._state["inventory"] = [] # Reset inventory if corrupted
            # Note: If we reset inventory here, the item was removed from the room but might not be added.
            # This is an edge case due to corrupted state. The error message above is better.
            # If we reach here, the inventory *should* be a list because of the check at the start.
        self._state["inventory"].append(item_data)

        self._write_json(self._state) # Save changes

        list_room_items_names, list_inventory_item_names = self.list_inventories()
        # list_inventory_item_names would now be ['old_key', 'Mysteries of the Cozy House']
        # based on your base_state example
        self._send_signal({f"type": "room_inventory", "item_list":list_room_items_names})
        self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})

        return f"You picked up the {item_display}."
    

    def list_inventories(self):

        """
        Lists the items in the current room and inventory
        Returns:
            list_room_items_names, list_inventory_item_names
        """


        current_room_id = self._state.get("current_room_id") # Use .get()
        # Assuming self._find_room_by_id works and returns the room dictionary
        room_data = self._find_room_by_id(current_room_id)

        # Get items specifically in the current room
        room_items = room_data.get("items", []) # Use .get(), default to empty list

        list_room_items_names=[
        ]

        for item in room_items:
            # CORRECTED: Access the 'name' key from the item dictionary
            name = item.get("name")

            # Optional: Check if name exists before appending (defensive)
            if name:
                list_room_items_names.append(name)

        # list_room_items_names would now be ['sofa', 'remote_control', 'pizza_slice']
        # if the current room is 200001 (living_room)

        # Get the inventory list directly from the state
        inventory_list = self._state.get("inventory", []) # Use .get(), default to empty list

        list_inventory_item_names = []

        for item in inventory_list:
            # CORRECTED: Access the 'name' key from the item dictionary in the inventory
            name = item.get("name")

            # Optional: Check if name exists before appending (defensive)
            if name:
                 list_inventory_item_names.append(name)

        # list_inventory_item_names would now be ['old_key', 'Mysteries of the Cozy House']
        # based on your base_state example
        return list_room_items_names, list_inventory_item_names

    def drop_item(self, item_id: int):
        """
        Attempts to move an item from the inventory into the current room using its ID.

        Args:
            item_id (int): The ID of the item to drop.

        Returns:
            str: A message indicating success or failure.
        """
        if not isinstance(item_id, int):
            return f"Failed to drop: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        item_info = self._find_item_info_by_id(item_id)

        if not item_info:
            return f"Failed to drop: Item with ID '{item_id}' not found anywhere."

        item_data = item_info["item_data"]
        item_display = self._format_item_for_display(item_data)
        current_room_id = self._state.get("current_room_id")
        current_room = self._find_room_by_id(current_room_id)
        current_room_display = self._format_room_for_display(current_room) if current_room else f"Unknown Room (ID:{current_room_id})"

        if item_info["location"] != "inventory":
            # Item exists, but isn't in inventory
            if item_info["location"] == "room":
                item_location_room = self._find_room_by_id(item_info['location_id'])
                location_display = self._format_room_for_display(item_location_room) if item_location_room else f"Unknown Room (ID:{item_info['location_id']})"
                return f"Failed to drop {item_display}: It is not in your inventory, it is in {location_display}."
            else: # Should not happen with current known locations
                return f"Failed to drop {item_display}: It is not in your inventory."


        # Item is confirmed to be in inventory
        if not isinstance(self._state.get("inventory"), list):
            return "Error: Cannot access inventory during drop. State might be corrupted."

        # Remove from inventory
        initial_count = len(self._state["inventory"])
        # Filter inventory, keeping items whose ID is not the one we're dropping
        self._state["inventory"] = [item for item in self._state["inventory"] if isinstance(item, dict) and item.get("id") != item_id]

        if len(self._state["inventory"]) == initial_count:
            # Item wasn't removed, indicates inconsistency
            print(f"Warning: Item ID '{item_id}' not removed by filter during drop from inventory.")
            return f"Error: Could not find item ID '{item_id}' in inventory list for removal during drop." # Report failure


        # Add to current room
        if current_room and isinstance(current_room.get("items"), list):
            # We need to use the original item_data dictionary that we found via _find_item_info_by_id
            # This ensures all original properties, including book-specific ones, are moved.
            current_room["items"].append(item_data) # Append the item data found initially
        else:
            # Critical error: Item removed from inventory but can't be placed.
            print(f"CRITICAL ERROR: Item {item_display} removed from inventory but could not be added to current room (ID:{current_room_id}). Item is potentially LOST.")
            # Consider adding it back to inventory here or implementing a transaction-like system.
            # For now, just report failure.
            # Add item back to inventory as a failsafe
            print(f"Attempting to restore item {item_display} to inventory due to room placement failure.")
            if isinstance(self._state.get("inventory"), list):
                self._state["inventory"].append(item_data)
                print("Item restored to inventory.")
            else:
                print("Failed to restore item to inventory, state corrupted.")
            return f"Error: Failed to drop {item_display} in the {current_room_display}. Could not access the room's item list. Item remains in inventory."



        current_room_id = self._state.get("current_room_id") # Use .get()
        # Assuming self._find_room_by_id works and returns the room dictionary
        room_data = self._find_room_by_id(current_room_id)

        # Get items specifically in the current room
        room_items = room_data.get("items", []) # Use .get(), default to empty list

        self._write_json(self._state) # Save changes

        list_room_items_names, list_inventory_item_names = self.list_inventories()
        # list_inventory_item_names would now be ['old_key', 'Mysteries of the Cozy House']
        # based on your base_state example

        self._send_signal({f"type": "room_inventory", "item_list":list_room_items_names})
        self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})

        return f"You dropped the {item_display} in the {current_room_display}."
    
    def get_room_name(self, room_id) -> str:
        """
        Returns the name of a room based on its ID.

        Args:
            room_id (int): The ID of the room.

        Returns:
            str: The name of the room, or "Unknown Room" if not found.
        """
        room = self._find_room_by_id(room_id)
        if room:
            return room.get("name", "Unknown Room")
        return "Unknown Room"


    def create_item(self, target_location: str, target_location_id: int | None, item_creation_data: dict, internal=False):
        """
        Creates a new item with a generated unique ID and places it in the specified location.
        This method is used for ALL item types, including books.
        Respects inventory limit when placing in inventory.

        Args:
            target_location (str): Where to place the item ('room' or 'inventory'). Case-insensitive.
            target_location_id (int or None): The ID of the room if target_location is 'room',
                                            or None if target_location is 'inventory'.
            item_creation_data (dict): A dictionary containing the item's properties.
                                    This dict should match the item structure for its type,
                                    but MUST NOT include the 'id' key (it is generated).
                                    e.g., for a book: {'name': str, 'descriptions': list[str], 'static': bool, 'type': 'book', 'chapters': list[dict]}

        Returns:
            str: A message indicating success or failure (e.g., invalid data, location not found, inventory full).
        """
        # Validate input data structure BEFORE adding ID
        # Use _is_valid_item_data without checking for ID presence yet
        is_valid, error_msg = self._is_valid_item_data(item_creation_data, check_id=False)
        if not is_valid:
            return f"Failed to create item: Invalid input data - {error_msg}"

        # Generate a new unique ID for the item
        new_item_id = self._generate_next_item_id()

        # Create the full item dictionary including the generated ID
        # Ensure we use a copy to avoid modifying the input dict
        new_item_data = item_creation_data.copy()
        new_item_data["id"] = new_item_id # Add the generated ID

        # Perform a final validation on the *full* item data with ID,
        # including type-specific checks (like for books).
        is_valid_final, error_msg_final = self._is_valid_item_data(new_item_data, check_id=True)
        if not is_valid_final:
            # This shouldn't happen if initial validation passed and only ID was added,
            # but good defensive check.
            print(f"Error: Final validation failed for item data with generated ID {new_item_id}: {error_msg_final}")
            # Optionally decrement ID counter here if ID was consumed but item is invalid.
            # self._state["next_item_id"] -= 1 # Be careful with this if multiple threads/calls are possible
            return f"Failed to create item due to internal validation error after ID generation: {error_msg_final}"


        item_display = self._format_item_for_display(new_item_data)
        target_location_lower = target_location.strip().lower()
        added = False
        location_desc = "an unknown location" # Default failure description

        if target_location_lower == "inventory":
            # Items created directly into inventory cannot be static (doesn't make sense)
            if new_item_data.get("static", False):
                print(f"Warning: Attempted to create static item {item_display} directly into inventory. 'static' attribute ignored.")
                new_item_data["static"] = False
            # No check for item name uniqueness; ID is the primary identifier.

            # Check if inventory is full BEFORE creating the item (NEW)
            current_inventory = self._state.get("inventory", [])
            if not isinstance(current_inventory, list): # Defensive check
                 print("Warning: Inventory state corrupted during item creation into inventory, treating as full for safety.")
                 return f"Error: Cannot create item {item_display}, inventory state is corrupted."

            if len(current_inventory) >= self.MAX_INVENTORY_SLOTS:
                # Optionally decrement ID counter if it was incremented but item wasn't added
                # For simplicity now, we'll let the counter increase. IDs are cheap.
                if internal:
                    return False
                return f"Failed to create item {item_display}: Your inventory is full! (Max items: {self.MAX_INVENTORY_SLOTS})"
            # End of NEW check

            # Ensure inventory is a list before appending (re-check after potential corruption check)
            if not isinstance(self._state.get("inventory"), list):
                 print("Warning: Inventory state corrupted during item creation, resetting to empty list before append.")
                 self._state["inventory"] = [] # Reset inventory if corrupted

            self._state["inventory"].append(new_item_data) # Add the complete item dict
            added = True
            location_desc = "your inventory"

        elif target_location_lower == "room":
            if not isinstance(target_location_id, int):
                if internal:
                    return False
                return f"Failed to create item {item_display}: Target room ID must be an integer when creating item in a room, received '{target_location_id}' ({type(target_location_id).__name__})."

            target_room = self._find_room_by_id(target_location_id)

            if target_room and isinstance(target_room.get("items"), list):
                target_room["items"].append(new_item_data) # Add the complete item dict
                added = True
                location_desc = f"the {self._format_room_for_display(target_room)}"
            else:
                if internal:
                    return False
                return f"Failed to create item {item_display}: Target room with ID '{target_location_id}' not found or room data corrupted."

        else:
            if internal:
                return False
            return f"Failed to create item {item_display}: Invalid target location '{target_location}'. Must be 'room' or 'inventory'."

        if added:
            self._write_json(self._state) # Save state with the new item and incremented counter
            list_room_items_names, list_inventory_item_names = self.list_inventories()
            # list_inventory_item_names would now be ['old_key', 'Mysteries of the Cozy House']
            # based on your base_state example

            self._send_signal({f"type": "room_inventory", "item_list":list_room_items_names})
            self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})
            if internal:
                return new_item_id
            return f"Item {item_display} created and placed in {location_desc}."
        else:
            # Should be covered by specific error messages above
            if internal:
                return False
            return f"Failed to create item {item_display} at location '{target_location}'."
        
    def trash_item(self, item_id: int, confirm: bool) -> str:
        """
        Removes an item by its ID *only* if it is located in the player's inventory.
        Items removed this way are permanently deleted from the state.
        Uses the existing remove_item method internally.

        Args:
            item_id (int): The ID of the item to trash from inventory.

        Returns:
            str: A message indicating success or failure (e.g., item not found, not in inventory).
        """
        if confirm:
            if not isinstance(item_id, int):
                return f"Failed to trash: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

            # Find the item to determine its current location
            item_info = self._find_item_info_by_id(item_id)

            if not item_info:
                return f"Failed to trash item: Item with ID '{item_id}' not found anywhere."

            item_data = item_info["item_data"]
            item_display = self._format_item_for_display(item_data)
            location = item_info["location"]

            # Check if the item is in the inventory
            if location != "inventory":
                # Item exists, but isn't in inventory
                if location == "room":
                    # Find the room name for a more informative message
                    room_name = self.get_room_name(item_info['location_id'])
                    return f"Failed to trash {item_display}: It is not in your inventory, it is in the {room_name}."
                else: # Should not happen with current known locations
                    return f"Failed to trash {item_display}: It is not in your inventory."

            # Item is confirmed to be in inventory, now remove it
            # The remove_item method handles the actual removal and state saving
            removal_result = self.remove_item(item_id)

            # The remove_item function already returns a success or failure message.
            # We can just return that message directly.
            # If remove_item succeeded, its message will indicate removal from 'your inventory'.
            # If it failed after finding the item in inventory (e.g., couldn't remove from list),
            # its error message is appropriate.
            if not removal_result.startswith("Error:"):
                # Success message from remove_item
                return f"You trashed the {item_display}."
            else:
                # Error message from remove_item
                print(f"Warning: trash_item called remove_item for {item_display} (ID:{item_id}) but it failed: {removal_result}")
                return f"Failed to trash {item_display}: {removal_result}"
        else:
            return f"Destruction of item {item_id} cancelled"
        
    def remove_item(self, item_id: int, internal=False):
        """
        Removes an item by its ID from wherever it is located (room or inventory).

        Args:
            item_id (int): The ID of the item to remove.

        Returns:
            str: A message indicating success or failure (e.g., item not found).
        """
        if not isinstance(item_id, int):
            if internal:
                False
            return f"Failed to remove: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        item_info = self._find_item_info_by_id(item_id)

        if not item_info:
            if internal:
                False
            return f"Failed to remove item: Item with ID '{item_id}' not found anywhere."

        item_data = item_info["item_data"] # Get the original item data dictionary
        item_display = self._format_item_for_display(item_data)
        location = item_info["location"]
        location_id = item_info["location_id"] # Room ID if in a room
        removed = False
        location_desc = "an unknown location"

        if location == "inventory":
            if isinstance(self._state.get("inventory"), list):
                initial_count = len(self._state["inventory"])
                # Filter inventory, keeping items whose ID is not the one we're removing
                self._state["inventory"] = [item for item in self._state["inventory"] if isinstance(item, dict) and item.get("id") != item_id]
                if len(self._state["inventory"]) < initial_count:
                    removed = True
                    location_desc = "your inventory"
                # else: Warning handled in pickup/drop, maybe log here too if filter failed

            else:
                if internal:
                    False
                return "Error: Cannot remove item from inventory, inventory state corrupted."

        elif location == "room":
            room_data = self._find_room_by_id(location_id)
            if room_data and isinstance(room_data.get("items"), list):
                initial_count = len(room_data["items"])
                # Filter room items, keeping items whose ID is not the one we're removing
                room_data["items"] = [item for item in room_data["items"] if isinstance(item, dict) and item.get("id") != item_id]
                if len(room_data["items"]) < initial_count:
                    removed = True
                    location_desc = f"the {self._format_room_for_display(room_data)}"
                # else: Warning handled in pickup/drop

            else:
                if internal:
                    False
                return f"Error: Cannot remove item from room '{location_id}', room data corrupted."

        else: # Should not happen with current locations
            if internal:
                False
            return f"Failed to remove item {item_display}: Unknown location type '{location}'."


        if removed:
            self._write_json(self._state) # Save state after removing the item
            list_room_items_names, list_inventory_item_names = self.list_inventories()
            self._send_signal({f"type": "room_inventory", "item_list":list_room_items_names})
            self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})
            if internal:
                True
            return f"Item {item_display} removed from {location_desc}."
        else:
            # This means the item was found by _find_item_info_by_id but the subsequent filter/removal failed.
            # Likely indicates a state inconsistency where the item wasn't actually in the list found by the lookup.
            return f"Failed to remove item {item_display} from {location_desc}: Could not remove from list."

    def get_all_rooms(self):
         """
         Lists all rooms in the game by name and ID.

         Returns:
             str: A comma-separated string of room descriptions (Name (ID:XXXXXX)),
                  or a message if no rooms are defined.
         """
         rooms_list = self._state.get("rooms") # Use .get()

         if isinstance(rooms_list, list): # Ensure it's a list before processing
              # Filter out invalid room data before formatting
              # Filter criteria: is a dict, has 'id', 'id' is int, 'name' is string
              valid_rooms = [
                  room for room in rooms_list
                  if isinstance(room, dict) and isinstance(room.get('id'), int) and isinstance(room.get('name'), str)
              ]
              room_display = [self._format_room_for_display(room) for room in valid_rooms]
              if room_display:
                   return f"Available rooms: {', '.join(room_display)}"
              else:
                   return "No rooms are currently defined."
         else:
              # This case should ideally be caught by validation, but defensive
              return "Error: Could not access room list. State might be corrupted."


    # --- Public Methods (Emote Management - NEW) ---

    def get_current_emote(self, internal: bool = False) -> str | dict:
        """
        Gets the current AI emote state.

        Args:
            act (bool): If True, perform the action (default True). If False, do nothing.
            internal (bool): If True, returns the raw emote state dictionary.
                             If False (default), returns a human-readable string.

        Returns:
            str or dict: The current emote state (internal=True) or a formatted message (internal=False).
                         Returns "unknown" or a corresponding message if state is invalid or act is False.
        """
        # Added robustness checks using .get() and isinstance
        current_emote = self._state.get("current_emote", "unknown")
        possible_emotes = self._state.get("possible_emotes", {})
        # Ensure possible_emotes is a dictionary before using it
        if not isinstance(possible_emotes, dict):
                possible_emotes = {} # Treat as empty if corrupted
                # Log warning? _post_init_state_validation should catch this, but defensive here.

        if internal:
            # Return the raw data (including the list of possible emotes)
            return {
                "current_emote": current_emote,
                "possible_emotes": possible_emotes
            }
        else:
            # Construct a human-readable string
            description = possible_emotes.get(current_emote, "no description available")
            # Refine message based on whether description is the fallback
            if description == "no description available" and current_emote != "unknown":
                    return f"The current emote is '{current_emote}', but its description is missing."
            elif current_emote == "unknown":
                    # This should only happen if validation failed or default is 'unknown'
                    return "The current emote is unknown or not set."
            else:
                    return f"The current emote is '{current_emote}'. Description: {description}"


    def get_possible_emotes(self, internal: bool = False) -> dict | str:
        """
        Gets the list of possible AI emotes and their descriptions.

        Args:
            act (bool): If True, perform the action (default True). If False, do nothing.
            internal (bool): If True, returns the raw dictionary of emotes.
                             If False (default), returns a human-readable string listing emotes and descriptions.

        Returns:
            dict or str: The dictionary of possible emotes (internal=True) or a formatted message (internal=False).
                         Returns an empty dict, message if state is invalid, or message if act is False.
        """
        # Added robustness checks using .get() and isinstance
        possible_emotes = self._state.get("possible_emotes", {})
        # Ensure possible_emotes is a dictionary before using it
        if not isinstance(possible_emotes, dict):
                possible_emotes = {} # Treat as empty if corrupted
                # Log warning?

        if internal:
            # Return the raw data
            # Ensure it's always a dictionary, even if state was bad or key was missing
            return possible_emotes
        else:
            # Construct a human-readable string
            if not possible_emotes:
                return "There are no possible emotes defined."

            message_lines = ["Here are the possible emotes:"]
            # Sort the keys alphabetically for consistent output
            for emote_name in sorted(possible_emotes.keys()):
                # Use .get() for description for robustness
                description = possible_emotes.get(emote_name, "no description available")
                message_lines.append(f"- '{emote_name}': {description}")

            return "\n".join(message_lines)


    def set_current_emote(self, emote_name: str, internal: bool = False) -> str | bool:
        """
        Sets the current emote if it exists in the possible_emotes list.
        Sends an 'emote_changed' signal on success.

        Args:
            emote_name (str): The name of the emote to set.
            internal (bool): If True, returns a boolean indicating success.
                             If False (default), returns a string message.

        Returns:
            str or bool: A string message (internal=False) or a boolean (True for success, False for failure) (internal=True).
        """
        if not isinstance(emote_name, str) or not emote_name.strip():
             message = "Error: Emote name must be a non-empty string."
             print(message) # Log internally
             return False if internal else message


        # Added robustness checks using .get() and isinstance
        possible_emotes = self._state.get("possible_emotes", {})
        # Ensure possible_emotes is a dictionary before using it
        if not isinstance(possible_emotes, dict):
             message = f"Error setting emote: 'possible_emotes' in state is not a dict ({type(possible_emotes).__name__}). Cannot set emote."
             print(message) # Log internally
             # We don't write state here as it's corrupted, validation should fix it on next load.
             return False if internal else message


        if emote_name in possible_emotes:
            # Check if the emote is already the current one
            current_emote = self._state.get("current_emote")
            if current_emote == emote_name:
                 message = f"The current emote is already '{emote_name}'."
                 # print(message) # Often not needed for success messages
                 return True if internal else message # Return success even if already set

            # Emote is valid and different from current, proceed to set
            self._state["current_emote"] = emote_name
            self._write_json(self._state) # Persist the change

            # Get description for the signal/message
            emote_description = possible_emotes.get(emote_name, "No description available.")

            # Send signal *after* state is updated and saved
            # Construct the signal data as defined in the original emoter.py
            self._send_signal({
                "type": "emote_changed",
                "emote_name": emote_name,
                "sound_path": f"style/sounds/{emote_name.lower()}.wav" # Assuming lowercase file names
            })

            # print(f"Current emote set to '{emote_name}'") # Keep print for internal logging
            if internal:
                # If internal, return True for success
                return True
            else:
                # If not internal, return a success message
                return f"Current emote successfully set to '{emote_name}' - {emote_description}"
        else:
            message = f"Error: Emote '{emote_name}' is not a possible emote. Available emotes: {', '.join(sorted(possible_emotes.keys()) if possible_emotes else ['none'])}"
            print(message) # Log internally
            if internal:
                # If internal, return False for failure
                return False
            else:
                return message # Return the informative error message

    # --- Public Methods (Book-Specific - Delegate to component - STAY here) ---
    # These methods call the corresponding methods on the _book_component instance

    def create_book_item(self, book_name: str, description: str) -> str:
        """
        Helper to create a new book item and place it in inventory.
        Uses the generic create_item method.

        Args:
            book_name (str): The name of the new book.
            description (str): A description for the new book.

        Returns:
            str: Message indicating success or failure.
        """
        if not isinstance(book_name, str) or not book_name.strip():
            return "Error: Book name must be a non-empty string."
        if not isinstance(description, str) or not description.strip():
            return "Error: Book description must be a non-empty string."

        book_data = {
            'name': book_name.strip(),
            'descriptions': [description.strip()], # Ensure descriptions is a list
            'static': False, # Books are typically not static
            'type': 'book',
            'chapters': [] # New books start with no chapters
        }
        # Delegate to the generic create_item method, placing in inventory
        return self.create_item("inventory", None, book_data)


    def list_inventory_books(self, internal=False) -> str | list[dict]:
         """
         Lists all book items currently in the player's inventory by name and ID.
         Delegates to BookComponent.

         Args:
            internal (bool): If True, returns a list of book dictionaries.
                             If False (default), returns a formatted string.

         Returns:
            str or list[dict]: A formatted string or a list of book item dictionaries.
         """
         # The BookComponent's list_inventory_books expects the raw inventory list
         inventory_list = self._state.get("inventory", [])
         if not isinstance(inventory_list, list):
              print("Warning: Inventory list corrupted, providing empty list to BookComponent.")
              inventory_list = [] # Provide empty list if state is bad

         return self._book_component.list_inventory_books(internal) # Pass inventory list


    def list_book_chapters(self, book_item_id: int) -> str:
        """
        Lists all chapter titles of a book item using its ID. Delegates to BookComponent.

        Args:
            book_item_id (int): The ID of the book item.

        Returns:
            str: A formatted string listing chapters or an error message.
        """
        # Find the item data using the generic helper
        item_info = self._find_item_info_by_id(book_item_id)
        if not item_info:
             return f"Error: No item found with ID '{book_item_id}'."

        item_data = item_info["item_data"]

        # Validate that it is indeed a book item
        is_valid_book, validation_msg = self._is_valid_item_data(item_data, check_id=True)
        if not is_valid_book or item_data.get("type") != "book":
             # Even if _is_valid_item_data passed, check the type explicitly
             if item_data.get("type") != "book":
                  return f"Error: Item with ID '{book_item_id}' ('{item_data.get('name', 'Unnamed')}') is not a book."
             else:
                 # This shouldn't happen if validation passed, but handle defensively
                 return f"Error: Item with ID '{book_item_id}' found but data is corrupted: {validation_msg}"


        # Check if the book is accessible (in current room or inventory) before listing chapters
        current_room_id = self._state.get("current_room_id")
        is_accessible = (item_info["location"] == "inventory") or (item_info["location"] == "room" and item_info["location_id"] == current_room_id)

        if not is_accessible:
             item_display = self._format_item_for_display(item_data)
             return f"You can only examine items in your current location or inventory. Item {item_display} is not here." # Simpler message for user

        # Delegate to the BookComponent, passing the item data
        return self._book_component.list_chapters(book_item_id)


    def read_book_chapter(self, book_item_id: int, chapter_title: str) -> str:
        """
        Reads the content of a specific chapter from a book item using its ID.
        Delegates to BookComponent.

        Args:
            book_item_id (int): The ID of the book item.
            chapter_title (str): The title of the chapter to read (case-insensitive).

        Returns:
            str: The chapter content or an error message.
        """
         # Find the item data using the generic helper
        item_info = self._find_item_info_by_id(book_item_id)
        if not item_info:
             return f"Error: No item found with ID '{book_item_id}'."

        item_data = item_info["item_data"]

        # Validate that it is indeed a book item
        is_valid_book, validation_msg = self._is_valid_item_data(item_data, check_id=True)
        if not is_valid_book or item_data.get("type") != "book":
             if item_data.get("type") != "book":
                  return f"Error: Item with ID '{book_item_id}' ('{item_data.get('name', 'Unnamed')}') is not a book."
             else:
                 return f"Error: Item with ID '{book_item_id}' found but data is corrupted: {validation_msg}"

        # Check if the book is accessible
        current_room_id = self._state.get("current_room_id")
        is_accessible = (item_info["location"] == "inventory") or (item_info["location"] == "room" and item_info["location_id"] == current_room_id)

        if not is_accessible:
             item_display = self._format_item_for_display(item_data)
             return f"You can only read books in your current location or inventory. Item {item_display} is not here."

        # Delegate to the BookComponent, passing the item data and chapter title
        return self._book_component.read_chapter(book_item_id, chapter_title)


    def add_book_chapter(self, book_item_id: int, chapter_title: str, content: str) -> str:
        """
        Adds a new chapter to a book item using its ID. Delegates to BookComponent.

        Args:
            book_item_id (int): The ID of the book item.
            chapter_title (str): The title for the new chapter.
            content (str): The content for the new chapter.

        Returns:
            str: Message indicating success or failure.
        """
         # Find the item data using the generic helper
        item_info = self._find_item_info_by_id(book_item_id)
        if not item_info:
             return f"Error: No item found with ID '{book_item_id}'."

        item_data = item_info["item_data"]

        # Validate that it is indeed a book item
        is_valid_book, validation_msg = self._is_valid_item_data(item_data, check_id=True)
        if not is_valid_book or item_data.get("type") != "book":
             if item_data.get("type") != "book":
                  return f"Error: Item with ID '{book_item_id}' ('{item_data.get('name', 'Unnamed')}') is not a book."
             else:
                 return f"Error: Item with ID '{book_item_id}' found but data is corrupted: {validation_msg}"

        # Delegate to the BookComponent, passing the item data and new chapter details
        result = self._book_component.add_chapter(book_item_id, chapter_title, content)

        # If the component modified the item data successfully, save the state
        # The component doesn't save, it just modifies the dict reference passed to it.
        # We need to check if the component indicated success and then save here.
        # A simple way is to check the message doesn't start with "Error:".
        if not result.startswith("Error:"):
            self._write_json(self._state) # Save the state changes
            # Optional: Send a signal about the book content change
            # self._send_signal({"type": "book_updated", "item_id": book_item_id})
        return result


    def update_book_chapter(self, book_item_id: int, chapter_title: str, new_content: str) -> str:
        """
        Updates the content of a chapter in a book item using its ID. Delegates to BookComponent.

        Args:
            book_item_id (int): The ID of the book item.
            chapter_title (str): The title of the chapter to update (case-insensitive).
            new_content (str): The new content for the chapter.

        Returns:
            str: Message indicating success or failure.
        """
         # Find the item data using the generic helper
        item_info = self._find_item_info_by_id(book_item_id)
        if not item_info:
             return f"Error: No item found with ID '{book_item_id}'."

        item_data = item_info["item_data"]

        # Validate that it is indeed a book item
        is_valid_book, validation_msg = self._is_valid_item_data(item_data, check_id=True)
        if not is_valid_book or item_data.get("type") != "book":
             if item_data.get("type") != "book":
                  return f"Error: Item with ID '{book_item_id}' ('{item_data.get('name', 'Unnamed')}') is not a book."
             else:
                 return f"Error: Item with ID '{book_item_id}' found but data is corrupted: {validation_msg}"

        # Delegate to the BookComponent, passing the book item ID, chapter title and new content
        result = self._book_component.update_chapter(book_item_id, chapter_title, new_content)

        # If the component modified the item data successfully, save the state
        if not result.startswith("Error:"):
            self._write_json(self._state) # Save the state changes
            # Optional: Send a signal about the book content change
            # self._send_signal({"type": "book_updated", "item_id": book_item_id})
        return result


    def delete_book_chapter(self, book_item_id: int, chapter_title: str) -> str:
        """
        Deletes a chapter from a book item using its ID. Delegates to BookComponent.

        Args:
            book_item_id (int): The ID of the book item.
            chapter_title (str): The title of the chapter to delete (case-insensitive).

        Returns:
            str: Message indicating success or failure.
        """
         # Find the item data using the generic helper
        item_info = self._find_item_info_by_id(book_item_id)
        if not item_info:
             return f"Error: No item found with ID '{book_item_id}'."

        item_data = item_info["item_data"]

        # Validate that it is indeed a book item
        is_valid_book, validation_msg = self._is_valid_item_data(item_data, check_id=True)
        if not is_valid_book or item_data.get("type") != "book":
             if item_data.get("type") != "book":
                  return f"Error: Item with ID '{book_item_id}' ('{item_data.get('name', 'Unnamed')}') is not a book."
             else:
                 return f"Error: Item with ID '{book_item_id}' found but data is corrupted: {validation_msg}"

        # Delegate to the BookComponent, passing the item data and chapter title
        result = self._book_component.delete_chapter(item_data, chapter_title)

         # If the component modified the item data successfully, save the state
        if not result.startswith("Error:"):
            self._write_json(self._state) # Save the state changes
            # Optional: Send a signal about the book content change
            # self._send_signal({"type": "book_updated", "item_id": book_item_id})
        return result

    def sleep(self, seconds):
        constant = 1
        # Using square root:
        energy_gain = constant * math.sqrt(seconds)
        #int_gain=int(energy_gain)
        self.adjust_stat("energy", energy_gain)
        self._send_signal({"type": "sleep", "duration": seconds})
        return f"Sleeping for: {seconds}, after you send your last message in this chain of actions, you will sleep for that ammount of time. This action will restore a total of {energy_gain} energy points. Make sure your next output only contains a message and no more actions. Get ready to sleep!"

    # --- Public Methods (Stats-Specific - Delegate to component - STAY here) ---

    # --- Public Methods (Stats Management - Delegate to component - NEW) ---

    def get_stats(self, internal: bool = False) -> str | dict:
        """
        Retrieves the current stats (fullness, hydration, or energy).
        Delegates to StatsComponent.

        Args:
            internal (bool): If True, returns the raw stats dictionary.
                             If False (default), returns a human-readable string.

        Returns:
            str or dict: The current stats dictionary (internal=True) or a formatted message (internal=False).
                         Returns an error message if the stats system is not available.
        """
        # Delegate the call to the StatsComponent instance
        if self._stats_component is not None:
             return self._stats_component.get_stats(internal)
        else:
             # Fallback/Error if component wasn't initialized
             print("Warning: Stats component not available when get_stats was called.")
             if internal:
                  # Return a standard structure indicating error for internal use
                  # Optionally try to return the raw state stats if they exist, though potentially corrupted
                  return {"status": "error", "message": "Stats system not available.", "stats_data_raw": self._state.get("stats", {})}
             else:
                  # Return a user-friendly error message
                  return "Error: Stats system not available."


    def adjust_stat(self, stat_name: str, amount: int|float) -> str | int | float:
        """
        Adjusts a specific stat (fullness, hydration, or energy) by a given amount.
        Positive amount increases, negative decreases. Caps at 0 and 100.
        Delegates to StatsComponent which handles state modification, saving, and signals.

        Args:
            stat_name (str): The name of the stat ('fullness', 'hydration', 'energy'). Case-insensitive.
            amount (int|float): The amount to add (positive) or subtract (negative) from the stat value.

        Returns:
            str: Message indicating success or failure or no change.
                 Returns an error message if the stats system is not available.
        """
        # Delegate the call to the StatsComponent instance
        # The component handles validation, state modification, saving, and signaling.
        if self._stats_component is not None:
             return self._stats_component.adjust_stat(stat_name, amount)
        else:
             # Fallback/Error if component wasn't initialized
             print("Warning: Stats component not available when adjust_stat was called.")
             return "Error: Stats system not available, unable to adjust stat."


    # --- NEW PUBLIC METHOD for Consumables ---
    def consume_item(self, item_id: int) -> str:
        """
        Allows the player to consume an item by its ID if it is in their inventory
        and is of type 'consumable'. Applies stat effects and removes the item.

        Args:
            item_id (int): The ID of the item to consume.

        Returns:
            str: A message indicating the outcome (success with effects, or failure).
        """
        if not isinstance(item_id, int):
            return f"Failed to consume: Item ID must be an integer, received '{item_id}' ({type(item_id).__name__})."

        # 1. Find the item by ID
        item_info = self._find_item_info_by_id(item_id)
        if not item_info:
            return f"Failed to consume: Item with ID '{item_id}' not found anywhere."

        item_data = item_info["item_data"]
        item_display = self._format_item_for_display(item_data)

        # 2. Check if it's in inventory
        if item_info["location"] != "inventory":
            return f"Failed to consume {item_display}: You can only consume items from your inventory. It is in {item_info['location']}."

        # 3. Validate the item data (includes type and consumable-specific checks)
        # This should have been done during loading/creation, but defensive check
        is_valid, msg = self._is_valid_item_data(item_data, check_id=True)
        if not is_valid:
            print(f"Warning: Attempted to consume invalid item ID {item_id}: {msg}. Removing from inventory due to corruption.")
            # Attempt to remove the corrupted item
            remove_result = self.remove_item(item_id) # This also saves state
            return f"Failed to consume {item_display}: Item data is corrupted. It has been removed from your inventory. ({msg})"


        # 4. Check if it's a consumable item
        if item_data.get("type") != "consumable":
            # Use .get() for type for safety, though validation should ensure it exists
            return f"Failed to consume {item_display}: This item is not a consumable type ({item_data.get('type', 'unknown type')})."

        # 5. Get stat effects and text effects (use .get for safety, provide defaults)
        stats_edit = item_data.get("stats_edit", {})
        effects_text_list = item_data.get("effects", []) # Default to empty list if missing

        # 6. Apply stat effects using the StatsComponent
        if self._stats_component is None:
            # Stats component failed to initialize
             print("Warning: StatsComponent not available during item consumption.")
             # Decide how to handle this - consume item anyway? Or fail?
             # Let's fail, as the primary effect (stat change) cannot happen.
             return f"Failed to consume {item_display}: The stats system is not available."

        # Call the component to apply effects; it handles clamping and signaling
        # It returns a dict of actual changes or None if stats data is corrupted
        stat_changes_summary = self._stats_component.apply_consumable_effects(stats_edit)

        if stat_changes_summary is None:
             # Stats component reported corrupted stats data
             return f"Failed to consume {item_display}: Error applying effects, stats data is corrupted."

        # 7. Remove the item from inventory
        # Do this manually here *after* effects are applied but *before* saving the overall state
        if isinstance(self._state.get("inventory"), list):
             initial_count = len(self._state["inventory"])
             # Filter inventory, keeping items whose ID is not the one we're consuming
             self._state["inventory"] = [item for item in self._state["inventory"] if isinstance(item, dict) and item.get("id") != item_id]

             if len(self._state["inventory"]) == initial_count:
                 # Item wasn't removed, indicates inconsistency
                 print(f"Warning: Item ID '{item_id}' not removed from inventory list during consumption.")
                 # Decide if this is a fatal error - item consumed effects but not removed
                 # Let's proceed but warn, as effects were applied. The user gets the effect but keeps the item.
                 removal_status = f"Warning: Item {item_display} consumed but could not be removed from inventory list."
                 print(removal_status) # Log the warning
             else:
                  removal_status = f"Item {item_display} consumed."
        else:
             # Inventory list corrupted during the process (unlikely if validation passed)
             print("Critical Error: Inventory state corrupted during item removal after consumption effects applied.")
             removal_status = f"Item {item_display} consumed effects, but inventory is corrupted and item removal failed."


        # 8. Select a random effect text (if available and valid)
        selected_effect_text = ""
        if isinstance(effects_text_list, list) and all(isinstance(text, str) for text in effects_text_list):
            valid_effect_texts = [text.strip() for text in effects_text_list if text and text.strip()] # Get non-empty strings
            if valid_effect_texts:
                selected_effect_text = random.choice(valid_effect_texts)
        else:
             # This case should be caught by _is_valid_item_data, but defensive
             print(f"Warning: Consumable item ID {item_id} ('{item_data.get('name', 'Unnamed')}') had invalid 'effects' structure.")


        # 9. Construct the final message
        message = removal_status

        # Add stat changes summary if any stats were actually changed
        if stat_changes_summary:
            changes_strings = []
            for stat, change in stat_changes_summary.items():
                # Format change amount with sign
                sign = "+" if change >= 0 else "" # Add + sign for positive changes
                changes_strings.append(f"{stat}: {sign}{change:.1f} points")
            message += f"\nYour stats changed: {', '.join(changes_strings)}."
             # Optionally add current stats here:
            current_stats_msg = self.get_stats(internal=False) # Calls component for formatted string
            if not current_stats_msg.startswith("Error:"):
                message += f"\n{current_stats_msg.replace('Current Stats: ', '')}" # Add just the values

        # Add the random effect text if selected
        if selected_effect_text:
            message += f"\n{selected_effect_text}"


        # 10. Save the state (both inventory changes and stat changes are now in self._state)
        self._write_json(self._state)
    
        list_room_items_names, list_inventory_item_names = self.list_inventories()

        self._send_signal({f"type": "room_inventory", "item_list":list_room_items_names})
        self._send_signal({f"type": "player_inventory", "item_list": list_inventory_item_names})

        return message

    # ... existing public book methods ...
    # ... example usage __main__ block ...

# Example Usage (for testing the class)
if __name__ == "__main__":
    # Create a directory for the state file
    state_dir = "tool_states_house_emote_test" # New test directory name
    json_file_path = os.path.join(state_dir, 'house_inventory_state_id.json') # File name inside directory

    # Clean up existing file for a clean test run
    if os.path.exists(json_file_path):
        try:
            os.remove(json_file_path)
            print("Removed existing state file for clean test.")
        except OSError as e:
            print(f"Error removing existing state file: {e}")
    # Ensure the test directory exists
    os.makedirs(state_dir, exist_ok=True)

    # Simple signal callback for testing
    def test_signal_callback(data):
        print(f"--- RECEIVED SIGNAL: {data} ---")

    print("\n--- Initializing Manager (should use default state) ---")
    # Pass the test signal callback
    manager = InventoryHouseManager(state_dir, signal=test_signal_callback)

    print("\n--- Getting initial Emote state ---")
    print(manager.get_current_emote()) # Should be neutral
    print(manager.get_possible_emotes()) # Should list defaults

    print("\n--- Getting initial Emote state (internal) ---")
    print(json.dumps(manager.get_current_emote(internal=True), indent=4))
    print(json.dumps(manager.get_possible_emotes(internal=True), indent=4))


    print("\n--- Setting Emote to 'happy' ---")
    print(manager.set_current_emote("happy")) # Should succeed and send signal

    print("\n--- Getting Emote state after setting ---")
    print(manager.get_current_emote()) # Should be happy

    print("\n--- Setting Emote to 'thinking' ---")
    print(manager.set_current_emote("thinking")) # Should succeed and send signal

    print("\n--- Getting Emote state after setting again ---")
    print(manager.get_current_emote()) # Should be thinking

    print("\n--- Setting Emote to an invalid emote ---")
    print(manager.set_current_emote("silly_face")) # Should fail and list options

    print("\n--- Getting Emote state after failed set ---")
    print(manager.get_current_emote()) # Should still be thinking

    print("\n--- Test internal=True for set_current_emote ---")
    print(f"Setting 'happy' internally: {manager.set_current_emote('happy', internal=True)}")
    print(f"Setting 'silly_face' internally: {manager.set_current_emote('silly_face', internal=True)}")
    print(manager.get_current_emote()) # Should be happy

    print("\n--- Getting other initial states to show they still work ---")
    print(f"Current Room ID: {manager.get_current_room_id()}")
    print(f"Current Room Name: {manager.get_current_room_name()}")
    print(manager.get_items_in_current_room())
    print(manager.get_inventory_items())
    print(manager.get_all_rooms())


    print("\n--- List books in inventory (delegated call) ---")
    print(manager.list_inventory_books())

    print("\n--- Get details for the default book item (internal=False) ---")
    # Find the ID of the default book for testing
    default_book_id = -1
    # Use internal=True first to safely get the item data for its ID
    default_book_info = manager.get_item_details(100004, internal=True) # Assuming default ID 100004
    if default_book_info and default_book_info.get('status') == 'found':
         default_book_id = default_book_info['details'].get('id')
         print(f"Default book (Mysteries of the Cozy House) ID: {default_book_id}")
         # Now test the public (internal=False) output
         print("\n--- Public Details for default book item ---")
         print(manager.get_item_details(default_book_id, internal=False))

         # Test internal=True output again to show the difference
         print("\n--- Internal Details for default book item ---")
         print(json.dumps(manager.get_item_details(default_book_id, internal=True), indent=4))


         print("\n--- List chapters of the default book (delegated call) ---")
         print(manager.list_book_chapters(default_book_id))

         print("\n--- Read a chapter from the default book (delegated call) ---")
         print(manager.read_book_chapter(default_book_id, "The Creaking Floorboard")) # Case-insensitive match test

         print("\n--- Add a new chapter to the default book (delegated call) ---")
         print(manager.add_book_chapter(default_book_id, "The Secret Attic", "The attic was full of dust and old memories."))
         print(manager.list_book_chapters(default_book_id)) # Verify new chapter is listed

         print("\n--- Update a chapter in the default book (delegated call) ---")
         print(manager.update_book_chapter(default_book_id, "The Creaking Floorboard", "It was a dark and stormy night. The floorboard creaked ominously."))
         print(manager.read_book_chapter(default_book_id, "The Creaking Floorboard")) # Read updated content

         print("\n--- Delete a chapter from the default book (delegated call) ---")
         print(manager.delete_book_chapter(default_book_id, "Whispers in the Walls"))
         print(manager.list_book_chapters(default_book_id)) # Verify chapter is gone

    else:
         print("\n--- Could not find the default book item ID! Skipping book-specific tests. ---")


    print("\n--- Creating a new book item using create_book_item (delegated call) ---")
    print(manager.create_book_item("Adventure Journal", "A small, leather-bound journal."))
    print(manager.list_inventory_books()) # Should list the new book

    print("\n--- Test examining the new book in inventory (internal=False) ---")
    # Find the ID of the new book
    inventory_books_str = manager.list_inventory_books()
    adventure_book_id = -1
    import re
    match = re.search(r"Adventure Journal \(ID:(\d+)\)", inventory_books_str)
    if match:
         adventure_book_id = int(match.group(1))
         print(f"Found Adventure Journal ID: {adventure_book_id}")

         print(manager.get_item_details(adventure_book_id, internal=False)) # Should show name/ID and descriptions

         print("\n--- Add a chapter to the Adventure Journal ---")
         print(manager.add_book_chapter(adventure_book_id, "Day 1", "Started my journey..."))
         print(manager.list_book_chapters(adventure_book_id))

         print("\n--- Read the new chapter ---")
         print(manager.read_book_chapter(adventure_book_id, "Day 1"))

         print("\n--- Remove the Adventure Journal item from inventory (using generic remove_item) ---")
         print(manager.remove_item(adventure_book_id))
         print(manager.get_inventory_items()) # Should be gone
         print(manager.list_inventory_books()) # Should be gone


    else:
         print("\n--- Could not find Adventure Journal ID after creation! Skipping related tests. ---")

    print("\n--- State file should now exist and reflect all changes ---")
    if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
        print(f"State successfully saved to {json_file_path}")
        # Read the file to confirm emote state is present
        with open(json_file_path, 'r') as f:
            saved_state = json.load(f)
            print("\n--- Emote state in saved file ---")
            print(f"current_emote: {saved_state.get('current_emote')}")
            print(f"possible_emotes keys: {list(saved_state.get('possible_emotes', {}).keys())}")

    else:
        print(f"Error: State file {json_file_path} was not created or is empty.")

    print("\n--- Initializing Manager again (should load state with happy emote) ---")
    manager2 = InventoryHouseManager(state_dir, signal=test_signal_callback)
    print(f"Current Room ID: {manager2.get_current_room_id()}")
    print(manager2.get_items_in_current_room())
    print(manager2.get_inventory_items())
    print(manager2.list_inventory_books())
    print("\n--- Emote state after reloading ---")
    print(manager2.get_current_emote()) # Should be happy

    # Re-find the default book ID if needed for checking its final state
    default_book_id_2 = -1
    inventory_items_on_reload = manager2._state.get("inventory", []) # Use .get()
    if isinstance(inventory_items_on_reload, list):
        for item in inventory_items_on_reload:
            if isinstance(item, dict) and item.get("name") == "Mysteries of the Cozy House":
                 default_book_id_2 = item.get("id")
                 break
    if default_book_id_2 != -1:
         print(f"\n--- Final chapters in default book (ID:{default_book_id_2:06d}) after tests ---")
         print(manager2.list_book_chapters(default_book_id_2)) # Should list "The Creaking Floorboard" (updated) and "The Secret Attic" (added), NOT "Whispers in the Walls" (deleted)
    else:
        print("\n--- Default book not found after reload! ---")