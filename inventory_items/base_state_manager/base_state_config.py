from inventory_items.items_provider.item_store import ItemStore
from inventory_items.rooms_provider.room_store import RoomStore
import json
import os
from pathlib import Path

ITEM_ID_START_COUNTER = 0
ROOM_ID_START_COUNTER = 1


class InitialStateConst():
    def __init__(
        self,
        config_root_dir="inventory_items/base_state_manager/configs",
        rooms_root_dir="inventory_items/rooms_provider/rooms_data",
    ):
        self.items_store = ItemStore("inventory_items/items_provider/items_data")
        self.rooms_store = RoomStore(rooms_root_dir)
        self.config_root_dir = config_root_dir
        self.states_configs = self._load_states_map()

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_states_map(self) -> dict:
        """
        Load the single JSON config map file that defines available states.
        """
        config_file_path = os.path.join(self.config_root_dir, "state_configs_map.json")

        if not os.path.exists(config_file_path):
            print(f"Config file '{config_file_path}' not found. Creating an empty one...")
            os.makedirs(self.config_root_dir, exist_ok=True)
            with open(config_file_path, 'w') as f:
                json.dump({}, f, indent=4)
            return {}

        try:
            with open(config_file_path, 'r') as f:
                config_data = json.load(f)
            if not isinstance(config_data, dict):
                print(f"Warning: {config_file_path} does not contain a dictionary at root level")
                return {}
            return config_data
        except json.JSONDecodeError as e:
            print(f"Error loading config from {config_file_path}: {e}")
            return {}

    def reload_configs(self):
        self.states_configs = self._load_states_map()
        print(f"Reloaded {len(self.states_configs)} configurations")

    def add_state_configuration(self, config_map: dict, subdirectory: str = ""):
        if not isinstance(config_map, dict):
            raise ValueError("Configuration must be a dictionary.")

        current_configs = dict(self.states_configs)
        current_configs.update(config_map)

        if subdirectory:
            target_dir = os.path.join(self.config_root_dir, subdirectory)
        else:
            target_dir = self.config_root_dir

        import time
        timestamp = int(time.time())
        config_file_path = os.path.join(target_dir, f"added_configs_{timestamp}.json")
        os.makedirs(target_dir, exist_ok=True)

        try:
            with open(config_file_path, 'w') as f:
                json.dump(config_map, f, indent=4)
            self.states_configs.update(config_map)
            print(f"Added {len(config_map)} configurations to {config_file_path}")
        except Exception as e:
            print(f"Error saving configurations: {e}")
            raise

    def remove_state_configuration(self, config_name: str):
        if config_name not in self.states_configs:
            raise ValueError(f"Configuration '{config_name}' not found.")

        config_file_path = os.path.join(self.config_root_dir, f"{config_name}.json")
        try:
            if os.path.exists(config_file_path):
                os.remove(config_file_path)
            del self.states_configs[config_name]
            print(f"Removed configuration '{config_name}'")
        except Exception as e:
            print(f"Error removing configuration '{config_name}': {e}")
            raise

    def list_available_configs(self):
        return list(self.states_configs.keys())

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _extract_room_names_from_layout(self, layout: dict) -> list[str]:
        """
        Returns the ordered, deduplicated list of room names declared by a layout file's
        explicit "rooms" roster, after validating it against "groups" and "connections".

        The "rooms" key is the single source of truth for which rooms exist in the Scene:
            "rooms": ["Room 101", "Room 101 Kitchenette", "Hallway 001", ...]

        "groups" and "connections" describe pathing only — every name they reference must
        already be declared in "rooms", and every name in "rooms" must appear in at least
        one of them. Both directions are enforced here, as hard failures:

          - A name in "groups" or "connections" that isn't in "rooms" raises immediately
            (catches typos and rooms that were wired up but never declared).
          - A name in "rooms" that never appears in "groups" or "connections" raises
            immediately (catches rooms that were declared but never wired up — they'd
            otherwise be silently unreachable).

        When an aliases map is present, "rooms", "groups", and "connections" are all
        authored using alias names — this method returns those alias names as-is.
        Resolution against the RoomStore (using the store_name side of the alias) happens
        in create_state.
        """
        rooms_roster = layout.get("rooms")
        if rooms_roster is None:
            raise ValueError(
                "Layout file must declare a 'rooms' key: the explicit list of every room "
                "name in this Scene. 'groups' and 'connections' only describe pathing "
                "between rooms already listed here."
            )
        if not isinstance(rooms_roster, list):
            raise ValueError("Layout 'rooms' key must be a list of room names.")

        seen = {}  # name -> first-seen index, for stable dedup
        for name in rooms_roster:
            if name not in seen:
                seen[name] = len(seen)
            else:
                print(f"Layout warning: '{name}' is listed more than once in 'rooms'.")

        roster = set(seen.keys())
        referenced = set()

        groups = layout.get("groups", {})
        for group_name, members in groups.items():
            for name in members:
                referenced.add(name)
                if name not in roster:
                    raise ValueError(
                        f"Layout error: '{name}' in group '{group_name}' is not declared "
                        f"in 'rooms'. Add it to 'rooms' or fix the name."
                    )

        for edge in layout.get("connections", []):
            if len(edge) != 2:
                raise ValueError(f"Layout error: malformed connection edge {edge!r}, expected [roomA, roomB].")
            for name in edge:
                referenced.add(name)
                if name not in roster:
                    raise ValueError(
                        f"Layout error: '{name}' in connections is not declared in "
                        f"'rooms'. Add it to 'rooms' or fix the name."
                    )

        unreferenced = roster - referenced
        if unreferenced:
            raise ValueError(
                f"Layout error: room(s) declared in 'rooms' but never used in 'groups' or "
                f"'connections', so they would be unreachable: {sorted(unreferenced)}."
            )

        return list(seen.keys())

    def _apply_layout_config(self, rooms: list, layout_config_path: str) -> list:
        """
        Applies movement group and connectoid connection data from a layout config
        file onto the room list.

        Layout config format:
        {
            "rooms": ["room_name", ...],
            "groups": {
                "group_name": ["room_name", ...]
            },
            "connections": [
                ["RoomOrConnectoidA", "RoomOrConnectoidB"],
                ...
            ]
        }

        Rules:
        - Rooms listed in "groups" receive movement_group, is_connectoid=False, connections=null.
        - Rooms that appear in "connections" edges but not in any group are connectoids:
          is_connectoid=True, movement_group=null, connections=[all their neighbours].
        - Connections are always bidirectional.

        By the time this runs, `rooms` is guaranteed (by _extract_room_names_from_layout
        and create_state's RoomStore resolution) to contain exactly the layout's "rooms"
        roster, and every name in "groups"/"connections" is guaranteed to be a member of
        that roster. So every room here ends up with either a movement_group or a
        connectoid connections list — there is no "unmentioned room" case left to handle.
        """
        with open(layout_config_path, 'r') as f:
            layout = json.load(f)

        groups = layout.get("groups", {})
        edges = layout.get("connections", [])

        room_by_name = {room["name"]: room for room in rooms}

        adjacency = {}
        for a, b in edges:
            adjacency.setdefault(a, [])
            adjacency.setdefault(b, [])
            if b not in adjacency[a]:
                adjacency[a].append(b)
            if a not in adjacency[b]:
                adjacency[b].append(a)

        group_members = {name for members in groups.values() for name in members}
        connectoid_names = {name for name in adjacency if name not in group_members}

        for group_name, members in groups.items():
            for name in members:
                room = room_by_name[name]
                room["movement_group"] = group_name
                room["is_connectoid"] = False
                room["connections"] = None

        for name in connectoid_names:
            room = room_by_name[name]
            room["is_connectoid"] = True
            room["movement_group"] = None
            room["connections"] = adjacency[name]

        return rooms

    # ------------------------------------------------------------------
    # State creation
    # ------------------------------------------------------------------

    def create_state(self, select_state):
        """
        Creates the complete initial game state based on a selected configuration.

        Config format (b_house_path is gone — the layout file is the manifest):
        {
            "items_config":  "path/to/items_config.json",
            "layout_config": "path/to/layout.json"
        }

        The layout file must declare a "rooms" roster; see _extract_room_names_from_layout
        for the validation rules enforced against it.
        """
        selected_config = self.states_configs.get(select_state)
        if not selected_config:
            available_configs = self.list_available_configs()
            raise ValueError(
                f"State configuration '{select_state}' not found. "
                f"Available configs: {available_configs}"
            )

        items_config_path = selected_config["items_config"]
        layout_config_path = selected_config["layout_config"]

        # Load items config
        with open(items_config_path, 'r') as f:
            items_config = json.load(f)

        # Load layout — source of truth for room manifest, topology, and starting room
        with open(layout_config_path, 'r') as f:
            layout = json.load(f)

        initial_room_name = layout.get("initial_room")
        if not initial_room_name:
            raise ValueError(
                f"Layout file '{layout_config_path}' must specify an 'initial_room'."
            )

        room_names = self._extract_room_names_from_layout(layout)

        if initial_room_name not in room_names:
            raise ValueError(
                f"initial_room '{initial_room_name}' is not declared in the layout's "
                f"'rooms' roster."
            )

        # aliases in the layout are authored as { store_name: alias_name }
        # We need the reverse to go from alias_name -> store_name during resolution
        aliases: dict[str, str] = layout.get("aliases", {})
        alias_to_store: dict[str, str] = {v: k for k, v in aliases.items()}

        # Resolve each layout name through the RoomStore, applying aliases where needed
        resolved_rooms = []
        missing = []
        for alias_name in room_names:
            store_name = alias_to_store.get(alias_name, alias_name)
            room = self.rooms_store.get_room(store_name)
            if room is None:
                missing.append(f"'{alias_name}' (store name: '{store_name}')" if alias_name != store_name else f"'{alias_name}'")
            else:
                # Rename the room to the alias so the engine only ever sees the alias
                room["name"] = alias_name
                resolved_rooms.append(room)

        if missing:
            raise ValueError(
                f"Layout references rooms not found in RoomStore: {missing}"
            )

        # Move initial room to index 0 and assign id=0
        initial_idx = next(i for i, r in enumerate(resolved_rooms) if r["name"] == initial_room_name)
        initial_room = resolved_rooms.pop(initial_idx)
        initial_room["id"] = 0
        final_rooms_list = [initial_room] + resolved_rooms

        # Apply movement groups and connectoid connections from the layout
        final_rooms_list = self._apply_layout_config(final_rooms_list, layout_config_path)

        # Populate items for each room
        for room in final_rooms_list:
            item_config_for_room = items_config.get(room["name"])

            if isinstance(item_config_for_room, str):
                filters = {'__source_path__': item_config_for_room}
                room["items"] = self.items_store.find_items(filters)
            elif isinstance(item_config_for_room, list):
                items_dict = self.items_store.get_item(item_config_for_room)
                room["items"] = list(items_dict.values())
            else:
                room["items"] = []

        # Populate inventory
        inventory_items = []
        inventory_config = items_config.get("inventory", [])

        if isinstance(inventory_config, str):
            filters = {'__source_path__': inventory_config}
            inventory_items = self.items_store.find_items(filters)
        elif isinstance(inventory_config, list) and inventory_config:
            items_dict = self.items_store.get_item(inventory_config)
            inventory_items = list(items_dict.values())

        # Assemble final state
        initial_state = {
            "next_item_id": ITEM_ID_START_COUNTER,
            "next_room_id": ROOM_ID_START_COUNTER,
            "current_room_id": 0,
            "rooms": final_rooms_list,
            "inventory": inventory_items,
            "current_emote": "neutral",
            "possible_emotes": {
                "neutral": "You're feeling calm and attentive.",
                "happy": "You're feeling cheerful and optimistic.",
                "sad": "You're feeling down.",
                "confused": "You're unsure or puzzled.",
                "excited": "You're enthusiastic and eager.",
                "thinking": "You're processing information or contemplating.",
                "angry": "You're feeling frustrated or upset."
            },
            "stats": {
                "fullness": 200.0,
                "hydration": 200.0,
                "energy": 200.0
            },
            "steps": 0
        }

        return initial_state