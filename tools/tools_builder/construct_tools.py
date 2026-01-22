# construct_tools.py - Refactored with Centralized Tool Management
# This file is responsible for constructing the tools and their definitions for an AI agent.
# Now features a cleaner, centralized approach to tool availability and item-tool relationships.

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


class ItemContext:
    """Centralized context about items and their power states."""
    
    def __init__(self, inventory_items, room_items):
        self.inventory_items = inventory_items or []
        self.room_items = room_items or []
        self.all_items = self._build_all_items_map()
        self.powered_off_items = self._identify_powered_off_items()
    
    def _build_all_items_map(self):
        """Build a unified map of all items by ID."""
        items_map = {}
        for item in self.room_items + self.inventory_items:
            if isinstance(item, dict) and "id" in item:
                items_map[item["id"]] = item
        return items_map
    
    def _identify_powered_off_items(self):
        """Identify all items that are powered off."""
        powered_off = set()
        for item_id, item in self.all_items.items():
            if "power_toggle" in item and not item.get("power_toggle", False):
                powered_off.add(item_id)
        return powered_off
    
    def is_item_in_inventory(self, item_id):
        """Check if an item is in the inventory."""
        return any(
            item.get("id") == item_id 
            for item in self.inventory_items 
            if isinstance(item, dict)
        )
    
    def is_item_powered_on(self, item_id):
        """Check if an item is powered on (or has no power toggle)."""
        return item_id not in self.powered_off_items
    
    def get_item(self, item_id):
        """Get item data by ID."""
        return self.all_items.get(item_id)
    
    def get_items_by_type(self, item_types, location=None):
        """
        Get items matching any of the given types.
        
        Args:
            item_types: List of item type strings to match
            location: 'inventory', 'room', or None for both
        """
        matching_items = []
        
        items_to_check = []
        if location == 'inventory':
            items_to_check = self.inventory_items
        elif location == 'room':
            items_to_check = self.room_items
        else:
            items_to_check = list(self.all_items.values())
        
        for item in items_to_check:
            if not isinstance(item, dict):
                continue
            
            item_item_types = item.get("type", [])
            if any(itype in item_types for itype in item_item_types):
                matching_items.append(item)
        
        return matching_items


class ToolAvailabilityChecker:
    """Centralized logic for determining tool availability."""
    
    def __init__(self, item_context, current_room_types):
        self.item_context = item_context
        self.current_room_types = current_room_types
    
    def is_tool_available(self, tool_config):
        """
        Determine if a tool should be available based on current context.
        
        Returns:
            bool: True if the tool should be available
        """
        # Skip if functions are None (failed initialization)
        functions = tool_config.get("functions", {})
        if any(func is None for func in functions.values()):
            return False
        
        use_level = tool_config.get("use_level", "")
        
        # Always available tools
        if use_level == "always_available":
            return True
        
        # Check room types and item types
        room_match = self._check_room_match(tool_config)
        item_match = self._check_item_match(tool_config)
        
        return room_match or item_match
    
    def _check_room_match(self, tool_config):
        """Check if tool matches current room types."""
        room_types = tool_config.get("room_types", [])
        if not room_types:
            return False
        return any(rt in self.current_room_types for rt in room_types)
    
    def _check_item_match(self, tool_config):
        """Check if tool matches available items based on use_level."""
        item_types = tool_config.get("item_types", [])
        if not item_types:
            return False
        
        use_level = tool_config.get("use_level", "")
        
        # Get matching items based on location requirements
        if use_level == "inventory_only":
            matching_items = self.item_context.get_items_by_type(item_types, location='inventory')
        elif use_level == "room_only":
            matching_items = self.item_context.get_items_by_type(item_types, location='room')
        else:  # dual_use, room_type, or other
            matching_items = self.item_context.get_items_by_type(item_types)
        
        # Filter out powered-off items
        for item in matching_items:
            item_id = item.get("id")
            if item_id and self.item_context.is_item_powered_on(item_id):
                return True
        
        return False


class ItemToolMapper:
    """Centralized logic for mapping items to their provided tools."""
    
    def __init__(self, tool_definitions, item_context):
        self.tool_definitions = tool_definitions
        self.item_context = item_context
    
    def get_tools_for_item(self, item_id):
        """
        Get all tool names that an item provides.
        
        Args:
            item_id: The ID of the item
            
        Returns:
            list: Tool names provided by this item (empty if powered off)
        """
        item = self.item_context.get_item(item_id)
        if not item:
            return []
        
        # Check if powered off
        if not self.item_context.is_item_powered_on(item_id):
            return []
        
        item_types = item.get("type", [])
        is_in_inventory = self.item_context.is_item_in_inventory(item_id)
        
        provided_tools = []
        
        # Check each tool definition
        for tool_key, tool_config in self.tool_definitions.items():
            tool_item_types = tool_config.get("item_types", [])
            if not tool_item_types:
                continue
            
            # Check if item type matches
            if not any(itype in tool_item_types for itype in item_types):
                continue
            
            # Check if item location matches use_level
            use_level = tool_config.get("use_level", "")
            
            can_provide = False
            if use_level == "inventory_only":
                can_provide = is_in_inventory
            elif use_level == "room_only":
                can_provide = not is_in_inventory
            elif use_level in ["dual_use", "room_type"]:
                can_provide = True
            
            if can_provide:
                # Add all function names from this tool config
                functions = tool_config.get("functions", {})
                provided_tools.extend(functions.keys())
        
        return provided_tools
    
    def get_all_items_tool_map(self):
        """
        Create a mapping of all item IDs to their provided tools.
        
        Returns:
            dict: {item_id: [list of tool names]}
        """
        tool_map = {}
        for item_id in self.item_context.all_items.keys():
            tool_map[item_id] = self.get_tools_for_item(item_id)
        return tool_map


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
        self.auction_house = AuctionHouse(state_manager)
        self.maze = MazeEnvironment(state_manager, self._signal_callback)

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
                    # "examine_item": self.state_manager.get_item_details, # Old method
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
                #"room_types": ["bedroom"] # Left in for reference
            },

            "pillow": {
                "functions": {
                    "hug_pillow": self.room_tools.bedroom.hug_pillow
                },
                "definitions": bedroom_tools,
                "item_types": ["pillow"],
                "use_level": "dual_use",
                #"room_types": ["bedroom"] # Left in for reference
            },

            "tv": {
                "functions": {
                    "watch_tv": self.room_tools.living_room.watch_tv,
                },
                "definitions": living_room_tools,
                "item_types": ["tv"],
                "use_level": "dual_use",
                #"room_types": ["living_room"] # Left in for reference
            },

            "auction": {
                "functions": {
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
                    #"random_wikipedia": self.room_tools.computer.random_wikipedia # Old, not used, could be though
                },
                "definitions": computer_room_tools,
                #"room_types": ["computer_room"], # Left in for reference
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

    def _get_current_context(self):
        """Get the current context including room types and items."""
        current_room_types = self.get_current_room_types()
        items_in_room = self.state_manager.inventory_service.list_items_in_current_room(internal=True) or []
        inventory_items = self.state_manager.get_inventory_items(internal=True) or []
        
        item_context = ItemContext(inventory_items, items_in_room)
        
        return current_room_types, item_context

    def get_current_room_types(self):
        """Retrieve the list of types for the current room."""
        current_id = self.state_manager.get_current_room_id()
        room = self.state_manager.room_manager._find_room_by_id(current_id)
        if room and "room_types" in room:
            return room["room_types"]
        return []

    def _generate_power_toggle_tools(self, item_context):
        """
        Generate dynamic toggle tools for items with power_toggle capability.
        
        Returns:
            list: Toggle tool definitions
        """
        toggle_definitions = []
        
        for item_id, item in item_context.all_items.items():
            if "power_toggle" not in item:
                continue
            
            item_name = item.get("name", "Unknown Item")
            is_powered_on = item.get("power_toggle", False)
            
            if is_powered_on:
                # Create "toggle OFF" tool
                toggle_definitions.append({
                    "type": "function",
                    "name": f"toggle_OFF_{item_id}",
                    "description": f"Turn OFF the {item_name} {item_id}. This will disable its functions until turned back on.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_id": {
                                "type": "number",
                                "description": f"The ID of the item to toggle OFF (use: {item_id})"
                            }
                        },
                        "required": ["item_id"],
                        "additionalProperties": False
                    }
                })
            else:
                # Create "toggle ON" tool
                toggle_definitions.append({
                    "type": "function",
                    "name": f"toggle_ON_{item_id}",
                    "description": f"Turn ON the {item_name} {item_id}. This will enable its functions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_id": {
                                "type": "number",
                                "description": f"The ID of the item to toggle ON (use: {item_id})"
                            }
                        },
                        "required": ["item_id"],
                        "additionalProperties": False
                    }
                })
        
        return toggle_definitions

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

    def construct_map(self):
        """Construct the function mapping based on current state using the unified system."""
        self.function_map = {}
        available_tool_keys = set()
        
        print("DEBUG: Constructing function map from unified tool definitions...")
        
        # Get current context
        current_room_types, item_context = self._get_current_context()
        checker = ToolAvailabilityChecker(item_context, current_room_types)
        
        # Add dynamic toggle functions to function map
        for item_id in item_context.all_items.keys():
            item = item_context.get_item(item_id)
            if "power_toggle" not in item:
                continue
            
            is_powered_on = item.get("power_toggle", False)
            
            if is_powered_on:
                self.function_map[f"toggle_OFF_{item_id}"] = lambda item_id=item_id: self._toggle_item_power(item_id, False)
            else:
                self.function_map[f"toggle_ON_{item_id}"] = lambda item_id=item_id: self._toggle_item_power(item_id, True)
        
        # Process each tool definition
        for tool_key, tool_config in self.tool_definitions.items():
            if checker.is_tool_available(tool_config):
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
        current_room_types, item_context = self._get_current_context()
        checker = ToolAvailabilityChecker(item_context, current_room_types)
        
        # Get and add power toggle tools first
        toggle_definitions = self._generate_power_toggle_tools(item_context)
        all_definitions.extend(toggle_definitions)
        seen_tool_names.update(d['name'] for d in toggle_definitions)
        
        # Process each tool definition
        for tool_key, tool_config in self.tool_definitions.items():
            if checker.is_tool_available(tool_config):
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
        # Detailed Debugging
        print(f"DEBUG: Available tool names: {seen_tool_names}")
        print(f"DEBUG: Available function names: {available_function_names}")
        
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
        
        # Get current context
        current_room_types, item_context = self._get_current_context()
        checker = ToolAvailabilityChecker(item_context, current_room_types)
        
        # Check all tool definitions for display_information functions
        for tool_key, tool_config in self.tool_definitions.items():
            display_info_func = tool_config.get("display_information")
            
            # Skip if no display function
            if not display_info_func:
                continue
            
            # Check if this tool should be included based on current context
            if checker.is_tool_available(tool_config):
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

        # Append already formatted context
        context.append("\n#############\n")
        context.append(self.state_manager.get_current_emote())
        context.append("\n#############\n")
        context.append(self.state_manager.get_possible_emotes())
        context.append("\n#############\n")
        context.append("In your inventory the current items are:")
        context.append(self.state_manager.get_inventory_items())
        context.append("#############")
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

    # ========================================================================
    # CENTRALIZED ITEM-TOOL RELATIONSHIP METHODS
    # ========================================================================

    def get_all_item_tools_map(self):
        """
        Create a mapping of ALL item IDs (inventory + room) to the tool names they provide.
        
        Returns:
            dict: {item_id: [list of tool names provided by this item]}
        """
        _, item_context = self._get_current_context()
        mapper = ItemToolMapper(self.tool_definitions, item_context)
        return mapper.get_all_items_tool_map()

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
        
        # Get item context
        _, item_context = self._get_current_context()
        
        # Determine power state
        has_switch = "power_toggle" in item_data
        is_powered_on = item_context.is_item_powered_on(item_id)
        
        # Get tools this item provides
        mapper = ItemToolMapper(self.tool_definitions, item_context)
        provided_tools = mapper.get_tools_for_item(item_id)
        
        return {
            "item_name": item_data.get("name", "Unknown"),
            "has_power_switch": has_switch,
            "is_powered_on": is_powered_on,
            "provided_tools": provided_tools
        }

    def get_item_details_with_tools(self, item_id):
        """
        Get detailed information about an item including what tools it provides.
        Formatted for display to the user.
        
        Args:
            item_id: The ID of the item to query
            
        Returns:
            str: Formatted item information
        """
        info = self.get_item_info_with_tools(item_id)
        
        if "error" in info:
            return info["error"]
        
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

        # Get base item details
        item_meta = self.state_manager.get_item_details(item_id, internal=True)
        data = item_meta.get("details", {})
        item_display = self.state_manager.inventory_service._format_item_for_display(data)
        descriptions = data.get("descriptions", [])
        
        output_string = f"{item_display}\n\n"
        
        if descriptions and isinstance(descriptions, list) and all(isinstance(d, str) for d in descriptions):
            all_descriptions = descriptions + extra_descriptions
            output_string += "\n".join(all_descriptions)
        else:
            output_string += "(No description available.)"
        
        return output_string