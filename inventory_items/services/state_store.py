# services/state_store.py
import json
import copy # For deep copying default state

# Assuming generic_json_tool.py is in utils, adjust import if different
try:
    from utils.generic_json_tool import GenericJsonTool
except ImportError:
    print("Error: generic_json_tool.py not found. Make sure it's in the same directory or PYTHONPATH.")
    import sys; sys.exit(1)

from inventory_items.items_validation.item_pydantic_models import (
    validate_item_dict,
    get_base_item_types,
    get_mcp_item_types)
from inventory_items.items_validation.room_pydantic_models import validate_room_dict
from inventory_items.services.connections_graph import ConnectionsGraph


import os

class StateStore(GenericJsonTool):
    ITEM_ID_START_COUNTER = 1
    ROOM_ID_START_COUNTER = 1

    def __init__(self, base_path, default_state, agent_config_path: str | None = None):
        self.json_filename = 'house_inventory_state_id.json'
        self._default_state = copy.deepcopy(default_state)

        # print(f"[StateStore] agent_config_path received: {agent_config_path}")
        # print(f"[StateStore] agent_config_path exists: {os.path.exists(agent_config_path) if agent_config_path else 'N/A'}")

        base = get_base_item_types()
        mcp  = get_mcp_item_types(config_path=agent_config_path) if agent_config_path else []
        
        # print(f"[StateStore] base types count: {len(base)}")
        # print(f"[StateStore] mcp types found: {mcp}")
        # print(f"[StateStore] total valid types: {len(base) + len(mcp)}")
        
        self._valid_types = set(base + mcp)

        json_path = os.path.join(str(base_path), self.json_filename)
        self._is_fresh_state = not os.path.exists(json_path)


        super().__init__(base_path)
        self._assign_missing_ids()
        self._post_init_state_validation()
        self._write_json(self._state)

        # Build the connections graph from the now-validated rooms list.
        # This must run after _assign_missing_ids and _post_init_state_validation
        # so every room is guaranteed to have a valid integer ID.
        self._connections_graph = ConnectionsGraph(
            self._state.get("rooms", [])
        )
 

 
    def get_connections_graph(self) -> ConnectionsGraph:
        """Returns the pre-built movement graph. Used by RoomManager."""
        return self._connections_graph
 
 
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

    # def _is_item_valid_for_this_agent(self, item: dict, check_id: bool) -> tuple[bool, str | None]:
    #     item_types = item.get("type", [])
    #     unknown_types = [t for t in item_types if t not in self._valid_types]
    #     if unknown_types:
    #         return False, f"Item has types {unknown_types} not valid for this agent."
    #     return validate_item_dict(item, check_id=check_id)

    def _is_item_valid_for_this_agent(self, item: dict, check_id: bool) -> tuple[bool, str | None]:
        item_types = item.get("type", [])
        if item_types is None:
            item_types = []

        # print(f"[DEBUG] _is_item_valid_for_this_agent: "
        #     f"name={item.get('name', '?')!r}, id={item.get('id', '?')!r}, "
        #     f"raw_type={item.get('type', '<missing>')!r}, "
        #     f"resolved_type={item_types!r}")

        if not isinstance(item_types, list):
            print(f"[DEBUG] item_types is not a list (got {type(item_types).__name__}); "
                f"coercing to list for safety.")
            item_types = [item_types] if item_types else []

        item["type"] = item_types  


        unknown_types = [t for t in item_types if t not in self._valid_types]

        if unknown_types:
            print(f"[DEBUG] Unknown types for item {item.get('name', '?')!r}: {unknown_types} "
                f"(valid_types has {len(self._valid_types)} entries, fresh_state={self._is_fresh_state})")
            if self._is_fresh_state:
                return False, f"Item has unknown types {unknown_types} — cannot create."
            else:
                print(f"Info: Item '{item.get('name', '?')}' has unrecognized types {unknown_types}. "
                    f"Keeping (types may belong to a disconnected MCP server).")
                return True, None

        result, error = validate_item_dict(item, check_id=check_id)
        if result is None:
            print(f"[DEBUG] validate_item_dict failed for item {item.get('name', '?')!r}: {error}")
        return result, error

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

        for room in self._state.get("rooms", []):
            if not isinstance(room, dict):
                print(f"Validation Warning: Found non-dict entry in rooms list: {room}. Removing.")
                needs_save = True
                continue

            # Duplicate ID check must happen before validate_room_dict since
            # uniqueness is a state-level constraint, not a per-room one.
            room_id = room.get("id")
            if isinstance(room_id, int) and room_id in room_ids_seen:
                print(f"Validation Warning: Duplicate room ID {room_id}. Removing this instance.")
                needs_save = True
                continue

            # Validate room structure and type-specific contracts via pydantic.
            result, error = validate_room_dict(room, check_id=True)
            if result is None:
                print(f"Validation Warning: Room (ID:{room.get('id', 'unknown')}) failed validation — {error}.")
                needs_save = True
                continue

            # Validate items inside the room — unchanged from before.
            original_item_count = len(room.get("items", []))
            valid_room_items = []
            for item in room.get("items", []):
                item_valid, item_error = self._is_item_valid_for_this_agent(item, check_id=True)
                if not item_valid:
                    print(f"Validation Warning: Item in room ID {room_id} — {item_error}.")
                    needs_save = True
                    continue
                valid_room_items.append(item)
            room["items"] = valid_room_items
            if len(room["items"]) < original_item_count:
                needs_save = True

            room_ids_seen.add(room_id)
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
                item_valid, error = self._is_item_valid_for_this_agent(item, check_id=True)
                if not item_valid:
                    print(f"... {error}. Removing.")
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