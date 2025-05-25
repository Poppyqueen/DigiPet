# Game Room Creation Guide

To create a new room, you'll define its structure as a dictionary within the `items_init.py` file. This file manages initial game state configurations, including `base_state` and `custom_state`, which hold lists of rooms.

You can either add your new room dictionary to an existing state dictionary's `"rooms"` list or create an entirely new state dictionary.

---

## Room Dictionary Structure

A room dictionary requires several key pieces of information:

*   `name`: A unique string identifier for the room, used for context.
*   `id`: **Only necessary for the very first room the agent starts in (must be `0`).** All other rooms do not need an `id` defined in `items_init.py` as their IDs will be automatically populated. The `"current_room_id"` in the state dictionary must match the ID of the desired starting room (`0`).
*   `image`: The filename (without extension) of the room's background image. Located in `style/images/` (JPG assumed).
*   `room_types`: A list of strings (e.g., `'lab'`, `'social'`, `'kitchen'`). These are **critical** as they dictate available tools via `tools_builder/construct_tools.py`.
*   `music`: The filename (without extension) of the background music (MP3) looping in this room. Located in `style/sounds/music/rooms/`.
*   `descriptions`: A dictionary containing time-of-day specific descriptions.
*   `items`: A list of dictionaries, each representing an item in the room.

### Detailed Property Breakdown

#### `name`
A unique string identifier for the room, used for context.

#### `id`
This is **only necessary for the very first room** the agent starts in, which **must** have an `id` of `0`. All other rooms do not need an `id` defined in `items_init.py` as their IDs will be automatically populated by the game's initialization script. The `"current_room_id"` in the state dictionary must match the ID of the desired starting room (which will be `0`).

#### `image`
The filename (without the extension) of the room's background image. This image file should be located in the `style/images/` folder (assuming JPG format).

#### `room_types`
A list of strings that categorize the room's nature (e.g., `'lab'`, `'social'`, `'kitchen'`, `'library'`). These types are **critical** because they dictate the tools (functions) available in that room. The `tools_builder/construct_tools.py` module uses these types to add relevant tools to the room. For example, a `'bedroom'` type might provide access to `'sleep'` and `'hug_pillow'` tools.

#### `music`
The filename (without the extension) of the background music track that will loop in this room. The game looks for an MP3 file in the `style/sounds/music/rooms/` folder.

#### `descriptions`
A dictionary containing time-of-day specific descriptions for the room. This dictionary **must** include keys for all seven time slots: `'late night'`, `'early morning'`, `'morning'`, `'noon'`, `'afternoon'`, `'late afternoon'`, and `'night'`. Each time slot key maps to a list of one to two distinct descriptive strings. These descriptions should convey the mood, lighting, activity level, and general atmosphere, focusing on sensory details and brevity. They should also be consistent with the room's concept and across different time slots. You can create these descriptions manually or use the AI helper tool `data_constructors/room_generator.py`.

#### `items`
A list of dictionaries, with each dictionary representing an item present in the room. This list can be empty initially. Items have their own structure, including:
*   `name`: A unique string identifier.
*   `descriptions`: A list of strings.
*   `static`: A boolean (e.g., `True` for furniture).
*   `type`: (e.g., `"furniture"`, `"tool"`, `"consumable"`, `"book"`).
    *   **Consumable items** include a `stats_edit` dictionary (for effects on fullness, hydration, energy) and an `effects` list.
    *   **Book items** include a `chapters` list, where each chapter is a dictionary with a `title` and `content`.

---

## Workflow Summary

Here's a summarized workflow for creating new game rooms:

1.  **Generate Room Descriptions with AI Helper:**
    *   Navigate to the `data_constructors/room_generator.py` script.
    *   Edit the `room_configs` list within this script. For each new room, add a dictionary specifying its concept (for AI description generation), `name`, `image`, `types`, and `music`.
    *   Run the script:
        ```bash
        python room_generator.py
        ```
        This will generate detailed, time-of-day specific descriptions and output the complete room structure into a `room_data.json` file.
    *   **Review:** **Always review** the generated data in `room_data.json` for accuracy and tone. Make any necessary manual adjustments there.

2.  **Integrate into Game State (`items_init.py`):**
    *   Open the `items_init.py` file.
    *   Choose an existing state dictionary (like `base_state`) or create a new one.
    *   Copy the generated room dictionary (or dictionaries) from `room_data.json`.
    *   Paste this room dictionary into the `"rooms"` list within the chosen state dictionary in `items_init.py`.

3.  **Configure Room ID and Starting Room:**
    *   **Crucially**, only set the `id` to `0` for the intended starting room. **Do not** include an `id` key for any other rooms; their IDs will be automatically assigned by the game's initialization script.
    *   If your new room (the one with `id: 0`) is intended to be the starting room, ensure the `"current_room_id"` in the state dictionary is set to `0`.

4.  **Populate with Items (Manual Step):**
    *   Within your newly added room dictionary in `items_init.py`, manually populate the `"items"` list with dictionaries representing the items present in that room. Even if `room_generator.py` initializes `items: []`, this is where you'd add the specific item data (`name`, `descriptions`, `static`, `type`, etc.).

5.  **Finalize Game State (if creating a new top-level state):**
    *   If you created a new top-level state dictionary, you'll also need to modify the `InventoryHouseManager` initialization in `inventory_house_manager.py` to set `self._default_state` to your new state.



## Crucial

For now the system does not have a method to load newly created rooms into already existing agents or worlds. If you create a new room, one will have to start a whole new run for this to be added. This is an area of improvement, so we can add new rooms into existing runs.