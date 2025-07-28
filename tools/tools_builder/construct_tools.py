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

import configparser


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
    harvesting_garden_tools,
    youtube_playlister_tools,
    discogs_tools,
    musicbrainz_tools,
    bluesky_tools # Ensure bluesky_tools is imported if it has definitions
)

from utils import open_meteo_handle, simulation

from tools.tools_folder.garden_tools import Garden_Mananger


# Import tools
# We import the tool handlers/classes here
from tools.tools_folder.rooms_tools import main_tools_handle
from tools.tools_folder.async_test_tool import simulate_data_fetch
from tools.tools_folder.thinking_tool import emit_inner_thought


# --- Global Configuration Loading (Happens once when the module is imported) ---
tools_config = configparser.ConfigParser()
# Attempt to read the config file. Consider providing a default path or making it configurable.
config_file_path = "main_config.ini"
if os.path.exists(config_file_path):
    tools_config.read(config_file_path)
    print(f"Config file '{config_file_path}' loaded.")
else:
    print(f"Warning: Config file '{config_file_path}' not found. Using default 'disabled' for optional tools.")

# Use a default section if 'Tools' is not found, to prevent KeyError
if 'Tools' not in tools_config:
    tools_config['Tools'] = {} # Create an empty section to safely use .getboolean

enabled_tools = tools_config['Tools']

# These booleans will dictate if the tools are *attempted* to be imported and initialized.
# We will then use the instance itself (e.g., self.youtube is not None) to determine if it truly succeeded.
youtube_enabled = enabled_tools.getboolean('enable_youtube', fallback=False)
discogs_enabled = enabled_tools.getboolean('enable_discogs', fallback=False)
musicbrainz_enabled = enabled_tools.getboolean('enable_musicbrainz', fallback=False)
bluesky_enabled = enabled_tools.getboolean('enable_bluesky', fallback=False)

# print(f"DEBUG: YouTube enabled (config): {youtube_enabled}")
# print(f"DEBUG: Discogs enabled (config): {discogs_enabled}")
# print(f"DEBUG: MusicBrainz enabled (config): {musicbrainz_enabled}")
# print(f"DEBUG: Bluesky enabled (config): {bluesky_enabled}")

# --- Conditional Imports (Only import if enabled in config) ---
# This saves memory and avoids NameErrors if external libraries aren't installed.
# We assign these to global variables only if they are imported successfully.
# This pattern ensures that the 'from utils import x' lines are only executed when needed.
if youtube_enabled:
    try:
        from utils import youtube_service
    except ImportError as e:
        print(f"Warning: Could not import youtube_service, disabling YouTube tools. Error: {e}")
        youtube_enabled = False # Mark as disabled if import fails
if discogs_enabled:
    try:
        from utils import discogs
    except ImportError as e:
        print(f"Warning: Could not import discogs, disabling Discogs tools. Error: {e}")
        discogs_enabled = False
if musicbrainz_enabled:
    try:
        from utils import musicbrainz
    except ImportError as e:
        print(f"Warning: Could not import musicbrainz, disabling MusicBrainz tools. Error: {e}")
        musicbrainz_enabled = False
if bluesky_enabled:
    try:
        from tools.tools_folder.bluesky_handle import bluesky_bot
    except ImportError as e:
        print(f"Warning: Could not import bluesky_bot, disabling Bluesky tools. Error: {e}")
        bluesky_enabled = False


class FunctionBuilder:
    def __init__(self, state_manager=None, signal=None, subdirectory=None, memory_manager=None):
        self.memory = memory_manager
        self.sub_directory = subdirectory
        self._signal_callback = signal
        self.state_manager = state_manager
        self.room_tools = main_tools_handle(self.state_manager, self._signal_callback, self.memory)
        self.A_Life = None # Initialized by _init_alife
        self.garden_manager = Garden_Mananger(self.state_manager, self._signal_callback)
        self._init_alife() # ALIFE is always initialized


        # --- Conditional Initialization of Optional Tool Handlers ---
        # Initialize to None first.
        self.youtube = None
        self.discogs_handle = None
        self.musicbrainz_ = None
        self.bluesky = None

        # Use the globally determined `_enabled` flags to attempt instantiation
        if youtube_enabled:
            try:
                # Check if the module was actually imported (prevent NameError if import failed silently)
                if 'youtube_service' in globals():
                    self.youtube = youtube_service.YouTubeTools()
                    print("YouTubeTools instance created.")
                else:
                    print("YouTubeTools not imported due to previous error; skipping instantiation.")
            except Exception as e:
                print(f"Error instantiating YouTubeTools: {e}")
                self.youtube = None # Ensure it's None if instantiation fails

        if discogs_enabled:
            try:
                if 'discogs' in globals():
                    self.discogs_handle = discogs.DiscogsTools()
                    print("DiscogsTools instance created.")
                else:
                    print("DiscogsTools not imported due to previous error; skipping instantiation.")
            except Exception as e:
                print(f"Error instantiating DiscogsTools: {e}")
                self.discogs_handle = None

        if musicbrainz_enabled:
            try:
                if 'musicbrainz' in globals():
                    self.musicbrainz_ = musicbrainz.MusicBrainzSearchTools()
                    print("MusicBrainzSearchTools instance created.")
                else:
                    print("MusicBrainzSearchTools not imported due to previous error; skipping instantiation.")
            except Exception as e:
                print(f"Error instantiating MusicBrainzSearchTools: {e}")
                self.musicbrainz_ = None

        if bluesky_enabled:
            try:
                if 'bluesky_bot' in globals():
                    self.bluesky = bluesky_bot(self.state_manager, self._signal_callback)
                    print("BlueskyBot instance created.")
                else:
                    print("BlueskyBot not imported due to previous error; skipping instantiation.")
            except Exception as e:
                print(f"Error instantiating BlueskyBot: {e}")
                self.bluesky = None


        # --- Central Mapping of Room Types to Functions and Definitions ---
        # Initialize with only the *always-present* room types.
        # Optional integrations will be added dynamically below if they are enabled and initialized.
        self._room_type_data = {
            "planting_garden": {
                "functions": {
                    "plant_seed": self.garden_manager.plant_seed,
                    "check_plant_state": self.garden_manager.check_plant_state,
                    "harvest_plant": self.garden_manager.harvest_plant,
                    "get_current_garden_information": self.garden_manager.get_garden_summary,
                    "water_plot": self.garden_manager.water_plot
                },
                "definitions": harvesting_garden_tools,
                "current_info": self.garden_manager.get_garden_summary
            },
            "dev_room":{
                "functions": {
                    "simulate_data_fetch": simulate_data_fetch
                },
                "definitions": dev_room_tools
            },
            "library": {
                "functions": {
                    "create_book_item": self.state_manager.create_book_item
                },
                "definitions": library_tools
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
                "definitions": living_room_tools,
                "current_info": self.room_tools.living_room.display_information
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
                "definitions": computer_room_tools,
                "current_info": self.room_tools.computer.display_information
            },
             "garden": {
                "functions": {
                     "dig_hole": self.room_tools.garden.dig_hole,
                     "lay_down": self.room_tools.garden.lay_down
                },
                "definitions": garden_room_tools,
                "current_info": self.room_tools.garden.display_information
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
                "definitions": lab_room_tools,
                "current_info": self.A_Life.display_information
            }
            # Add entries for other static room types as needed
        }


        # --- Dynamically Add Optional Tool Data if Enabled and Initialized ---
        if self.musicbrainz_: # Check if the instance was successfully created
            self._room_type_data["musicbrainz"] = {
                "functions": {
                    "musicbrainz_search_artists_by_tags": self.musicbrainz_.search_artists_by_tags,
                    "musicbrainz_search_albums_by_tags": self.musicbrainz_.search_albums_by_tags,
                    "musicbrainz_get_artist_details_and_albums": self.musicbrainz_.get_artist_details_and_albums,
                    "musicbrainz_search_artists_by_name": self.musicbrainz_.search_artists_by_name,
                    "musicbrainz_get_album_tracklist": self.musicbrainz_.get_album_tracklist,
                    "musicbrainz_search_album_by_name": self.musicbrainz_.search_album_by_name
                },
                "definitions": musicbrainz_tools
            }
            print("MusicBrainz tools added to room type data.")

        if self.discogs_handle: # Check if the instance was successfully created
            self._room_type_data["discogs"] = {
                "functions": {
                    "discogs_search_artist_by_name": self.discogs_handle.search_artist_by_name,
                    "discogs_get_artist_master_releases_overview": self.discogs_handle.get_artist_master_releases_overview,
                    "discogs_get_master_release_tracklist": self.discogs_handle.get_master_release_tracklist,
                    "discogs_get_collection_summary": self.discogs_handle.get_collection_summary,
                    "discogs_get_wantlist_summary": self.discogs_handle.get_wantlist_summary,
                    "discogs_search_master_release_by_name": self.discogs_handle.search_master_release_by_name,
                    "discogs_get_collection_unique_artists": self.discogs_handle.get_collection_unique_artists,
                    "discogs_get_wantlist_unique_artists": self.discogs_handle.get_wantlist_unique_artists
                },
                "definitions": discogs_tools
            }
            print("Discogs tools added to room type data.")

        if self.youtube: # Check if the instance was successfully created
            self._room_type_data["youtube_playlists"] = {
                "functions": {
                    "youtube_search_video": self.youtube.search_video,
                    "youtube_create_playlist": self.youtube.create_playlist,
                    "youtube_add_video_to_playlist": self.youtube.add_video_to_playlist,
                    "youtube_open_youtube_item": self.youtube.open_youtube_item
                },
                "definitions": youtube_playlister_tools,
                "current_info": self.youtube.get_summary
            }
            print("YouTube Playlists tools added to room type data.")

        if self.bluesky: # Check if the instance was successfully created
            self._room_type_data["bluesky_social"] = { # Using a distinct room type name
                "functions": {
                    "post_bluesky": self.bluesky.post_bluesky
                },
                "definitions": bluesky_tools # Use the imported definitions list
            }
            print("Bluesky Social tools added to room type data.")


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
            "pickup_item": self.state_manager.pickup_item,
            "examine_item": self.state_manager.get_item_details,
            "drop_item": self.state_manager.drop_item,
            "consume_item": self.state_manager.consume_item,
            #"trash_item": self.state_manager.trash_item,
            "add_item_description": self.state_manager.add_item_description,
            "emit_inner_thought": emit_inner_thought

            # Note: "post_bluesky" was here as an example but is now handled
            # as part of the dynamic _room_type_data for "bluesky_social"
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
        try: # Added try-except for ALife initialization as well
            self.A_Life = simulation.ALifeSimulation(archive_path=archive_dir, state_manager=self.state_manager, signal=self._signal_callback)
            print("ALifeSimulation instance created, including its manager.")
        except Exception as e:
            print(f"Error initializing ALifeSimulation: {e}. ALife features will be unavailable.")
            self.A_Life = None # Ensure A_Life is None if it fails
            # Remove ALIFE_research from _room_type_data if A_Life is None
            # This requires dynamic _room_type_data for ALIFE too, or handling this specific case.
            # For now, _room_type_data is hardcoded for ALIFE, so ALIFE_research functions would fail if A_Life is None.
            # A more robust solution might move ALIFE_research into the dynamic section as well.
            return # Exit if ALife failed to initialize

        # --- Step 2: Check the ALifeManager for existing simulations ---
        # We can directly access the manager instance created within ALifeSimulation
        manager = self.A_Life.simulations_manager

        if not manager:
             print("Error: ALifeManager failed to initialize. Cannot proceed.")
             # Handle this error appropriately, perhaps raise an exception
             return

        # Get the list of simulation IDs from the manager's state
        sim_ids = list(manager._state.keys()) # Accessing the internal state is safe here

        current_sim_id = None # Initialize to None
        current_step = 0

        if sim_ids:
            # --- Step 3: Existing simulations found - Load the first one ---
            state_info = self.state_manager.get_sim_state()
            sim_id = state_info.get("id_value", None)
            print(f"Simulation ID from state manager: {sim_id}")
            current_step = state_info.get("sim_current_step", 0)

            if not sim_id or sim_id not in sim_ids: # Also check if the stored sim_id actually exists
                print("Warning: No valid simulation ID found in state manager or ID does not exist. Loading the first available simulation.")
                current_sim_id = sim_ids[0]
            else:
                current_sim_id = sim_id
            print(f"Found {len(sim_ids)} existing simulation(s). Attempting to load last open/first available with ID: '{current_sim_id}'")
            load_message = self.A_Life.load_previous_simulation(current_sim_id, current_step)

            print(f"Load Status: {load_message}")

        else:
            # --- Step 4: No existing simulations found - Create, Run, and Archive a new one ---
            print("No existing simulations found in the archive.")
            print("Creating, running, and archiving a new simulation with default configuration.")

            message = self.A_Life.create_new_simulation()
            current_step = 0
            # Get the ID of the newly created simulation
            current_sim_id = list(self.A_Life.simulations_manager._state.keys())[0] if self.A_Life.simulations_manager and self.A_Life.simulations_manager._state else "N/A (Error)"

            print(f"New Simulation ID: {message}")

        # --- Step 5: Final Confirmation ---
        print(f"\nALife initialization complete.")
        if self.A_Life and self.A_Life.history:
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
            #print(f"DEBUG: Current room types: {room['room_types']}")
            return room["room_types"]
        #print("DEBUG: No room types found or room not found.")
        return [] # Return empty list if no types found

    def construct_map(self):
        """
        Constructs the function mapping based on the current room's types
        and the player's inventory, with base functions added last.
        """
        # Start with an empty map
        self.function_map = {}
        print(f"DEBUG: Initializing empty function map for dynamic construction.")

        # 1. Add room-type specific functions FIRST
        current_types = self.get_current_room_types()
        for room_type in current_types:
            # Only add if the room_type is actually in the _room_type_data map (which is now dynamic)
            if room_type in self._room_type_data and "functions" in self._room_type_data[room_type]:
                self.function_map.update(self._room_type_data[room_type]["functions"])
                print(f"DEBUG: Added functions for room type: {room_type}")

        # 2. Add item-specific functions (these will overwrite room functions if names clash)
        inventory_items = self.state_manager.get_inventory_items(internal=True)
        if isinstance(inventory_items, list): # Ensure it's a list
            for item_in_inventory in inventory_items:
                if isinstance(item_in_inventory, dict): # Ensure item is a dict
                    item_types_list = item_in_inventory.get("type", [])
                    if isinstance(item_types_list, list): # Ensure types is a list
                        for individual_type_str in item_types_list:
                            if individual_type_str in self._item_specific_functions:
                                self.function_map.update(self._item_specific_functions[individual_type_str])
                                print(f"DEBUG: Added functions for item type: {individual_type_str} from item '{item_in_inventory.get('name', 'Unknown Item')}'")

        # 3. Finally, add base functions LAST.
        # This means if a base function has the same name as a room or item function,
        # the base function's implementation will be the one that is ultimately used.
        self.function_map.update(self.base_function_map)
        #print(f"DEBUG: Added base functions last. Final constructed function map keys: {list(self.function_map.keys())}")

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

        # Add room-type specific definitions
        current_types = self.get_current_room_types()
        for room_type in current_types:
            # Only add if the room_type is actually in the _room_type_data map (which is now dynamic)
            if room_type in self._room_type_data and "definitions" in self._room_type_data[room_type]:
                all_potential_definitions.extend(self._room_type_data[room_type]["definitions"])
                # print(f"DEBUG: Added definitions for room type: {room_type}")

        # Add item-specific definitions based on inventory
        inventory_items = self.state_manager.get_inventory_items(internal=True)
        if isinstance(inventory_items, list): # Ensure it's a list
            for item_in_inventory in inventory_items:
                if isinstance(item_in_inventory, dict): # Ensure item is a dict
                    item_types_list = item_in_inventory.get("type", [])
                    if isinstance(item_types_list, list): # Ensure types is a list
                        for individual_type_str in item_types_list:
                            if individual_type_str in self._item_specific_definitions:
                                all_potential_definitions.extend(self._item_specific_definitions[individual_type_str])
                                # print(f"DEBUG: Added definitions for item type: {individual_type_str} from item '{item_in_inventory.get('name', 'Unknown Item')}'")

        # Add base tools (always available if their function is in the map)
        all_potential_definitions.extend(base_tools)


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

        #print(f"DEBUG: Final available tool definitions count: {len(available_tools_definitions)}")
        #print(f"DEBUG: Final available tool definition names: {[d['name'] for d in available_tools_definitions]}")

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
        context.append("MAIN SOURCE OF UNIVERSAL TRUTH:")
        context.append("#############")
        context.append("Current State:")
        context.append(f"Current time: {f}")

        # Format the current room name and types
        current_room_name = self.state_manager.get_current_room_name()
        current_room_types = self.get_current_room_types()
        format_room = f"Currently, you are in: {current_room_name}\n"

        context.append(format_room)
        #context.append(descriptions)

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
        context.append("\n#############\n")

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



        context.append("#############")
        context.append("END OF MAIN SOURCE OF UNIVERSAL TRUTH")
        string_context = "\n".join(context)
        return string_context

    def get_current_room_info(self): 
        
        # This is currently used to update and display information into the GUI about the current room based on the types. 
        # It retrieves information a function tied to each room type for the room we are in and returns this to the pygame integration
        # I don't know if it should be here
        """
        Constructs and returns specific information about the current room
        including room-type-specific functions for information retrieval.
        """
        current_room_id = self.state_manager.get_current_room_id()
        full_room = self.state_manager._find_room_by_id(current_room_id)

        if not full_room:
            print(f"Error: Could not find room with ID: {current_room_id}")
            return {"title": "Unknown Room", "body": "Could not retrieve information about this room."}

        room_name = full_room.get("name", "Unknown Room")
        
        # Get the general description of the room from the state manager
        
        # Get the list of types associated with the current room
        room_types = self.get_current_room_types()

        room_description = self.state_manager.get_current_room_description()

        # Initialize a list to hold all parts of the body content
        body_parts = [room_description] # Start with the general room description

        # Iterate through room types to find and call specific info functions
        for room_type in room_types:
            # Check if this room type has specific data and a 'current_info' function defined
            # Ensure it's in the dynamically built _room_type_data
            if room_type in self._room_type_data and "current_info" in self._room_type_data[room_type]:
                info_function = self._room_type_data[room_type]["current_info"]
                try:
                    # Call the specific info function for this room type
                    type_info = info_function()
                    if type_info:
                        # Append the specific info, formatted for clarity
                        body_parts.append(f"\n--- {room_type.replace('_', ' ').title()} Details ---\n{type_info}")
                except Exception as e:
                    # Handle potential errors during the call to the info function
                    print(f"Warning: Error calling current_info for room type '{room_type}': {e}")
                    body_parts.append(f"\n--- {room_type.replace('_', ' ').title()} Details ---\n(Error retrieving specific details: {e})")

        # If after collecting all parts, the body is still empty (e.g., no description, no type-specific info)
        if not any(body_parts): # Check if all elements in body_parts are empty/None/False-like
            body_parts = ["No specific information available for this room."]
        
        # Join all collected parts into a single string
        body_content = "\n".join([part for part in body_parts if part]) # Filter out any None or empty strings that might have snuck in

        info = {
            "title": room_name,
            "body": body_content
        }
        return info

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