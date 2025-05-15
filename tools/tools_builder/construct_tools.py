# construct_tools.py
# This file is responsible for constructing the tools and their definitions for an AI agent.
# It imports necessary components from other files and defines the FunctionBuilder class.
# It includes methods to construct function mappings and tool definitions based on the current room's *types*.
# It also includes a method to call functions dynamically based on the current room and function name.
# It includes examples on room and item specific functions.

# Notes:
# The tool definitions are JSON structures, the names and order of arguments are important and need to
# be consistent with the functions in the tools folder. This is a crucial part of the design of new tools.

# All tools end up here one way or another, if initialized from another module or imported directly for use
# all tools are included here and then passed to the AI agent


# Import necessary components from library_tools.py (and potentially other files)
# from tools_folder.functions_local import (
#     get_weather,      # Import the global functions
#     get_time,
#     send_email
# )

# Import tools and their definitions from the tools folder
# Here we can import tools that don't need to interact inside the AI agent itself or the CLI, so we can construct them directly here
from datetime import datetime
# Import the tool definitions lists
# We still need to import these lists, but they will be organized differently below
from .my_tools import (
    base_tools,
    library_tools,
    book_tools,
    white_room_tools,
    living_room_tools,
    bedroom_tools,
    bathroom_tools,
    computer_room_tools,
    garden_room_tools,
    kitchen_room_tools
)

from utils import open_meteo_handle

# Import tools
# We import the tool handlers/classes here
from tools.tools_folder.bluesky_handle import bluesky_bot
from tools.tools_folder.rooms_tools import main_tools_handle

class FunctionBuilder:
    def __init__(self, state_manager=None, signal=None):
        self._signal_callback = signal
        self.state_manager = state_manager
        self.room_tools = main_tools_handle(self.state_manager, self._signal_callback)

        # --- Central Mapping of Room Types to Functions and Definitions ---
        # This dictionary holds the functions and tool definitions associated with each room type.
        # Keys are room type strings (e.g., "library", "bedroom").
        # Values are dictionaries with keys "functions" (dict of function name -> callable)
        # and "definitions" (list of tool definition dicts).
        self._room_type_data = {
            "library": {
                "functions": {
                    "create_book_item": self.state_manager.create_book_item
                    # Add other specific library functions here if they existed
                    # e.g., "save_note": self.local_library.save_note,
                },
                "definitions": library_tools # Use the imported definition list
            },
            "bedroom": {
                "functions": {
                    "sleep": self.room_tools.bedroom.sleep,
                    "hug_pillow": self.room_tools.bedroom.hug_pillow,
                    "look_under_bed": self.room_tools.bedroom.look_under_bed
                },
                "definitions": bedroom_tools
            },
            "living_room": {
                "functions": {
                    "watch_tv": self.room_tools.living_room.watch_tv,
                    "look_at_window": self.room_tools.living_room.look_at_window,
                    "sit_on_couch": self.room_tools.living_room.sit_on_couch
                },
                "definitions": living_room_tools
            },
             "bathroom": {
                "functions": {
                    "drink_water": self.room_tools.bathroom.drink_water,
                    "wash_hands": self.room_tools.bathroom.wash_hands
                },
                "definitions": bathroom_tools
            },
             "computer_room": {
                "functions": {
                     "random_wikipedia": self.room_tools.computer.random_wikipedia
                },
                "definitions": computer_room_tools
            },
             "garden": {
                "functions": {
                     "dig_hole": self.room_tools.garden.dig_hole,
                     "lay_down": self.room_tools.garden.lay_down
                },
                "definitions": garden_room_tools
            },
             "white_room": {
                "functions": {
                     "meditate": self.room_tools.white_room.meditate
                     # e.g., "create_room": self.room_handler.create_room # If this was type-specific
                },
                "definitions": white_room_tools
            },
            "kitchen": {
                "functions": {
                    "prepare_food": self.room_tools.kitchen.prepare_food
                },
                "definitions": kitchen_room_tools
            }
            # Add entries for other room types as needed
        }
        # --- End Central Mapping ---


        # Create the mapping dictionary for base functions (always available)
        # These functions are independent of room type or inventory.
        self.base_function_map = {
            # Global functions (if you uncommented them)
            # "get_weather": get_weather,
            # "get_time": get_time,
            # "send_email": send_email,

            # State Manager base functions
            "get_items_in_current_room": self.state_manager.get_items_in_current_room,
            "set_current_emote": self.state_manager.set_current_emote,
            "move_to_room": self.state_manager.set_current_room,
            "get_all_rooms": self.state_manager.get_all_rooms,
            "examine_item": self.state_manager.get_item_details,
            "pickup_item": self.state_manager.pickup_item,
            "drop_item": self.state_manager.drop_item,
            "consume_item": self.state_manager.consume_item,
            "trash_item": self.state_manager.trash_item,
            "add_item_description": self.state_manager.add_item_description,

            # Other base functions (if needed)
            # "post_bluesky": self.blsky.post_bluesky, # Example of another base service
        }

        # Item-specific functions (like books), defined separately as they depend on inventory
        self._item_specific_functions = {
            "book": { # Key can be an item type or identifier
                 "list_chapters": self.state_manager.list_book_chapters,
                 "add_chapter": self.state_manager.add_book_chapter,
                 "read_chapter": self.state_manager.read_book_chapter,
                 "delete_chapter": self.state_manager.delete_book_chapter,
                 "update_chapter": self.state_manager.update_book_chapter
                 # Add other item-specific functions here
                 # e.g., "add_possible_emote": self.emote_manager.add_possible_emote # for "mirror"
            }
        }

        # Item-specific tool definitions, defined separately
        self._item_specific_definitions = {
             "book": book_tools # Use the imported definition list
             # Add other item definition lists here
             # e.g., "mirror": mirror_tools # Use the imported definition list
        }

        # self.function_map will be constructed dynamically by construct_map
        self.function_map = {} # Initialize as empty; filled by construct_map


    def get_current_room_types(self):
        """Retrieves the list of types for the current room."""
        current_id = self.state_manager.get_current_room_id()
        room = self.state_manager._find_room_by_id(current_id) # Assuming _find_room_by_id is accessible or use a public getter
        if room and "room_types" in room:
            print(f"DEBUG: Current room types: {room['room_types']}")
            return room["room_types"]
        print("DEBUG: No room types found or room not found.")
        return [] # Return empty list if no types found

    def construct_map(self):
        """
        Constructs the function mapping based on the current room's types
        and the player's inventory.
        """
        # Start with base functions
        self.function_map = self.base_function_map.copy()

        # Add room-type specific functions
        current_types = self.get_current_room_types()
        for room_type in current_types:
            if room_type in self._room_type_data and "functions" in self._room_type_data[room_type]:
                self.function_map.update(self._room_type_data[room_type]["functions"])
                print(f"DEBUG: Added functions for room type: {room_type}")


        # Add item-specific functions based on inventory
        # Iterate through item types that have specific functions defined
        for type, functions in self._item_specific_functions.items():
            # You'll need a way to check if the *type* of item is in the inventory.
            # Assuming state_manager has a method like `has_item_of_type(item_type)`
            # Or, more robustly, iterate inventory and check item types/properties.
            # For simplicity, let's check if the inventory contains ANY item associated with this type.
            # A better approach might be to check specific items or item properties.
            # Example: Check if any book is in inventory
            if type == "book" and self.state_manager.list_inventory_books(True):
                 self.function_map.update(functions)
                 print(f"DEBUG: Added functions for item type: {type} (book)")

            # Add checks for other item types similarly
            # if item_type == "mirror" and self.state_manager.verify_item_in_inventory("mirror"):
            #      self.function_map.update(functions)
            #      print(f"DEBUG: Added functions for item type: {item_type} (mirror)")


        # print(f"DEBUG: Final constructed function map keys: {list(self.function_map.keys())}")


    def construct_tools(self):
        """
        Constructs and returns the list of tool definitions (JSON-like structure)
        available based on the current room's types and inventory.
        This list is built by collecting definitions from relevant types/items
        and then filtering based on the functions currently present in self.function_map.
        """
        # First, build the function map for the current state
        # This ensures self.function_map is up-to-date
        self.construct_map()

        # Collect all potential tool definitions relevant to the current state
        all_potential_definitions = []

        # Add base tools (always available if their function is in the map)
        all_potential_definitions.extend(base_tools)

        # Add room-type specific definitions
        current_types = self.get_current_room_types()
        for room_type in current_types:
            if room_type in self._room_type_data and "definitions" in self._room_type_data[room_type]:
                all_potential_definitions.extend(self._room_type_data[room_type]["definitions"])
                # print(f"DEBUG: Added definitions for room type: {room_type}")

        # Add item-specific definitions based on inventory
        # Iterate through item types that have specific definitions defined
        for type, definitions in self._item_specific_definitions.items():
             # Check if the inventory contains items of this type
             # Example: Check if any book is in inventory
             if type == "book" and self.state_manager.list_inventory_books(True):
                  all_potential_definitions.extend(definitions)
                 # print(f"DEBUG: Added definitions for item type: {item_type} (book)")

             # Add checks for other item types similarly
             # if item_type == "mirror" and self.state_manager.verify_item_in_inventory("mirror"):
             #      all_potential_definitions.extend(definitions)
             #      print(f"DEBUG: Added definitions for item type: {item_type} (mirror)")


        # Now, filter the potential definitions based on which function names
        # are actually present in the constructed function_map.
        available_tools_definitions = []
        available_function_names = set(self.function_map.keys()) # Get a set for efficient lookup

        for definition in all_potential_definitions:
            tool_name = definition.get('name')
            # Check if the tool's name corresponds to an available function
            if tool_name and tool_name in available_function_names:
                 available_tools_definitions.append(definition)
            # Optional: Add a print statement here if you want to see which tools are excluded
            # else:
            #     print(f"Excluding tool definition '{tool_name}' as function is not in map.")

        # print(f"DEBUG: Final available tool definitions count: {len(available_tools_definitions)}")
        # print(f"DEBUG: Final available tool definition names: {[d['name'] for d in available_tools_definitions]}")

        return available_tools_definitions

    def construct_context(self):
        """
        Constructs and returns context for the LLM based on recent actions taken by the functions.
        This will be redundant for many functions, but it is useful for certain essential information
        that needs to be passed to the LLM every prompt, like location, inventory, etc.
        """
        context = []
        now = datetime.now()
        f = now.strftime("%Y-%m-%d %H:%M:%S")
        context.append("#############")
        context.append("Current context:")
        context.append(f"Current time: {f}")

        # Format the current room name and types
        current_room_name = self.state_manager.get_current_room_name()
        current_room_types = self.get_current_room_types()
        format_room = f"Currently, you are in the room: {current_room_name}"
        # if current_room_types:
        #     format_room += f" (Types: {', '.join(current_room_types)})"
        context.append(format_room)

        # Append already formatted context
        context.append("#############")
        context.append(self.state_manager.get_current_emote())
        context.append("#############")
        context.append(self.state_manager.get_possible_emotes())
        context.append("#############")
        context.append("In your inventory the current items are:")
        context.append(self.state_manager.get_inventory_items())
        context.append("#############")
        context.append("In the current room the items are:")
        context.append(self.state_manager.get_items_in_current_room())
        context.append("#############")
        context.append("Current stats:")
        context.append(self.state_manager.get_stats())

        # Add weather context ONLY if the room type is "garden"
        if "garden" in current_room_types:
             try:
                 weather_info = open_meteo_handle.get_full_weather()
                 context.append("#############")
                 context.append("Current outdoor weather:")
                 context.append(weather_info)
             except Exception as e:
                 print(f"Warning: Could not fetch weather for garden: {e}")
                 context.append("#############")
                 context.append("Could not retrieve current outdoor weather.")


        string_context = "\n".join(context)
        return string_context


    def call_function(self, name, args):
        """
        Calls the function mapped to the given name.
        The function map is constructed dynamically BEFORE the call.
        """
        # Ensure the function_map is up-to-date based on the current state BEFORE attempting to call.
        # We no longer pass current_room explicitly here; construct_map gets it from state_manager
        self.construct_map()

        # Look up the function in the map built by construct_map
        func = self.function_map.get(name)

        if func:
            try:
                print(f"Calling {name} with args: {args}")
                # Call the function using the retrieved object and unpack args
                # Ensure args is a dictionary for **args
                if not isinstance(args, dict):
                     print(f"Warning: Arguments for {name} were not a dictionary. Attempting direct pass.")
                     # Handle cases where args might not be a dict, though tool calls usually provide dicts
                     result = func(args) if args else func() # Basic handling, might need refinement
                else:
                     result = func(**args) # func is either a global function or a method object
                print(f"{name} returned: {result}")
                return result
            except TypeError as e:
                # Specific error for argument mismatch
                print(f"Error calling function {name}: Argument mismatch or type error: {e}")
                # Provide feedback that includes the function name
                return f"Error: Invalid arguments provided for function '{name}'. Details: {e}"
            except Exception as e:
                # Catch any other unexpected errors during the function's execution
                print(f"An unexpected error occurred during execution of {name}: {e}")
                # Provide feedback that includes the function name
                return f"Error executing function '{name}'. Details: {e}"
        else:
            # Handle unknown function names for the *current* map configuration
            # Get the current room name for a more helpful error message
            current_room_name = self.state_manager.get_current_room_name()
            print(f"Warning: Attempted to call unknown function: {name} in room '{current_room_name}' or with current inventory.")
            return f"Error: Unknown function '{name}' is not available in your current location ({current_room_name}) or with your current inventory."