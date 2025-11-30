import json
import os
from pathlib import Path

from ..items_provider.item_store import ItemStore


ITEM_ID_START_COUNTER = 0
ROOM_ID_START_COUNTER = 1

class InitialStateConst():
    def __init__(self, config_root_dir="inventory_items/base_state_manager/configs"):
        self.items_store = ItemStore("inventory_items/items_provider/items_data")
        self.config_root_dir = config_root_dir
        # new config method, use directory walking to find all config files
        self.states_configs = self._load_states_map()

    def _load_states_map(self) -> dict:
        """
        Walk through the config root directory and load all JSON config map files.
        Each JSON file should contain a dictionary of state configurations in the same format
        as the original state_configs_map.json
        """
        all_configs = {}
        
        if not os.path.exists(self.config_root_dir):
            print(f"Config directory '{self.config_root_dir}' not found. Creating it...")
            os.makedirs(self.config_root_dir, exist_ok=True)
            return all_configs

        try:
            # Walk through the directory tree
            for root, dirs, files in os.walk(self.config_root_dir):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r') as f:
                                config_data = json.load(f)
                            
                            # Merge the configurations from this file into all_configs
                            # This maintains the same structure as your original single JSON file
                            if isinstance(config_data, dict):
                                all_configs.update(config_data)
                                #print(f"Loaded {len(config_data)} configs from {file_path}")
                            else:
                                print(f"Warning: {file_path} does not contain a dictionary at root level")
                                
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"Error loading config from {file_path}: {e}")
                            continue
                            
        except Exception as e:
            print(f"Error walking config directory: {e}")
            
        return all_configs

    def reload_configs(self):
        """
        Reload all configurations from the directory structure.
        Useful if configs have been added/modified externally.
        """
        self.states_configs = self._load_states_map()
        print(f"Reloaded {len(self.states_configs)} configurations")

    def add_state_configuration(self, config_map: dict, subdirectory: str = ""):
        """
        Adds state configurations by saving them to a JSON file in the config directory
        and updates self.states_configs. Maintains the same interface as the original method.
        
        Args:
            config_map: Dictionary of configurations to add (same format as original)
            subdirectory: Optional subdirectory within the config root to save the file
                        (e.g., "local_ai_gens" will save to config_root_dir/local_ai_gens/)
        """
        if not isinstance(config_map, dict):
            raise ValueError("Configuration must be a dictionary.")

        # Load existing configurations to avoid overwriting
        current_configs = dict(self.states_configs)
        
        # Add the new configurations
        current_configs.update(config_map)

        # Determine the target directory
        if subdirectory:
            target_dir = os.path.join(self.config_root_dir, subdirectory)
        else:
            target_dir = self.config_root_dir

        # Save to a new JSON file (you can customize the filename)
        import time
        timestamp = int(time.time())
        config_file_path = os.path.join(target_dir, f"added_configs_{timestamp}.json")
        
        # Ensure the target directory exists
        os.makedirs(target_dir, exist_ok=True)

        try:
            # Save only the new configurations to the file
            with open(config_file_path, 'w') as f:
                json.dump(config_map, f, indent=4)

            # Update the in-memory state
            self.states_configs.update(config_map)
            print(f"Added {len(config_map)} configurations to {config_file_path}")
            
        except Exception as e:
            print(f"Error saving configurations: {e}")
            raise

    def remove_state_configuration(self, config_name: str):
        """
        Remove a state configuration by deleting its JSON file and updating self.states_configs
        """
        if config_name not in self.states_configs:
            raise ValueError(f"Configuration '{config_name}' not found.")

        config_file_path = os.path.join(self.config_root_dir, f"{config_name}.json")
        
        try:
            if os.path.exists(config_file_path):
                os.remove(config_file_path)
            
            # Remove from in-memory state
            del self.states_configs[config_name]
            print(f"Removed configuration '{config_name}'")
            
        except Exception as e:
            print(f"Error removing configuration '{config_name}': {e}")
            raise

    def list_available_configs(self):
        """
        Return a list of all available configuration names
        """
        return list(self.states_configs.keys())

    def create_state(self, select_state):
        """
        Creates the complete initial game state based on a selected configuration.
        This includes populating rooms with items, setting the starting room,
        and adding all other necessary state data.
        """
        # Load the selected state's configuration from states_configs
        selected_config = self.states_configs.get(select_state)
        if not selected_config:
            available_configs = self.list_available_configs()
            raise ValueError(f"State configuration '{select_state}' not found. Available configs: {available_configs}")

        base_house_path = selected_config["b_house_path"]
        items_config_path = selected_config["items_config"]

        # Load the base room data from the provided JSON file
        with open(base_house_path, 'r') as f:
            base_rooms_data = json.load(f)

        # Load the items configuration data
        with open(items_config_path, 'r') as f:
            items_config = json.load(f)

        # Separate the initial room to ensure it's at the start of the list
        initial_room_name = items_config.get("initial_room")
        if not initial_room_name:
            raise ValueError("Configuration must specify an 'initial_room'.")

        initial_room_dict = None
        other_rooms = []

        for room in base_rooms_data:
            if room["name"] == initial_room_name:
                initial_room_dict = room
            else:
                other_rooms.append(room)

        if initial_room_dict is None:
            raise ValueError(f"Initial room '{initial_room_name}' not found in the base house data.")

        # Assign an 'id' of 0 only to the initial room
        initial_room_dict["id"] = 0
        final_rooms_list = [initial_room_dict]

        # The other rooms are added to the list without an 'id' key
        final_rooms_list.extend(other_rooms)
        
        # Populate the 'items' list for each room using the new items_config map
        for room in final_rooms_list:
            item_config_for_room = items_config.get(room["name"])

            if isinstance(item_config_for_room, str):  # Check if it's a path
                filters = {'__source_path__': item_config_for_room}
                room["items"] = self.items_store.find_items(filters)
            elif isinstance(item_config_for_room, list):  # Check if it's a list of names
                items_dict = self.items_store.get_item(item_config_for_room)
                room["items"] = list(items_dict.values())
            else:
                # If no items are configured or format is wrong, it remains an empty list
                room["items"] = []

        # Handle inventory population based on config type (path or list)
        inventory_items = []
        inventory_config = items_config.get("inventory", [])  # Default to empty list

        if isinstance(inventory_config, str):  # Check if it's a path
            filters = {'__source_path__': inventory_config}
            inventory_items = self.items_store.find_items(filters)
        elif isinstance(inventory_config, list) and inventory_config:  # Check if it's a non-empty list
            items_dict = self.items_store.get_item(inventory_config)
            inventory_items = list(items_dict.values())

        # Assemble the final, complete state dictionary
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
            "is_color_configured": False,
            "pet_theme_color": [100, 255, 100],
            "steps": 0
        }

        return initial_state
