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
import os.path
import json
import inspect

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
    kitchen_room_tools,
    lab_room_tools,
    dev_room_tools,
)

from utils import open_meteo_handle, simulation

# Import tools
# We import the tool handlers/classes here
from tools.tools_folder.bluesky_handle import bluesky_bot
from tools.tools_folder.rooms_tools import main_tools_handle

from tools.tools_folder.async_test_tool import simulate_data_fetch

class FunctionBuilder:
    def __init__(self, state_manager=None, signal=None, subdirectory=None, memory_manager=None):
        self.memory = memory_manager
        self.sub_directory=subdirectory
        self._signal_callback = signal
        self.state_manager = state_manager
        self.room_tools = main_tools_handle(self.state_manager, self._signal_callback, self.memory)
        self.A_Life = None
        self._init_alife()


        # --- Central Mapping of Room Types to Functions and Definitions ---
        # This dictionary holds the functions and tool definitions associated with each room type.
        # Keys are room type strings (e.g., "library", "bedroom").
        # Values are dictionaries with keys "functions" (dict of function name -> callable)
        # and "definitions" (list of tool definition dicts).
        self._room_type_data = {
            "dev_room": {
                "functions": {
                    "simulate_data_fetch": simulate_data_fetch

                },
                "definitions": dev_room_tools # Use the imported definition list
            },
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
                     "search_wikipedia_articles": self.room_tools.computer.search_wikipedia_articles,
                     "get_wikipedia_article_content": self.room_tools.computer.get_wikipedia_article_content,
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
                },
                "definitions": white_room_tools
            },
            "kitchen": {
                "functions": {
                    "prepare_food": self.room_tools.kitchen.prepare_food
                },
                "definitions": kitchen_room_tools
            },
            "ALIFE_research":{
                "functions": {
                    "set_current_tick_ALIFE":self.A_Life.set_current_tick_ALIFE,
                    "observe_ALIFE":self.A_Life.observe_ALIFE,
                    "forward_ALIFE": self.A_Life.forward_ALIFE,
                    "backward_ALIFE": self.A_Life.backward_ALIFE,
                    "create_new_simulation": self.A_Life.create_new_simulation,
                    "load_previous_simulation": self.A_Life.load_previous_simulation,
                    "list_simulations": self.A_Life.simulations_manager.list_simulations,
                    "details_of_simulation": self.A_Life.simulations_manager.details_of_simulation,
                    "update_simulation_name": self.A_Life.simulations_manager.update_simulation_name,
                    "add_simulation_detail": self.A_Life.simulations_manager.add_simulation_detail,

                },
                "definitions": lab_room_tools
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
            "list_items_in_current_room": self.state_manager.list_items_in_current_room,
            "set_current_emote": self.state_manager.set_current_emote,
            "move_to_room": self.state_manager.set_current_room,
            "list_all_rooms": self.state_manager.get_all_rooms,
            "examine_item": self.state_manager.get_item_details,
            "pickup_item": self.state_manager.pickup_item,
            "drop_item": self.state_manager.drop_item,
            "consume_item": self.state_manager.consume_item,
            #"trash_item": self.state_manager.trash_item,
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

    def _init_alife(self):
        """
        Initializes the ALifeSimulation instance.
        Loads the first existing simulation from the archive if available,
        otherwise creates a new simulation run and archives it.
        Leaves the ALifeSimulation instance ready to view at tick 0 of the loaded/new history.
        """
        # Define the directory where simulation archives will be stored
        # This path is passed to ALifeSimulation, which passes it to ALifeManager.
        archive_dir = os.path.join(self.sub_directory, "simulation_archives") # Using a clear name
        os.makedirs(archive_dir, exist_ok=True)
        print(f"Ensured archive directory exists at: {archive_dir}")

        # --- Step 1: Initialize ALifeSimulation (which also initializes ALifeManager) ---
        # We initialize it first so we have the manager instance available to query.
        # We don't pass a specific config here yet, let it load defaults initially.
        self.A_Life = simulation.ALifeSimulation(archive_path=archive_dir, state_manager=self.state_manager)
        print("ALifeSimulation instance created, including its manager.")

        # --- Step 2: Check the ALifeManager for existing simulations ---
        # We can directly access the manager instance created within ALifeSimulation
        manager = self.A_Life.simulations_manager

        if not manager:
             print("Error: ALifeManager failed to initialize. Cannot proceed.")
             # Handle this error appropriately, perhaps raise an exception
             return

        # Get the list of simulation IDs from the manager's state
        sim_ids = list(manager._state.keys()) # Accessing the internal state is safe here

        if sim_ids:
            # --- Step 3: Existing simulations found - Load the first one ---
            state_info=self.state_manager.get_sim_state()
            sim_id=state_info.get("id_value", None)
            print(f"Simulation ID from state manager: {sim_id}")
            current_step=state_info.get("sim_current_step", 0)
            if not sim_id:
                print("Warning: No simulation ID found in state manager. Loading the first available simulation.")
                current_sim_id = sim_ids[0]
            else:
                current_sim_id = sim_id
            print(f"Found {len(sim_ids)} existing simulation(s). Attempting to load the last open one with ID: '{current_sim_id}'")
            load_message = self.A_Life.load_previous_simulation(current_sim_id, current_step)

            print(f"Load Status: {load_message}")

            # After load_previous_simulation, self.A_Life instance state (config,
            # history, entities, current_tick) is updated based on the loaded data.
            # load_previous_simulation already sets current_tick to 0.

        else:
            # --- Step 4: No existing simulations found - Create, Run, and Archive a new one ---
            print("No existing simulations found in the archive.")
            print("Creating, running, and archiving a new simulation with default configuration.")

            # The create_new_simulation method handles:
            # 1. Re-initializing the simulation state based on current config (defaults if none loaded).
            # 2. Running the simulation fully to populate history.
            # 3. Archiving the completed run (creating JSON and TXT files, registering with manager).
            # 4. Setting the instance state (history, current_tick=0, etc.) to the new run.
            message = self.A_Life.create_new_simulation()
            current_step=0
            current_sim_id = list(self.A_Life.simulations_manager._state.keys())[0] if self.A_Life.simulations_manager and self.A_Life.simulations_manager._state else "N/A (Error)"

            print(f"New Simulation ID: {message}")

        # --- Step 5: Final Confirmation ---
        # Regardless of whether we loaded or created, the self.A_Life instance
        # should now be initialized and positioned at tick 0 of its history.
        print(f"\nALife initialization complete.")
        if self.A_Life and self.A_Life.history:
             # Find the ID of the simulation currently loaded/created (it will be the first in the manager now)
             self.state_manager.set_sim_state(current_sim_id, self.A_Life.current_tick)
             print(f"Currently loaded Simulation ID: '{current_sim_id}'")
             print(f"Current Tick: {self.A_Life.current_tick}")
             print(f"Total ticks in loaded history: {len(self.A_Life.history)-1}") # Last tick index is len-1
        else:
             print("Warning: ALifeSimulation instance created, but history is empty after initialization.")

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
        format_room = f"Currently, you are in: {current_room_name}\n"
        descriptions = self.state_manager.get_current_room_description()
        print(f"‼️‼️‼️‼️‼️DEBUG: Current room types ‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️: {current_room_types}, descriptions: {descriptions}")
        # if current_room_types:
        #     format_room += f" (Types: {', '.join(current_room_types)})"
        context.append(format_room)
        context.append(descriptions)

        # Append already formatted context
        context.append("\n#############\n")
        context.append(self.state_manager.get_current_emote())
        context.append("\n#############\n")
        context.append(self.state_manager.get_possible_emotes())
        context.append("\n#############\n")
        context.append("In your inventory the current items are:")
        context.append(self.state_manager.get_inventory_items())
        # context.append("#############")
        # context.append("In the current room the items are:")
        # context.append(self.state_manager.list_items_in_current_room()) Keep it lean
        context.append("\n#############\n")
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


    async def call_function(self, name, args):
        """
        Calls the function mapped to the given name.
        The function map is constructed dynamically BEFORE the call.
        Supports both synchronous and asynchronous functions.
        """
        # Ensure the function_map is up-to-date based on the current state BEFORE attempting to call.
        # We no longer pass current_room explicitly here; construct_map gets it from state_manager
        self.construct_map()

        # Look up the function in the map built by construct_map
        func = self.function_map.get(name)

        if func:
            try:
                print(f"Calling {name} with args: {args}")
                # Ensure args is a dictionary for **args
                if not isinstance(args, dict):
                    print(f"Warning: Arguments for {name} were not a dictionary. Attempting direct pass.")
                    # Handle cases where args might not be a dict, though tool calls usually provide dicts
                    if inspect.iscoroutinefunction(func):
                        result = await func(args) if args else await func()
                    else:
                        result = func(args) if args else func() # Basic handling, might need refinement
                else:
                    if inspect.iscoroutinefunction(func):
                        result = await func(**args)
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