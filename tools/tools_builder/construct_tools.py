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

# construct_tools.py - Refactored with Unified Tool Definitions System
# This file is responsible for constructing the tools and their definitions for an AI agent.
# Now uses a single unified map to handle all tool cases: room types, inventory items, and base functions.

from utils.loc_datetime import datetime
import os.path
import inspect


# Import the tool definitions lists
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
    harvesting_garden_tools,
    youtube_playlister_tools,
    discogs_tools,
    musicbrainz_tools,
    bluesky_tools,
    seat_tools,
    art_book_tools,
    laptop_tools,
    dispenser_tools,
    maze_tools,
    searxng_tools
)
from tools.tools_folder import simulation

from tools.tools_folder.garden_tools import Garden_Mananger
from tools.tools_folder.rooms_tools import main_tools_handle
from tools.tools_folder.thinking_tool import emit_inner_thought
from tools.tools_folder.images_lab import ImagesLab
from tools.tools_folder.dispenser_tools import DispenserTools

from tools.tools_folder.auction_house import AuctionHouse

from tools.tools_folder.maze import MazeEnvironment

class FunctionBuilder:
    def __init__(self, state_manager=None, signal=None, subdirectory=None, memory_manager=None, config_manager=None, open_meteo=None):
        
        # Configuration flags
        self.youtube_enabled = config_manager.get_config('Tools', "enable_youtube")
        self.discogs_enabled = config_manager.get_config('Tools', "enable_discogs")
        self.musicbrainz_enabled = config_manager.get_config('Tools', "enable_musicbrainz")
        self.bluesky_enabled = config_manager.get_config('Tools', "enable_bluesky")
        self.wikipedia_enabled = config_manager.get_config('Tools', "enable_wikipedia")
        self.searxng_enabled = config_manager.get_config('Tools', "enable_searxng")
        print(f"self.searxng_enabled: {self.searxng_enabled}")

        # Initialize core components
        self.open_meteo = open_meteo
        self.memory = memory_manager
        self.sub_directory = subdirectory
        self._signal_callback = signal
        self.state_manager = state_manager
        self.room_tools = main_tools_handle(self.state_manager, self._signal_callback, self.memory, config_manager, self.open_meteo)
        self.garden_manager = Garden_Mananger(self.state_manager, self._signal_callback, self.open_meteo)
        self.images_lab = ImagesLab(self.sub_directory)
        self.dispenser_tools = DispenserTools(self.state_manager, self._signal_callback)

        self.auction_house=AuctionHouse(state_manager)

        self.maze=MazeEnvironment(state_manager, self._signal_callback)

        self.A_Life = None
        self._init_alife()

        # Initialize optional tool handlers
        self.youtube = None
        self.discogs_handle = None
        self.musicbrainz_ = None
        self.bluesky = None
        self.searxng = None
        
        # Conditional imports and initializations
        self._init_optional_tools()
        
        # Initialize the unified tool definitions map
        self._init_unified_tool_definitions()
        
        # Function map will be constructed dynamically
        self.function_map = {}

    def _init_optional_tools(self):
        """Initialize optional tool handlers based on configuration."""
        
        if self.youtube_enabled:
            try:
                from tools.tools_folder.tools_helpers.services import youtube_service
                self.youtube = youtube_service.YouTubeTools()
                print("YouTubeTools instance created.")
            except Exception as e:
                print(f"Error with YouTube tools: {e}")
                
        if self.discogs_enabled:
            try:
                from tools.tools_folder.tools_helpers.services import discogs
                self.discogs_handle = discogs.DiscogsTools()
                print("DiscogsTools instance created.")
            except Exception as e:
                print(f"Error with Discogs tools: {e}")
                
        if self.musicbrainz_enabled:
            try:
                from tools.tools_folder.tools_helpers.services import musicbrainz
                self.musicbrainz_ = musicbrainz.MusicBrainzSearchTools()
                print("MusicBrainzSearchTools instance created.")
            except Exception as e:
                print(f"Error with MusicBrainz tools: {e}")
                
        if self.bluesky_enabled:
            try:
                from tools.tools_folder.bluesky_handle import bluesky_bot
                self.bluesky = bluesky_bot(self.state_manager, self._signal_callback, self.images_lab)
                print("BlueskyBot instance created.")
            except Exception as e:
                print(f"Error with Bluesky tools: {e}")

        if self.searxng_enabled:
            try:
                from tools.tools_folder.searxnAI import AISearXNG
                self.searxng = AISearXNG()
                print("AISearXNG instance created.")
            except Exception as e:
                print(f"Error with SearxNG tools: {e}")

    def _init_unified_tool_definitions(self):
        """Initialize the unified tool definitions map that handles all cases."""
        
        self.tool_definitions = {
            # Base tools - always available
            "base_functions": {
                "functions": {
                    "list_items_in_current_room": self.state_manager.list_items_in_current_room,
                    "set_current_emote": self.state_manager.set_current_emote,
                    "move_to_room": self.state_manager.set_current_room,
                    "list_all_rooms": self.state_manager.get_all_rooms,
                    "pick_up_item": self.state_manager.pickup_item,
                    # "examine_item": self.state_manager.get_item_details,
                    "examine_item": self.get_item_details_with_tools,
                    "drop_item": self.state_manager.drop_item,
                    "add_item_description": self.state_manager.add_item_description,
                    "emit_inner_thought": emit_inner_thought,
                    "list_items_in_inventory": self.state_manager.get_inventory_items,
                },
                "definitions": base_tools,
                "use_level": "always_available"
            },

            "consumables_tools": {
                "functions": {
                    "consume_item": self.state_manager.consume_item,
                },
                "definitions": base_tools,
                "use_level": "inventory_only",
                "item_types": ["consumable"]
            },
            
            # Room-specific tools
            "planting_garden": {
                "functions": {
                    "plant_seed": self.garden_manager.plant_seed,
                    "check_plant_state": self.garden_manager.check_plant_state,
                    "harvest_plant": self.garden_manager.harvest_plant,
                    "get_current_garden_information": self.garden_manager.ai_get_garden_summary,
                    "water_plot": self.garden_manager.water_plot
                },
                "definitions": harvesting_garden_tools,
                "room_types": ["planting_garden"],
                "display_information": self.garden_manager.get_garden_summary,
                "use_level": "room_type"
            },
            
            "library": {
                "functions": {
                    "create_book_item": self.state_manager.create_book_item
                },
                "definitions": library_tools,
                "room_types": ["library"],
                "use_level": "room_type"
            },
            
            "living_room": {
                "functions": {
                    "look_at_window": self.room_tools.living_room.look_at_window,
                },
                "definitions": living_room_tools,
                "room_types": ["living_room"],
                "display_information": self.room_tools.living_room.display_information,
                "use_level": "room_type"
            },
            
            "bathroom": {
                "functions": {
                    "drink_water": self.room_tools.bathroom.drink_water,
                    "wash_hands": self.room_tools.bathroom.wash_hands
                },
                "definitions": bathroom_tools,
                "room_types": ["bathroom"],
                "use_level": "room_type"
            },
            
            "garden": {
                "functions": {
                    "dig_hole": self.room_tools.garden.dig_hole,
                    "lay_down": self.room_tools.garden.lay_down
                },
                "definitions": garden_room_tools,
                "room_types": ["garden"],
                "display_information": self.room_tools.garden.display_information,
                "use_level": "room_type"
            },
            
            "white_room": {
                "functions": {
                    "meditate": self.room_tools.white_room.meditate
                },
                "definitions": white_room_tools,
                "room_types": ["white_room"],
                "use_level": "room_type"
            },
            
            "kitchen": {
                "functions": {
                    "prepare_food": self.room_tools.kitchen.prepare_food
                },
                "definitions": kitchen_room_tools,
                "room_types": ["kitchen"],
                "use_level": "room_type"
            },
            
            "ALIFE_research": {
                "functions": {
                    "set_current_tick_ALIFE": self.A_Life.set_current_tick_ALIFE if self.A_Life else None,
                    "observe_ALIFE": self.A_Life.observe_ALIFE if self.A_Life else None,
                    "forward_ALIFE": self.A_Life.forward_ALIFE if self.A_Life else None,
                    "backward_ALIFE": self.A_Life.backward_ALIFE if self.A_Life else None,
                    "create_new_simulation": self.A_Life.create_new_simulation if self.A_Life else None,
                    "load_previous_simulation": self.A_Life.load_previous_simulation if self.A_Life else None,
                    "list_simulations": self.A_Life.simulations_manager.list_simulations if self.A_Life and self.A_Life.simulations_manager else None,
                    "details_of_simulation": self.A_Life.simulations_manager.details_of_simulation if self.A_Life and self.A_Life.simulations_manager else None,
                    "update_simulation_name": self.A_Life.simulations_manager.update_simulation_name if self.A_Life and self.A_Life.simulations_manager else None,
                    "add_simulation_detail": self.A_Life.simulations_manager.add_simulation_detail if self.A_Life and self.A_Life.simulations_manager else None,
                },
                "definitions": lab_room_tools,
                "room_types": ["ALIFE_research"],
                "display_information": self.A_Life.display_information if self.A_Life else None,
                "use_level": "room_type"
            },
            
            # Inventory-only item tools
            "book": {
                "functions": {
                    "list_chapters": self.state_manager.list_book_chapters,
                    "add_chapter": self.state_manager.add_book_chapter,
                    "read_chapter": self.state_manager.read_book_chapter,
                    "delete_chapter": self.state_manager.delete_book_chapter,
                    "update_book_chapter": self.state_manager.update_book_chapter,
                },
                "definitions": book_tools,
                "item_types": ["book"],
                "use_level": "inventory_only"
            },
            
            "art_book": {
                "functions": {
                    "create_svg_image": self.images_lab.create_svg_image,
                    "read_archive": self.images_lab.read_archive
                },
                "definitions": art_book_tools,
                "item_types": ["art_book"],
                "use_level": "inventory_only"
            },
            # Dual-use item tools (available in room or inventory)
            "seat": {
                "functions": {
                    "take_a_seat": self.room_tools.living_room.take_a_seat
                },
                "definitions": seat_tools,
                "item_types": ["seat"],
                "use_level": "dual_use"
            },

            "maze": {
                "functions": {
                    "VMaze-create_maze": self.maze.create_maze,
                    "VMaze-observe_environment": self.maze.observe_environment,
                    "VMaze-move": self.maze.move
                },
                "definitions": maze_tools,
                "item_types": ["maze"],
                "use_level": "room_only",
                "display_information": self.maze.display_information
            },

            "bed": {
                "functions": {
                    "sleep": self.room_tools.bedroom.sleep,
                    "look_under_bed": self.room_tools.bedroom.look_under_bed
                },
                "definitions": bedroom_tools,
                "item_types": ["bed"],
                "use_level": "dual_use",
                #"room_types": ["bedroom"]
            },

            "pillow":{
                "functions":{
                    "hug_pillow": self.room_tools.bedroom.hug_pillow
                },
                "definitions": bedroom_tools,
                "item_types": ["pillow"],
                "use_level": "dual_use",
                #"room_types": ["bedroom"]
            },

            "tv":{
                "functions":{
                    "watch_tv": self.room_tools.living_room.watch_tv,
                },
                "definitions": living_room_tools,
                "item_types": ["tv"],
                "use_level": "dual_use",
                #"room_types": ["living_room"]
            },

            "auction":{
                "functions":{
                    "computer_browse_auction_house": self.auction_house.get_pretty_items_list,
                    "computer_lookup_auction_house_item": self.auction_house.lookup_item,
                    "computer_buy_item": self.auction_house.buy_item,
                    "computer_sell_item": self.auction_house.sell_item,
                    "computer_get_currency": self.auction_house.get_currency
                },
                "definitions": laptop_tools,
                "item_types": ["laptop", "desktop_computer"],
                "use_level": "dual_use"
            },

            # Room Only Tools

            "dispenser": {
                "functions": {
                    "dispense_candy": self.dispenser_tools.dispense_candy,
                    "refill_dispenser": self.dispenser_tools.refill_dispenser
                },
                "definitions": dispenser_tools,
                "item_types": ["dispenser"],
                "use_level": "room_only"
            }
        }
        
        # Add conditional tools if they were successfully initialized
        self._add_conditional_tools()

    def _add_conditional_tools(self):
        """Add optional tools to the unified map if they were successfully initialized."""
        
        if self.wikipedia_enabled:
            self.tool_definitions["wikipedia"] = {
                "functions": {
                    "computer_search_wikipedia_articles": self.room_tools.computer.search_wikipedia_articles,
                    "computer_get_wikipedia_article_content": self.room_tools.computer.get_wikipedia_article_content,
                    #"random_wikipedia": self.room_tools.computer.random_wikipedia
                },
                "definitions": computer_room_tools,
                #"room_types": ["computer_room"],
                "item_types": ["wikipedia", "laptop", "desktop_computer"],
                "display_information": self.room_tools.computer.display_information,
                "use_level": "dual_use"
            }
            print("Wikipedia tools added to unified definitions.")

        if self.youtube:
            self.tool_definitions["youtube_playlists"] = {
                "functions": {
                    "youtube_search_video": self.youtube.search_video,
                    "youtube_create_playlist": self.youtube.create_playlist,
                    "youtube_add_video_to_playlist": self.youtube.add_video_to_playlist,
                    "youtube_open_youtube_item": self.youtube.open_youtube_item
                },
                "definitions": youtube_playlister_tools,
                "room_types": ["youtube_playlists", "music_room"],
                "item_types": ["youtube_playlists", "iPod"],
                "display_information": self.youtube.get_summary,
                "use_level": "inventory_only"
            }
            print("YouTube tools added to unified definitions.")

        if self.discogs_handle:
            self.tool_definitions["discogs"] = {
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
                "definitions": discogs_tools,
                "room_types": ["discogs", "music_room"],
                "item_types": ["discogs", "iPod"],
                "use_level": "inventory_only"
            }
            print("Discogs tools added to unified definitions.")

        if self.musicbrainz_:
            self.tool_definitions["musicbrainz"] = {
                "functions": {
                    "musicbrainz_get_artist_details_and_works": self.musicbrainz_.get_artist_details_and_works,
                    "musicbrainz_search_artists_by_name": self.musicbrainz_.search_artists_by_name,
                    "musicbrainz_get_tracklist": self.musicbrainz_.get_tracklist,
                    "musicbrainz_search_release_group": self.musicbrainz_.search_release_group,
                    "musicbrainz_search_by_raw_lucene": self.musicbrainz_.search_by_raw_lucene
                },
                "definitions": musicbrainz_tools,
                "room_types": ["musicbrainz", "music_room"],
                "item_types": ["musicbrainz", "iPod"],
                "use_level": "inventory_only"
            }
            print("MusicBrainz tools added to unified definitions.")

        if self.bluesky:
            self.tool_definitions["bluesky_social"] = {
                "functions": {
                    "post_bluesky": self.bluesky.post_bluesky,
                    "get_posts_needing_responses": self.bluesky.get_posts_needing_responses,
                    "post_reply": self.bluesky.post_reply
                },
                "definitions": bluesky_tools,
                "room_types": ["bluesky_social"],
                "item_types": ["bluesky_social", "cellphone", "laptop"],
                "use_level": "inventory_only"
            }
            print("Bluesky tools added to unified definitions.")
        
        if self.searxng:
            self.tool_definitions["searxng"] = {
                "functions": {
                    "search_searxng": self.searxng.search,
                    "query_searxng_website": self.searxng.query_website,
                    "list_searxng_cache": self.searxng.list_cache
                },
                "definitions": searxng_tools,
                "item_types": ["searxng", "laptop", "desktop_computer"],
                "use_level": "dual_use"
            }
            print("SearxNG tools added to unified definitions.")


# Toggle Implementation
# Toggle Implementation

    def _get_power_toggle_tools(self, items_in_room, inventory_items):
        """
        Generate dynamic toggle tools for items with power_toggle capability.
        Returns: (toggle_definitions, powered_on_items, powered_off_items)
        """

        toggle_definitions = []
        powered_on_items = set()  # item IDs that are ON
        powered_off_items = set()  # item IDs that are OFF
        
        # Check all items (both inventory and room)

        all_items = inventory_items + items_in_room

        
        for item in all_items:
            if not isinstance(item, dict):
                continue
                
            # Check if item has power_toggle capability
            if "power_toggle" not in item:
                continue
                
            item_id = item.get("id")
            item_name = item.get("name", "Unknown Item")
            is_powered_on = item.get("power_toggle", False)
            
            if is_powered_on:
                powered_on_items.add(item_id)
                # Create "toggle OFF" tool
                toggle_definitions.append(
                {
                "type": "function",
                "name":f"toggle_OFF_{item_id}",
                "description":f"Turn OFF the {item_name} {item_id}. This will disable its functions until turned back on.",
                "parameters":{
                    "type":"object",
                    "properties":{
                        "item_id":{
                            "type":"number",
                            "description":f"The ID of the item to toggle OFF (use: {item_id})"
                        }
                    },
                    "required":["item_id"],
                    "additionalProperties":False
                }
                }
                )
            else:
                powered_off_items.add(item_id)
                # Create "toggle ON" tool
                toggle_definitions.append(
                {
                "type": "function",
                "name":f"toggle_ON_{item_id}",
                "description":f"Turn ON the {item_name} {item_id}. This will enable its functions.",
                "parameters":{
                    "type":"object",
                    "properties":{
                        "item_id":{
                            "type":"number",
                            "description":f"The ID of the item to toggle ON (use: {item_id})"
                        }
                    },
                    "required":["item_id"],
                    "additionalProperties":False
                }
                }
                )
        
        return toggle_definitions, powered_on_items, powered_off_items

    def _toggle_item_power(self, item_id: str, turn_on: bool):
        """
        Toggle the power state of an item.
        
        Args:
            item_id: The ID of the item to toggle
            turn_on: True to turn ON, False to turn OFF
        
        Returns:
            Success or error message
        """
        # Get and validate the item
        item_data, error = self.state_manager.inventory_service.get_validated_item_data(item_id)
        if error:
            return error
        
        # Check if item has power_toggle capability
        if "power_toggle" not in item_data:
            return f"Error: Item '{item_data.get('name', 'Unknown')}' does not have power toggle capability."
        
        # Get current state
        current_state = item_data.get("power_toggle", False)
        item_name = item_data.get("name", "Unknown Item")
        
        # Check if already in desired state
        if current_state == turn_on:
            state_str = "ON" if turn_on else "OFF"
            return f"The {item_name} is already turned {state_str}."
        
        # Toggle the state
        item_data["power_toggle"] = turn_on
        
        # Persist the changes
        persist_error = self.state_manager.inventory_service.persist_item_changes(item_id)
        if persist_error:
            return persist_error
        
        # Send feedback
        state_str = "ON" if turn_on else "OFF"
        self._signal_callback({
            "type": "show_message_popup",
            "message": f"Toggled {item_name} {state_str}"
        })
        
        return f"Successfully turned {state_str} the {item_name}."

    def _init_alife(self):
        """Initialize the ALifeSimulation instance."""
        archive_dir = os.path.join(self.sub_directory, "simulation_archives")
        os.makedirs(archive_dir, exist_ok=True)
        
        try:
            self.A_Life = simulation.ALifeSimulation(archive_path=archive_dir, state_manager=self.state_manager, signal=self._signal_callback)
            print("ALifeSimulation instance created.")
            
            # Load existing simulation or create new one
            manager = self.A_Life.simulations_manager
            if manager:
                sim_ids = list(manager._state.keys())
                current_sim_id = None
                current_step = 0
                
                if sim_ids:
                    state_info = self.state_manager.get_sim_state()
                    sim_id = state_info.get("id_value", None)
                    current_step = state_info.get("sim_current_step", 0)
                    
                    if not sim_id or sim_id not in sim_ids:
                        current_sim_id = sim_ids[0]
                    else:
                        current_sim_id = sim_id
                    
                    load_message = self.A_Life.load_previous_simulation(current_sim_id, current_step)
                    print(f"Loaded simulation: {load_message}")
                else:
                    message = self.A_Life.create_new_simulation()
                    current_sim_id = list(self.A_Life.simulations_manager._state.keys())[0] if self.A_Life.simulations_manager._state else "N/A"
                    print(f"Created new simulation: {message}")
                
                if self.A_Life and self.A_Life.history:
                    self.state_manager.set_sim_state(current_sim_id, self.A_Life.current_tick)
                    
        except Exception as e:
            print(f"Error initializing ALifeSimulation: {e}")
            self.A_Life = None

    def get_current_room_types(self):
        """Retrieve the list of types for the current room."""
        current_id = self.state_manager.get_current_room_id()
        room = self.state_manager.room_manager._find_room_by_id(current_id)
        if room and "room_types" in room:
            return room["room_types"]
        return []
        

    def _tool_should_be_available(self, tool_config, current_room_types, items_in_room, inventory_items, powered_off_items):
        """
        Determine if a tool should be available based on current context.
        A tool is available if ANY of its criteria match the current context.
        
        Args:
            powered_off_items: Set of item IDs that are currently powered OFF
        """
        # Skip if functions are None (failed initialization)
        functions = tool_config.get("functions", {})
        if any(func is None for func in functions.values()):
            return False
        
        # Always available tools
        use_level = tool_config.get("use_level", "")
        if use_level == "always_available":
            return True
        
        # Get room and item type lists
        room_types = tool_config.get("room_types", [])
        item_types = tool_config.get("item_types", [])
        
        # Track if we found a match
        room_match = False
        item_match = False
        
        # Check room types if they exist
        if room_types and any(rt in current_room_types for rt in room_types):
            room_match = True
        
        # Check item types if they exist
        if item_types:
            # Helper to check if item is powered and matches types
            def check_item_match(item):
                if not isinstance(item, dict):
                    return False
                item_id = item.get("id")
                item_types_list = item.get("type", [])
                type_matches = any(it in item_types for it in item_types_list)
                
                # If item has power_toggle and is OFF, exclude it
                if type_matches and "power_toggle" in item and item_id in powered_off_items:
                    return False
                
                return type_matches
            
            # For inventory_only tools, only check inventory
            if use_level == "inventory_only":
                item_match = any(check_item_match(inv_item) for inv_item in inventory_items)
            
            elif use_level == "room_only":
                item_match = any(check_item_match(room_item) for room_item in items_in_room)
            
            # For dual_use and room_type tools, check both inventory and room items
            else:
                item_match = (
                    any(check_item_match(inv_item) for inv_item in inventory_items) or
                    any(check_item_match(room_item) for room_item in items_in_room)
                )
        
        return room_match or item_match

    def construct_map(self):
        """Construct the function mapping based on current state using the unified system."""
        self.function_map = {}
        available_tool_keys = set()
        
        print("DEBUG: Constructing function map from unified tool definitions...")
        
        # Get current context
        current_room_types = self.get_current_room_types()
        items_in_room = self.state_manager.inventory_service.list_items_in_current_room(internal=True) or []
        inventory_items = self.state_manager.get_inventory_items(internal=True) or []
        
        # Get power toggle info
        _, _, powered_off_items = self._get_power_toggle_tools(items_in_room, inventory_items)
        
        # Add dynamic toggle functions to function map
        all_items = inventory_items + items_in_room
        for item in all_items:
            if not isinstance(item, dict) or "power_toggle" not in item:
                continue
            item_id = item.get("id")
            is_powered_on = item.get("power_toggle", False)
            
            if is_powered_on:
                self.function_map[f"toggle_OFF_{item_id}"] = lambda item_id=item_id: self._toggle_item_power(item_id, False)
            else:
                self.function_map[f"toggle_ON_{item_id}"] = lambda item_id=item_id: self._toggle_item_power(item_id, True)
        
        # Process each tool definition
        for tool_key, tool_config in self.tool_definitions.items():
            if self._tool_should_be_available(tool_config, current_room_types, items_in_room, inventory_items, powered_off_items):
                functions = tool_config.get("functions", {})
                self.function_map.update(functions)
                available_tool_keys.add(tool_key)
                print(f"DEBUG: Added functions from tool: {tool_key}")
        
        print(f"DEBUG: Final function map has {len(self.function_map)} functions from tools: {available_tool_keys}")

    def construct_tools(self):
        """Construct the list of tool definitions based on current state."""
        self.construct_map()  # Ensure function_map is up-to-date
        
        all_definitions = []
        seen_tool_names = set()
        available_function_names = set(self.function_map.keys())
        
        print("DEBUG: Constructing tool definitions from unified system...")
        
        # Get current context
        current_room_types = self.get_current_room_types()
        items_in_room = self.state_manager.inventory_service.list_items_in_current_room(internal=True) or []
        inventory_items = self.state_manager.get_inventory_items(internal=True) or []
        
        # Get power toggle tools and info
        toggle_definitions, _, powered_off_items = self._get_power_toggle_tools(items_in_room, inventory_items)
        
        # Add toggle tools first
        all_definitions.extend(toggle_definitions)
        seen_tool_names.update(d['name'] for d in toggle_definitions)
        
        # Process each tool definition
        for tool_key, tool_config in self.tool_definitions.items():
            if self._tool_should_be_available(tool_config, current_room_types, items_in_room, inventory_items, powered_off_items):
                definitions = tool_config.get("definitions", [])
                
                # Add definitions uniquely, only for functions that are actually available
                for definition in definitions:
                    tool_name = definition.get('name')
                    if (tool_name and 
                        tool_name not in seen_tool_names and 
                        tool_name in available_function_names):
                        all_definitions.append(definition)
                        seen_tool_names.add(tool_name)
        
        print(f"DEBUG: Final available tool definitions: {len(all_definitions)} tools (including {len(toggle_definitions)} toggle tools)")
        
        return all_definitions

    async def call_function(self, name, args):
        """Call the function mapped to the given name."""
        self.construct_map()  # Ensure function_map is up-to-date
        
        func = self.function_map.get(name)
        
        if func:
            try:
                print(f"Calling {name} with args: {args}")
                
                if not isinstance(args, dict):
                    print(f"Warning: Arguments for {name} were not a dictionary.")
                    if inspect.iscoroutinefunction(func):
                        result = await func(args) if args else await func()
                    else:
                        result = func(args) if args else func()
                else:
                    if inspect.iscoroutinefunction(func):
                        result = await func(**args)
                    else:
                        result = func(**args)
                        
                print(f"{name} returned: {result}")
                return result
                
            except TypeError as e:
                print(f"Error calling function {name}: Argument mismatch: {e}")
                return f"Error: Invalid arguments for function '{name}'. Details: {e}"
            except Exception as e:
                print(f"Unexpected error during execution of {name}: {e}")
                return f"Error executing function '{name}'. Details: {e}"
        else:
            current_room_name = self.state_manager.get_current_room_name()
            print(f"Warning: Unknown function: {name} in room '{current_room_name}'")
            return f"Error: Unknown function '{name}' is not available in your current location ({current_room_name}) or with your current inventory."
        



    def get_current_tools_info(self):
        """
        Constructs and returns specific information about the current context
        by checking all currently available tools for display_information functions.
        """
        current_room_id = self.state_manager.get_current_room_id()
        full_room = self.state_manager.room_manager._find_room_by_id(current_room_id)
        
        if not full_room:
            print(f"Error: Could not find room with ID: {current_room_id}")
            return {"title": "Unknown Room", "body": "Could not retrieve information about this room."}
        
        room_name = full_room.get("name", "Unknown Room")
        room_description = self.state_manager.get_current_room_description()
        
        # Start with the general room description
        body_parts = [room_description] if room_description else []
        
        # Get current context to determine what tools are available
        current_room_types = self.get_current_room_types()
        items_in_room = self.state_manager.inventory_service.list_items_in_current_room(internal=True) or []
        inventory_items = self.state_manager.get_inventory_items(internal=True) or []
        
        # Check all tool definitions for display_information functions
        for tool_key, tool_config in self.tool_definitions.items():
            display_info_func = tool_config.get("display_information")
            
            # Skip if no display function
            if not display_info_func:
                continue

            _, _, powered_off_items = self._get_power_toggle_tools(items_in_room, inventory_items)
            
            # Check if this tool should be included based on current context
            if self._tool_should_be_available(tool_config, current_room_types, items_in_room, inventory_items, powered_off_items):
                try:
                    type_info = display_info_func()
                    if type_info:
                        # Format the tool name for display
                        display_name = tool_key.replace('_', ' ').title()
                        body_parts.append(f"\n--- {display_name} Details ---\n{type_info}")
                        print(f"DEBUG: Added display info from tool: {tool_key}")
                except Exception as e:
                    print(f"Warning: Error calling display_information for tool '{tool_key}': {e}")
                    display_name = tool_key.replace('_', ' ').title()
                    body_parts.append(f"\n--- {display_name} Details ---\n(Error retrieving details: {e})")
        
        # If no information was collected, provide a default message
        if not any(body_parts):
            body_parts = ["No specific information available for this room."]
        
        # Join all parts, filtering out empty strings
        body_content = "\n".join([part for part in body_parts if part])
        
        info = {
            "title": room_name,
            "body": body_content
        }
        
        print(f"DEBUG: Room info constructed with {len(body_parts)} sections")
        return info
    


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
        context.append("This source at any point seen, is the most up to date grounded state.")
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
        context.append("#############")
        # context.append("In the current room the items are:")
        # context.append(self.state_manager.inventory_service.list_items_in_current_room()) # Keep it lean, deactivate this if necesary
        # context.append("\n#############\n")
        context.append("Current stats:")
        context.append(self.state_manager.get_stats())

        context.append("\n#############\n")

        # Add weather context ONLY if the room type is "garden"
        if "garden" in current_room_types:
             try:
                 weather_info = self.open_meteo.get_full_weather()
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

    # TODO: This is awful, rewrite this, or integrate it, or SOMETHING 

    def _get_item_tools_map(self, inventory_items, items_in_room, inventory_only=False):
        """
        Internal method to create item-to-tools mapping.
        
        Args:
            inventory_items: List of items in inventory
            items_in_room: List of items in current room
            inventory_only: If True, only map inventory items. If False, map all items.
            
        Returns:
            dict: {item_id: [list of tool names provided by this item]}
        """
        item_tools_map = {}
        
        # Get powered off items
        _, _, powered_off_items = self._get_power_toggle_tools(items_in_room, inventory_items)
        
        # Determine which items to process
        if inventory_only:
            items_to_process = inventory_items
        else:
            # Combine both, but use a dict to avoid duplicates by item_id
            all_items_dict = {}
            for item in items_in_room:
                if isinstance(item, dict) and "id" in item:
                    all_items_dict[item["id"]] = item
            for item in inventory_items:
                if isinstance(item, dict) and "id" in item:
                    all_items_dict[item["id"]] = item
            items_to_process = list(all_items_dict.values())
        
        # Process each item
        for item in items_to_process:
            if not isinstance(item, dict):
                continue
                
            item_id = item.get("id")
            item_types = item.get("type", [])
            
            if not item_id:
                continue
            
            # Check if item is in inventory
            is_in_inventory = any(
                inv_item.get("id") == item_id 
                for inv_item in inventory_items 
                if isinstance(inv_item, dict)
            )
            
            # Check if item is powered off (if it has power toggle capability)
            if "power_toggle" in item and item_id in powered_off_items:
                # Powered off items don't provide tools
                item_tools_map[item_id] = []
                continue
            
            # List to store tool names this item provides
            provided_tools = []
            
            # Check each tool definition to see if this item enables it
            for tool_key, tool_config in self.tool_definitions.items():
                # Skip tools without item_types requirement
                tool_item_types = tool_config.get("item_types", [])
                if not tool_item_types:
                    continue
                
                # Check if this item's types match the tool's requirements
                if any(item_type in tool_item_types for item_type in item_types):
                    use_level = tool_config.get("use_level", "")
                    
                    # Determine if this item can provide these tools based on use_level and location
                    can_provide = False
                    
                    if use_level == "inventory_only":
                        # Only if item is in inventory
                        can_provide = is_in_inventory
                    elif use_level == "room_only":
                        # Only if item is in room (not in inventory)
                        can_provide = not is_in_inventory
                    elif use_level == "dual_use":
                        # Can be used from either location
                        can_provide = True
                    elif use_level == "room_type":
                        # Can be used from either location (like dual_use)
                        can_provide = True
                    
                    if can_provide:
                        # Get ONLY the function names this tool config actually provides
                        functions = tool_config.get("functions", {})
                        for func_name in functions.keys():
                            if func_name not in provided_tools:
                                provided_tools.append(func_name)
            
            # Add to map (even if empty list, so we know we checked this item)
            item_tools_map[item_id] = provided_tools
        
        return item_tools_map


    def get_all_item_tools_map(self):
        """
        Create a mapping of ALL item IDs (inventory + room) to the tool names they provide.
        
        Returns:
            dict: {item_id: [list of tool names provided by this item]}
        """
        inventory_items = self.state_manager.get_inventory_items(internal=True) or []
        items_in_room = self.state_manager.inventory_service.list_items_in_current_room(internal=True) or []
        
        return self._get_item_tools_map(inventory_items, items_in_room, inventory_only=False)



    def get_item_info_with_tools(self, item_id):
        """
        Get detailed information about an item including what tools it provides.
        Works for items in inventory OR in the current room.
        
        Args:
            item_id: The ID of the item to query
            
        Returns:
            dict: Information about the item and its tools
        """
        item_data, error = self.state_manager.inventory_service.get_validated_item_data(item_id)
        if error:
            return {"error": error}
        
        # 1. Determine Power State
        # If "power_toggle" exists, use its value. If not, it's always True.
        has_switch = "power_toggle" in item_data
        is_powered_on = item_data.get("power_toggle", True) 
        
        # 2. Map Tools - use ALL items map since we might be examining room items
        tools_map = self.get_all_item_tools_map() # TODO: This is broken, it 
        all_potential_tools = tools_map.get(item_id, [])
        
        # 3. Filter Tools based on power
        # Tools are active if the item is powered ON or if it doesn't need power at all.
        active_tools = all_potential_tools if is_powered_on else []
        
        return {
            "item_name": item_data.get("name", "Unknown"),
            "has_power_switch": has_switch,
            "is_powered_on": is_powered_on,
            "provided_tools": active_tools
        }

    def get_item_details_with_tools(self, item_id): # TODO: This is a bit of a hack, but it works for now. It is an attempt to make the system clearer for the LLM to understand.
        """
        Get detailed information about an item including what tools it provides.
        
        Args:
            item_id: The ID of the item to query
            
        Returns:
            dict: Information about the item and its tools
        """
        
        info = self.get_item_info_with_tools(item_id)
        extra_descriptions = []

        # Only mention power if the item actually has a toggle switch
        if info.get("has_power_switch"):
            state = "on" if info["is_powered_on"] else "off"
            extra_descriptions.append(f"The power switch is currently {state}.")

        # List tools (will be empty if powered off, or populated if always-on/powered-on)
        tools = info.get("provided_tools", [])
        if tools:
            extra_descriptions.append(f"Provides tools: {', '.join(tools)}")
        elif info.get("has_power_switch") and not info["is_powered_on"]:
            extra_descriptions.append("Turn the power on to use this item's tools.")


        item_meta = self.state_manager.get_item_details(item_id, internal=True)
        data = item_meta.get("details", {})
        item_display = self.state_manager.inventory_service._format_item_for_display(data) # this is ugly, but it works
        descriptions = data.get("descriptions", [])
        output_string = f"{item_display}\n\n"
        if descriptions and isinstance(descriptions, list) and all(isinstance(d, str) for d in descriptions):
            all_descriptions = descriptions + extra_descriptions
            output_string += "\n".join(all_descriptions)
        else:
            output_string += "(No description available.)"
        return output_string