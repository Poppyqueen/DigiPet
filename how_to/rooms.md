# Game Rooms/Houses: What and How

House definitions are used the first time you initialize a new agent. These initial configurations are used to make the home of the agent and populate them with items. The system allows you to create these initial configurations for houses to create initial states for your agents.

The runtime goes like this:

We open an agent and check if it is a new agent. If it is, we will use its configured initial house and items state to instantiate the world. If we have an agent that has already been instantiated, we will ignore this initial configuration and load the unique saved state of its own world. So, homes are configurable only on the initialization of these agents. This is important to consider.

An Initial State is built from two parts: a base home design and a collection of items for this specific home design, both as separate JSON files.

The project includes two different states which you can use to guide your own designs: DevRoom and PrimeHouse and a respective configuration for each.

## What are Base Houses?

**Example:**
`inventory_items/base_state_manager/houses_data/prime_house.json`

This is a JSON list of 'rooms' dictionaries, these contain the following keys:

- **name:** a string, free to be whatever
- **image:** a string for the name of an image to use. Images should be included in the dir `style/images/` as a jpg, i.e., `image: lab_room` points to the file `lab_room.jpg`
- **room_types:** a list of types that gives tools or functions affordances to the agent
- **music:** mp3 files the same way as the image key, in `style/sounds/music/rooms/`, i.e., `white_room` points to `white_room.mp3`
- **descriptions:** this is a dictionary with the keys `late night`, `early morning`, `morning`, `noon`, `afternoon`, `late afternoon` and `night`. Each contains a list of strings that work as descriptions of the room at that specific time of the day
- **items:** this key needs to be initialized as an empty list for each room

## What are room configurations?

**Example:**
`inventory_items/base_state_manager/houses_configs/prime_house_config.json`

Each config is made with a Base House in mind. Here we specify the name of the items each of the rooms defined in a Base House will have. These item names are the names directly from our items store.

This is a singular JSON structure. It expects a key called `initial_room` as a string that defines the name for the room we will initialize in.

- **initial_room:** string with the name of the room to start in

Following, you need a key for each of the rooms in your Base House, and inside this key there is a list of the items we will use by name as they are in our ItemStore.


## How do they work?

This specific implementation is up to change, but for now to introduce new initial states, the process has been updated to be more dynamic and modular by loading configurations from a dedicated directory structure rather than modifying specific Python files.

### Configuration Loading

Initial state configurations are now loaded dynamically by recursively walking a configuration root directory. By default, this directory is:

`inventory_items/base_state_manager/configs`

### Introducing a New Initial State

To introduce a new initial state (e.g., `"my_new_state"`), follow these steps:

1.  **Create your Base House** file (`my_new_house.json`) and **Room Configuration** file (`my_new_house_config.json`) as described in the previous sections.
2.  **Create a New Configuration Map File** (or modify an existing one) within the `config_root_dir` (e.g., `inventory_items/base_state_manager/configs/my_ai_generated_states.json`).

3.  This JSON file must contain a dictionary where the keys are the initial state names, and the values are dictionaries specifying the paths to the base house and items configuration files:

    ```json
    {
        "my_new_state": {
            "b_house_path": "inventory_items/base_state_manager/houses_data/my_new_house.json",
            "items_config": "inventory_items/base_state_manager/houses_configs/my_new_house_config.json"
        }
    }
    ```

    *   All JSON files found in the configuration directory will be merged, making the new state name (`"my_new_state"`) automatically available for use during agent initialization.

### Item Configuration Flexibility (Update)

The item specification in the room configuration file (`houses_configs/*.json`) is now more flexible and can also include a key for the agent's starting **inventory**:

| Key | Description |
| :--- | :--- |
| **`initial_room`** | *string*. Name of the room to start in. |
| **`[Room Name]`** | *list of strings* or *string*. Specifies items for that room. Can be: <ul><li>A **list of item names** (e.g., `["bed_single", "desk"]`) which are looked up in the ItemStore.</li><li>A **string path** (e.g., `"inventory_items/item_sets/living_room.json"`) which is treated as a `__source_path__` filter to load all items defined in that specific file.</li></ul> |
| **`inventory`** | *list of strings* or *string* (Optional). Specifies items the agent starts with in their inventory. Follows the same list/path format as room items. |

**Item names** are the names of the items in the ItemStore, which can be found in `inventory_items/item_store.json`, append as a suffix to the name of the item the following pattern '[xN]', where x is an identifier flag which should always be present as 'x' and N is the number of items of that type to include as a stack. For example, if you want to include a stack of 3 apples in a room, you would write `"apple[x3]"`.

### Configuration Management Utility

The system includes methods to manage the configurations dynamically:

-   **`list_available_configs()`**: Returns a list of all state names loaded from the directory structure.
-   **`reload_configs()`**: Forces a complete reload of all configuration map files from the disk.
-   **`add_state_configuration(config_map, subdirectory="")`**: Programmatically adds a new configuration dictionary and saves it to a new JSON file within the specified (or default) config directory.