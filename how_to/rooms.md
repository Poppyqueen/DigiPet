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

This specific implementation is up to change, but for now to introduce new initial states, after you create your configuration and base house files, go into `inventory_items/base_state_manager/base_state_config.py`

Here we can change `self.states_configs` which maps a name for your initial state and the two files:

```python
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
```

Here you have to add your mapping.

`inventory_items/inventory_manager.py` also needs changes. For `available_states` you have to add the name you just created in this `states_config`:

```python
available_states = [
    "base_state",
    "dev_room",
    "my_new_state"  # add it here
]
```

**Note:** One has to change the GUI code to add this to the interface for now. We will have to update this involved process, but if you don't need it on the GUI it will be enough to do the steps above for it to be a valid configuration.