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
        Derive the ordered, deduplicated list of room names declared by a layout file.

        Every room that exists in the house is named in one of two places:
          - groups:      { group_name: [room_name, ...] }
          - connections: [[roomA, roomB], ...]

        When an aliases map is present, groups and connections are authored using
        alias names — this method returns those alias names as-is. Resolution against
        the RoomStore (using the store_name side of the alias) happens in create_state.

        The returned order is: group members first (in declaration order), then any
        connectoid names that appear only in connections, also in declaration order.
        This is stable and deterministic across runs.
        """
        seen = {}  # name -> first-seen index, for stable dedup

        groups = layout.get("groups", {})
        for members in groups.values():
            for name in members:
                if name not in seen:
                    seen[name] = len(seen)

        for edge in layout.get("connections", []):
            for name in edge:
                if name not in seen:
                    seen[name] = len(seen)

        return sorted(seen, key=lambda n: seen[n])

    def _apply_layout_config(self, rooms: list, layout_config_path: str) -> list:
        """
        Applies movement group and connectoid connection data from a layout config
        file onto the room list.

        Layout config format:
        {
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
        - Rooms not mentioned in either get movement_group="default".
        - Connections are always bidirectional.
        - Warns on any name in the layout that has no matching room in the house.
        """
        with open(layout_config_path, 'r') as f:
            layout = json.load(f)

        groups = layout.get("groups", {})
        edges = layout.get("connections", [])

        room_by_name = {room["name"]: room for room in rooms}

        for group_name, members in groups.items():
            for name in members:
                if name not in room_by_name:
                    print(f"Layout warning: '{name}' in group '{group_name}' has no matching room.")

        adjacency = {}
        for edge in edges:
            if len(edge) != 2:
                print(f"Layout warning: skipping malformed edge {edge}")
                continue
            a, b = edge
            for name in (a, b):
                if name not in room_by_name:
                    print(f"Layout warning: '{name}' in connections has no matching room.")
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
                if name in room_by_name:
                    room = room_by_name[name]
                    room["movement_group"] = group_name
                    room["is_connectoid"] = False
                    room["connections"] = None

        for name in connectoid_names:
            if name in room_by_name:
                room = room_by_name[name]
                room["is_connectoid"] = True
                room["movement_group"] = None
                room["connections"] = adjacency[name]

        mentioned = group_members | connectoid_names
        for room in rooms:
            if room["name"] not in mentioned:
                room["movement_group"] = "default"
                room["is_connectoid"] = False
                room["connections"] = None

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
                f"groups or connections."
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