
# services/state_store.py
import json
import copy # For deep copying default state

# Assuming generic_json_tool.py is in utils, adjust import if different
try:
    from utils.generic_json_tool import GenericJsonTool
except ImportError:
    print("Error: generic_json_tool.py not found. Make sure it's in the same directory or PYTHONPATH.")
    import sys; sys.exit(1)

class StateStore(GenericJsonTool):
    ITEM_ID_START_COUNTER = 1 # Re-define constants here or pass from config
    ROOM_ID_START_COUNTER = 1

    def __init__(self, base_path, default_state): # Removed config_manager, will get default_state directly
        self.json_filename = 'house_inventory_state_id.json'
        # Use deepcopy to ensure modifications to _state don't affect original default_state dict
        self._default_state = copy.deepcopy(default_state)
        super().__init__(base_path) # Loads/creates self._state

        # Perform initial state integrity checks and ID assignments
        self._assign_missing_ids()
        self._post_init_state_validation()

        # Ensure save after initial setup/validation
        self._write_json(self._state)


    def get_state_section(self, key, default=None):
        """Provides read-access to a section of the state."""
        return self._state.get(key, default)

    def update_state_section(self, key, value):
        """Updates a section of the state and persists it to disk."""
        self._state[key] = value
        self._write_json(self._state)

    def get_full_state(self):
        """Returns the entire raw state dictionary. Use with caution."""
        return self._state

    def save_state(self):
        """Manually triggers a save of the current state."""
        self._write_json(self._state)

    # --- ID Generation Methods (MOVED HERE) ---
    def get_next_item_id(self):
        """Generates and increments the next unique item ID."""
        next_id = self._state.get("next_item_id", self.ITEM_ID_START_COUNTER)
        if not isinstance(next_id, int) or next_id < self.ITEM_ID_START_COUNTER:
            next_id = self.ITEM_ID_START_COUNTER
            print(f"Warning: Resetting next_item_id counter due to invalid value: {self._state.get('next_item_id')}")
            self._state["next_item_id"] = next_id
            self.save_state() # Save immediate correction

        self._state["next_item_id"] = next_id + 1
        if next_id + 1 > 999999:
            print(f"Warning: Item ID counter exceeds 6 digits ({next_id + 1}). Consider implementing ID reuse or expansion.")
        # Note: The incremented counter is saved with the next call to update_state_section or save_state.
        # For robustness, could save here if generating a new ID implies a change that must be persisted immediately.
        # But typically, ID generation is followed by an action that also causes a save.
        return next_id

    def get_next_room_id(self):
        """Generates and increments the next unique room ID."""
        next_id = self._state.get("next_room_id", self.ROOM_ID_START_COUNTER)
        if not isinstance(next_id, int) or next_id < self.ROOM_ID_START_COUNTER:
            next_id = self.ROOM_ID_START_COUNTER
            print(f"Warning: Resetting next_room_id counter due to invalid value: {self._state.get('next_room_id')}")
            self._state["next_room_id"] = next_id
            self.save_state() # Save immediate correction

        self._state["next_room_id"] = next_id + 1
        if next_id + 1 > 999999:
            print(f"Warning: Room ID counter exceeds 6 digits ({next_id + 1}). Consider implementing ID reuse or expansion.")
        return next_id

    # --- Post-Init Validation (MOVED HERE, adapted to operate on self._state) ---
    def _assign_missing_ids(self):
        # This method needs to *modify* self._state.
        # The logic remains largely the same, but now it uses self.get_next_item_id()
        # and self.get_next_room_id() which are *also* methods of StateStore.
        # Make sure to call self.save_state() at the end if changes were made.
        needs_save = False

        # First pass: Assign missing IDs to rooms and items based on next_id counters.
        # This ensures all rooms and items have stable IDs before we decide on the start room.
        rooms_list = self._state.get("rooms")
        if isinstance(rooms_list, list):
            for i, room in enumerate(rooms_list):
                if isinstance(room, dict):
                    if 'id' not in room:
                        room['id'] = self.get_next_room_id() # Use StateStore's ID generator
                        needs_save = True

                    if isinstance(room.get("items"), list):
                            for j, item in enumerate(room["items"]):
                                if isinstance(item, dict) and 'id' not in item:
                                    item['id'] = self.get_next_item_id() # Use StateStore's ID generator
                                    needs_save = True

        inventory_list = self._state.get("inventory")
        if isinstance(inventory_list, list):
            for i, item in enumerate(inventory_list):
                    if isinstance(item, dict) and 'id' not in item:
                        item['id'] = self.get_next_item_id() # Use StateStore's ID generator
                        needs_save = True

        # Second pass: Handle setting the initial current_room_id if it was defaulted to 0
        if self._state.get("current_room_id") == 0:
            print("Initial current_room_id is 0. Determining actual start room...")
            target_start_room_id = 0

            found_preferred_start_room = False
            if isinstance(rooms_list, list) and len(rooms_list) > 0:
                for room in rooms_list:
                    if isinstance(room, dict) and room.get("id") == target_start_room_id:
                        self._state["current_room_id"] = target_start_room_id
                        needs_save = True
                        found_preferred_start_room = True
                        break

                if not found_preferred_start_room:
                    first_room = rooms_list[0]
                    if isinstance(first_room, dict) and isinstance(first_room.get("id"), int):
                        print(f"No room with ID {target_start_room_id} found. Setting current_room_id from default 0 to the ID of the first room ('{first_room.get('name', 'Unnamed')}'), which is {first_room['id']}.")
                        self._state["current_room_id"] = first_room["id"]
                        needs_save = True
                    else:
                        print("Warning: Initial current_room_id was 0, but no rooms found or first room has no valid ID after assignment.")
            elif not rooms_list:
                    print("Warning: Initial current_room_id is 0 but no rooms are defined.")

        if needs_save:
            print("Finished assigning missing IDs and setting initial room if needed. Saving state.")
            self.save_state()

    def _post_init_state_validation(self):
        # This method needs to *modify* self._state.
        # All validation logic, including for emotes, stats, pet color, steps, sim_state,
        # rooms, and inventory, will be here.
        # Make sure to call self.save_state() at the end if changes were made.
        needs_save = False

        # --- Validate ID counters ---
        if not isinstance(self._state.get("next_item_id"), int) or self._state.get("next_item_id", 0) < self.ITEM_ID_START_COUNTER:
            print(f"Validation Warning: 'next_item_id' invalid ({self._state.get('next_item_id')}). Resetting to start counter {self.ITEM_ID_START_COUNTER}.")
            self._state["next_item_id"] = self.ITEM_ID_START_COUNTER
            needs_save = True
        if not isinstance(self._state.get("next_room_id"), int) or self._state.get("next_room_id", 0) < self.ROOM_ID_START_COUNTER:
            print(f"Validation Warning: 'next_room_id' invalid ({self._state.get('next_room_id')}). Resetting to start counter {self.ROOM_ID_START_COUNTER}.")
            self._state["next_room_id"] = self.ROOM_ID_START_COUNTER
            needs_save = True

        # --- Validate basic structure keys and types ---
        if not isinstance(self._state.get("current_room_id"), int):
            print("Validation Warning: 'current_room_id' missing or not integer. Setting to default from _default_state.")
            self._state["current_room_id"] = self._default_state.get("current_room_id", -1)
            needs_save = True

        if not isinstance(self._state.get("rooms"), list):
            print("Validation Warning: 'rooms' missing or not list. Resetting to default.")
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

        ## --- Validate Currency State --- 

        currency_data = self._state.get("currency")
        default_currency_data = self._default_state.get("currency", 150)

        if currency_data is None or not isinstance(currency_data, (int, float)):
            print(f"Validation Warning: 'currency' missing or invalid ({currency_data}). Resetting to default ({default_currency_data}).")
            self._state["currency"] = default_currency_data
            needs_save = True
        elif currency_data < 0:
            print(f"Validation Warning: 'currency' value ({currency_data}) is negative. Clamping to 0.")
            self._state["currency"] = 0
            needs_save = True

        # --- Validate Rooms ---
        room_ids_seen = set()
        valid_rooms = []
        # Need a helper for _is_valid_item_data if this is to remain in StateStore,
        # or move the specific validation here. For now, assuming a helper that will be provided.
        # This is a bit tricky as _is_valid_item_data has item_types which is domain specific.
        # Best approach: _post_init_state_validation in StateStore does *structural* validation.
        # Domain-specific validation (e.g., specific item types) happens in their respective services.
        # For this example, let's keep it here, assuming ALLOWED_ITEM_TYPES is somehow accessible or
        # define a simplified item validation for structural checks only.
        # For a proper refactor, _is_valid_item_data would be in InventoryService.

        # Temporary _is_valid_item_data stub for StateStore's validation
        def _local_is_valid_item_data(item_data, check_id=False):
            if not isinstance(item_data, dict): return False, "Not a dict"
            if check_id and (item_data.get('id') is None or not isinstance(item_data.get('id'), int)): return False, "Invalid ID"
            if not isinstance(item_data.get('name'), str) or not item_data.get('name').strip(): return False, "Invalid name"
            if not isinstance(item_data.get('descriptions'), list) or not all(isinstance(d, str) for d in item_data.get('descriptions')): return False, "Invalid descriptions"
            
            # --- CORRECTED: static validation - just check type, do NOT alter value ---
            if 'static' not in item_data or not isinstance(item_data.get('static'), bool): 
                return False, "Invalid 'static' (must be bool) or missing."
            # --- END CORRECTED ---

            item_type = item_data.get("type", [])
            if not isinstance(item_type, list) or not item_type or not all(isinstance(t, str) for t in item_type): return False, "Invalid type list"

            # Stacking attributes validation for _local_is_valid_item_data (remains mostly same as before, but note it also shouldn't change existing values)
            stackable = item_data.get("stackable", False)
            if not isinstance(stackable, bool): return False, "Invalid 'stackable' (must be bool)"
            # item_data["stackable"] = stackable # No longer force default here, let _is_valid_item_data in InventoryService handle it better or assume input is okay

            quantity = item_data.get("quantity", 1)
            if not isinstance(quantity, int) or quantity <= 0: return False, "Invalid 'quantity' (must be positive int)"
            item_data["quantity"] = quantity # No longer force default here

            max_stack_size = item_data.get("max_stack_size")
            if max_stack_size is not None and (not isinstance(max_stack_size, int) or max_stack_size <= 0):
                return False, "Invalid 'max_stack_size' (must be positive int or None)"

            # This part is a *validation* on existing data, not a modification for non-stackable.
            # It's okay to warn/fail if an existing non-stackable has quantity > 1.
            if not stackable and (quantity > 1 or (max_stack_size is not None and max_stack_size > 1)):
                # If the item is marked as non-stackable, its quantity must be 1.
                # If this fails, it indicates an issue in the loaded state or default state.
                return False, "Non-stackable item has quantity > 1 or max_stack_size > 1."

            return True, ""

        rooms_list_to_validate = self._state.get("rooms", [])

        rooms_list_to_validate = self._state.get("rooms", [])
        for room in rooms_list_to_validate:
            if not isinstance(room, dict):
                print(f"Validation Warning: Found non-dict entry in rooms list: {room}. Removing.")
                needs_save = True
                continue
            required_room_keys = ["id", "name", "descriptions", "items", "image", "room_types"]
            if not all(key in room for key in required_room_keys):
                print(f"Validation Warning: Room missing required keys ({required_room_keys}): ID {room.get('id', 'unknown')}. Removing.")
                needs_save = True
                continue
            if not isinstance(room.get("image"), str):
                print(f"Validation Warning: Room '{room.get('name', 'Unnamed Room')}' has non-string image name. Removing")
                needs_save =True
                continue
            if not isinstance(room.get("music"), str) and room.get("music") is not None: # Allow music to be None
                print(f"Validation Warning: Room '{room.get('name', 'Unnamed Room')}' has non-string music name. Removing")
                needs_save =True
                continue
            if not isinstance(room.get("room_types"), list) or not all(isinstance(d, str) for d in room.get("room_types", [])):
                print(f"Validation Warning: Room '{room.get('name', 'Unnamed Room')}' has non-string room_type. Removing")
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
            if not isinstance(room.get("descriptions"), dict): # Now expects a dict for descriptions
                print(f"Validation Warning: Room '{room['name']}' (ID:{room['id']}) has invalid descriptions (not dictionary). Correcting to empty dict.")
                room["descriptions"] = {}
                needs_save = True
            if not isinstance(room.get("items"), list):
                print(f"Validation Warning: Room '{room['name']}' (ID:{room['id']}) has invalid 'items' (not list). Correcting to empty list.")
                room["items"] = []
                needs_save = True

            # Specific validation for "planting_garden" room_type
            if "planting_garden" in room.get("room_types", []):
                if not isinstance(room.get("plot_number"), int):
                    print(f"Validation Warning: Room '{room['name']}' (ID:{room['id']}) has invalid 'plot_number' (not int). Correcting to base number.")
                    room["plot_number"] = 3
                    needs_save = True

            original_item_count_in_room = len(room.get("items", []))
            valid_room_items_list = []
            if isinstance(room.get("items"), list):
                for item in room["items"]:
                    is_valid, msg = _local_is_valid_item_data(item, check_id=True)
                    if not is_valid:
                        print(f"Validation Warning: Invalid item found in room ID {room.get('id', 'unknown')}: {msg}. Removing.")
                        needs_save = True
                        continue
                    valid_room_items_list.append(item)
            room["items"] = valid_room_items_list
            if len(room["items"]) < original_item_count_in_room:
                needs_save = True

            room_ids_seen.add(room["id"])
            valid_rooms.append(room)

        self._state["rooms"] = valid_rooms

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
        for room in self._state.get("rooms", []):
            if isinstance(room, dict) and isinstance(room.get("items"), list):
                for item in room["items"]:
                    if isinstance(item, dict) and isinstance(item.get('id'), int):
                            if item['id'] in item_ids_seen:
                                print(f"Validation Warning: Duplicate item ID found ({item['id']}) in room ID {room.get('id', 'unknown')}. Item '{item.get('name', 'Unnamed')}'. This instance will be removed during final item list construction.")
                                needs_save = True
                            item_ids_seen.add(item['id'])

        valid_inventory_items_list = []
        inventory_list_to_validate = self._state.get("inventory")
        if isinstance(inventory_list_to_validate, list):
            original_inventory_count = len(inventory_list_to_validate)
            for item in inventory_list_to_validate:
                is_valid, msg = _local_is_valid_item_data(item, check_id=True)
                if not is_valid:
                    print(f"Validation Warning: Invalid item found in inventory: {msg}. Removing.")
                    needs_save = True
                    continue
                if isinstance(item, dict) and isinstance(item.get('id'), int):
                    if item['id'] in item_ids_seen:
                            print(f"Validation Warning: Duplicate item ID found ({item['id']}) in inventory. Item '{item.get('name', 'Unnamed')}'. Removing this instance.")
                            needs_save = True
                            continue
                    item_ids_seen.add(item['id'])
                    valid_inventory_items_list.append(item)
                else:
                    print(f"Validation Warning: Item passed basic validation but ID invalid: {item}. Removing.")
                    needs_save = True
                    continue

            self._state["inventory"] = valid_inventory_items_list
            if len(self._state["inventory"]) < original_inventory_count:
                needs_save = True

        max_existing_item_id = max(list(item_ids_seen) + [self.ITEM_ID_START_COUNTER - 1])
        if self._state.get("next_item_id", 0) <= max_existing_item_id:
            print(f"Validation Warning: 'next_item_id' ({self._state.get('next_item_id')}) is not greater than the highest existing item ID ({max_existing_item_id}). Adjusting.")
            self._state["next_item_id"] = max_existing_item_id + 1
            needs_save = True

        max_existing_room_id = max(list(room_ids_seen) + [self.ROOM_ID_START_COUNTER - 1])
        if self._state.get("next_room_id", 0) <= max_existing_room_id:
            print(f"Validation Warning: 'next_room_id' ({self._state.get('next_room_id')}) is not greater than the highest existing room ID ({max_existing_room_id}). Adjusting.")
            self._state["next_room_id"] = max_existing_room_id + 1
            needs_save = True

        # --- NEW: Validate Pet Theme Color State ---
        is_color_configured_val = self._state.get("is_color_configured")
        if not isinstance(is_color_configured_val, bool):
            print(f"Validation Warning: 'is_color_configured' missing or not boolean ({type(is_color_configured_val).__name__}). Setting to default (False).")
            self._state["is_color_configured"] = False
            needs_save = True

        pet_theme_color_val = self._state.get("pet_theme_color")
        is_valid_color_format = (
            isinstance(pet_theme_color_val, (list, tuple)) and
            len(pet_theme_color_val) == 3 and
            all(isinstance(c, (int, float)) for c in pet_theme_color_val)
        )
        if not is_valid_color_format:
            default_color = self._default_state.get("pet_theme_color", [100, 255, 100])
            print(f"Validation Warning: 'pet_theme_color' missing or invalid format ({pet_theme_color_val}). Setting to default {default_color}.")
            self._state["pet_theme_color"] = list(default_color)
            needs_save = True
        else:
            clamped_color = [
                max(0, min(255, int(c))) for c in pet_theme_color_val
            ]
            if clamped_color != pet_theme_color_val:
                print(f"Validation Warning: 'pet_theme_color' values ({pet_theme_color_val}) outside 0-255 range or not integers. Clamping to {clamped_color}.")
                self._state["pet_theme_color"] = clamped_color
                needs_save = True
        
        # New: Validate Sound State
        is_sound_configured_val = self._state.get("is_sound_configured")
        if not isinstance(is_sound_configured_val, bool):
            print(f"Validation Warning: 'is_sound_configured' missing or not boolean ({type(is_sound_configured_val).__name__}). Setting to default (False).")
            self._state["is_sound_configured"] = False
            needs_save = True

        pet_sound_val = self._state.get("pet_sound")
        if not isinstance(pet_sound_val, str):
            print(f"Validation Warning: 'pet_sound' missing or not string ({type(pet_sound_val).__name__}). Setting to default ('').")
            self._state["pet_sound"] = ""
            needs_save = True

        # --- NEW: Validate Steps State ---
        steps_value = self._state.get("steps")
        default_steps_value = 0

        if not isinstance(steps_value, int):
            print(f"Validation Warning: 'steps' missing or not an integer ({type(steps_value).__name__}). Setting to default ({default_steps_value}).")
            self._state["steps"] = default_steps_value
            needs_save = True
        elif steps_value < 0:
            print(f"Validation Warning: 'steps' value ({steps_value}) is negative. Resetting to default ({default_steps_value}).")
            self._state["steps"] = default_steps_value
            needs_save = True

        # --- NEW: Validate current_sim ID State ---
        id_value = self._state.get("id_value")
        default_id_value = ""

        if not isinstance(id_value, str):
            print(f"Validation Warning: 'id_value' missing or not an string ({type(id_value).__name__}). Setting to default ({default_id_value}).")
            self._state["id_value"] = default_id_value
            needs_save = True

        sim_current_step = self._state.get("sim_current_step")
        default_sim_current_step = 0
        if not isinstance(sim_current_step, int):
            print(f"Validation Warning: 'sim_current_step' missing or not an integer ({type(sim_current_step).__name__}). Setting to default ({default_sim_current_step}).")
            self._state["sim_current_step"] = default_sim_current_step
            needs_save = True
        elif sim_current_step < 0:
            print(f"Validation Warning: 'sim_current_step' value ({sim_current_step}) is negative. Resetting to default ({default_sim_current_step}).")
            self._state["sim_current_step"] = default_sim_current_step
            needs_save = True


        # -- new validate currency state --
        currency_value = self._state.get("currency")
        default_currency_value = 0

        if not isinstance(currency_value, (int, float)):
            print(f"Validation Warning: 'currency' missing or not a number ({type(currency_value).__name__}). Setting to default ({default_currency_value}).")
            self._state["currency"] = default_currency_value
            needs_save = True
        elif currency_value < 0:
            print(f"Validation Warning: 'currency' value ({currency_value}) is negative. Resetting to default ({default_currency_value}).")
            self._state["currency"] = default_currency_value
            needs_save = True

            
        if needs_save:
            print(f"Correcting state based on validation warnings for StateStore. Saving state.")
            self.save_state()