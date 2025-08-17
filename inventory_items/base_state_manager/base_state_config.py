from inventory_items.items_provider.item_store import ItemStore
import json

ITEM_ID_START_COUNTER = 0
ROOM_ID_START_COUNTER = 1

class InitialStateConst():
    def __init__(self):
        self.items_store = ItemStore("inventory_items/items_provider/items_data")

        # new config method, use a config file for both, like so
        self.states_configs = {
            "base_state": {
                "b_house_path": "inventory_items/base_state_manager/houses_data/prime_house.json",
                "items_config": "inventory_items/base_state_manager/houses_configs/prime_house_config.json"
            },
            "dev_room": {
                "b_house_path": "inventory_items/base_state_manager/houses_data/base_dev_room.json",
                "items_config": "inventory_items/base_state_manager/houses_configs/dev_room_config.json"
            }
        }
        
    def create_state(self, select_state):
        """
        Creates the complete initial game state based on a selected configuration.
        This includes populating rooms with items, setting the starting room,
        and adding all other necessary state data.
        """
        # Load the selected state's configuration from states_configs
        selected_config = self.states_configs.get(select_state)
        if not selected_config:
            raise ValueError(f"State configuration '{select_state}' not found.")

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