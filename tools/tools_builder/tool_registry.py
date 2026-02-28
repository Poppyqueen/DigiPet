# tool_registry.py
# Owns two things that belong together:
#   1. Service instances (garden_manager, images_lab, lighthouse, etc.)
#   2. The tool_definitions dict that references those service methods
#
# It does NOT own availability logic — that lives in tool_availability.py.
# It does NOT own construct_map / construct_tools / call_function — those live in construct_tools.py.
#
# Initialization order matters here:
#   Phase 1: Services that have NO availability dependency (garden, images_lab, etc.)
#   Phase 2: Build tool_definitions (references service methods)
#   Phase 3: Build the toolset_checker from tool_definitions (needs the dict to exist)
#   Phase 4: Services that NEED the toolset_checker (lighthouse, etc.)

import os
from tools.tools_folder.alife_controller import ALifeController
from tools.tools_folder.garden_tools import Garden_Mananger
from tools.tools_folder.rooms_tools import main_tools_handle
from tools.tools_folder.thinking_tool import emit_inner_thought
from tools.tools_folder.images_lab import ImagesLab
from tools.tools_folder.dispenser_tools import DispenserTools
from tools.tools_folder.auction_house import AuctionHouse
from tools.tools_folder.maze import MazeEnvironment
from tools.tools_folder.lighthouse_controller import LighthouseController
from tools.tools_folder.items_toggle import ItemToggleTool

from tools.tools_folder.book_tools import BookTools
from tools.tools_folder.consumables import ConsumablesTools


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
    searxng_tools,
    iov_pressure_tools,
    lamp_tools,
    spirit_pan_tools,
    clockwork_lens_tools,
    lantern_room_tools,
    fresnel_lens_tools,
    spirit_source_tools,
    accessible_light_viewing_room_tools,
    toggle_item_power_tool,
)

from .tool_availability import make_toolset_checker


class ToolRegistry:
    """
    Owns service instances and the tool_definitions dict.

    Consumed by FunctionBuilder (construct_tools.py), which handles
    the runtime mechanics of map construction, tool dispatch, and context building.

    Typical usage in FunctionBuilder:
        self.registry = ToolRegistry(state_manager, signal, subdirectory,
                                     memory_manager, config_manager, open_meteo,
                                     get_context_fn=self._get_current_context)
        self.tool_definitions = self.registry.tool_definitions
        # Services are accessed via self.registry.lighthouse, etc.
    """

    def __init__(self, state_manager, signal, subdirectory,
                 memory_manager, config_manager, open_meteo,
                 get_context_fn):
        """
        Args:
            get_context_fn: Zero-arg callable → (room_types, ItemContext).
                            Provided by FunctionBuilder so the toolset_checker
                            always reads live state. Must be bound before passing.
        """
        self._signal = signal
        self._get_context = get_context_fn

        # --- Feature flags ---
        self.youtube_enabled       = config_manager.get_config("Tools", "enable_youtube")
        self.discogs_enabled       = config_manager.get_config("Tools", "enable_discogs")
        self.musicbrainz_enabled   = config_manager.get_config("Tools", "enable_musicbrainz")
        self.bluesky_enabled       = config_manager.get_config("Tools", "enable_bluesky")
        self.wikipedia_enabled     = config_manager.get_config("Tools", "enable_wikipedia")
        self.searxng_enabled       = config_manager.get_config("Tools", "enable_searxng")

        # =================================================================
        # Phase 1 — services with no availability dependency
        # =================================================================
        self.room_tools     = main_tools_handle(state_manager, signal, memory_manager, config_manager, open_meteo)
        self.garden_manager = Garden_Mananger(state_manager, signal, open_meteo)
        self.images_lab     = ImagesLab(subdirectory)
        self.dispenser_tools = DispenserTools(state_manager, signal)
        self.auction_house  = AuctionHouse(state_manager)
        self.maze           = MazeEnvironment(state_manager, signal)
        self.A_Life         = ALifeController(state_manager=state_manager, signal=signal, base_path=subdirectory)
        self.book_tools     = BookTools(state_manager, signal)
        self.consumables_tools = ConsumablesTools(state_manager, signal)

        self.item_toggle    = ItemToggleTool(state_manager, signal)

        # Optional services
        self.youtube         = None
        self.discogs_handle  = None
        self.musicbrainz_    = None
        self.bluesky         = None
        self.searxng         = None
        self._init_optional_services(state_manager, signal)

        # =================================================================
        # Phase 2 — build tool_definitions (needs service methods to exist)
        # =================================================================
        self.tool_definitions = self._build_tool_definitions(state_manager, open_meteo)
        self._add_conditional_tools(state_manager) # State manager not used for these tools, but kept for consistency

        # =================================================================
        # Phase 3 — build toolset_checker (needs tool_definitions to exist)
        # =================================================================
        self.toolset_checker = make_toolset_checker(
            get_context_fn=self._get_context,
            tool_definitions=self.tool_definitions,   # passed by reference
        )

        # =================================================================
        # Phase 4 — services that need the toolset_checker
        # =================================================================
        self.lighthouse = LighthouseController(
            state_manager,
            signal,
            open_meteo,
            is_toolset_available=self.toolset_checker,
            base_path=subdirectory,
        )
        self._add_lighthouse_tools()

    # ------------------------------------------------------------------
    # Phase 1 helpers
    # ------------------------------------------------------------------


    def _init_optional_services(self, state_manager, signal):
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
                self.bluesky = bluesky_bot(state_manager, signal, self.images_lab)
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

    # ------------------------------------------------------------------
    # Phase 2 helpers
    # ------------------------------------------------------------------

    def _build_tool_definitions(self, state_manager, open_meteo) -> dict:
        """
        The canonical tool_definitions dict.
        All service references are resolved here — services must exist before this runs.
        """
        al = self.A_Life  # shorthand

        return {
            # ----------------------------------------------------------------
            # Always available
            # ----------------------------------------------------------------
            "base_functions": {
                "functions": {
                    "list_items_in_current_room":   state_manager.list_items_in_current_room,
                    "set_current_emote":            state_manager.set_current_emote,
                    "move_to_room":                 state_manager.set_current_room,
                    "list_all_rooms":               state_manager.get_all_rooms,
                    "pick_up_item":                 state_manager.pickup_item,
                    "examine_item":                 None,  # set by FunctionBuilder (needs self ref)
                    "drop_item":                    state_manager.drop_item,
                    "add_item_description":         state_manager.add_item_description,
                    "emit_inner_thought":           emit_inner_thought,
                    "list_items_in_inventory":      state_manager.get_inventory_items,
                },
                "definitions": base_tools,
                "use_level": "always_available",
            },
            "consumables_tools": {
                "functions": {"consume_item": self.consumables_tools.consume_item},
                "definitions": base_tools,
                "use_level": "inventory_only",
                "item_types": ["consumable"], # TODO: Add agent information, return the uses left when holding an item
            },

            # ----------------------------------------------------------------
            # Room-specific
            # ----------------------------------------------------------------
            "planting_garden": {
                "functions": {
                    "plant_seed":                       self.garden_manager.plant_seed,
                    "check_plant_state":                self.garden_manager.check_plant_state,
                    "harvest_plant":                    self.garden_manager.harvest_plant,
                    "get_current_garden_information":   self.garden_manager.ai_get_garden_summary,
                    "water_plot":                       self.garden_manager.water_plot,
                },
                "definitions": harvesting_garden_tools,
                "room_types": ["planting_garden"],
                "display_information":  self.garden_manager.get_garden_summary,
                "agent_information":    self.garden_manager.get_garden_summary,
            },
            "library": {
                "functions": {"create_book_item": self.book_tools.create_book_item},
                "definitions": library_tools,
                "room_types": ["library"],
            },
            "living_room": {
                "functions": {"look_at_window": self.room_tools.living_room.look_at_window}, # TODO: make this an item
                "definitions": living_room_tools,
                "room_types": ["living_room"],
                # "display_information":  self.room_tools.living_room.display_information, # TODO: This returns... TV info, not specific to room
                # "agent_information":    self.room_tools.living_room.display_information,
            },
            "bathroom": {
                "functions": {
                    "drink_water":  self.room_tools.bathroom.drink_water,
                    "wash_hands":   self.room_tools.bathroom.wash_hands,
                },
                "definitions": bathroom_tools,
                "room_types": ["bathroom"],
            },
            "garden": {
                "functions": {
                    "dig_hole":     self.room_tools.garden.dig_hole,
                    "lay_down":     self.room_tools.garden.lay_down,
                },
                "definitions": garden_room_tools,
                "room_types": ["garden"],
                "display_information":  self.room_tools.garden.display_information,
                "agent_information":    self.room_tools.garden.display_information,
            },
            "white_room": {
                "functions": {"meditate": self.room_tools.white_room.meditate},
                "definitions": white_room_tools,
                "room_types": ["white_room"],
            },
            "kitchen": {
                "functions": {"prepare_food": self.room_tools.kitchen.prepare_food},
                "definitions": kitchen_room_tools,
                "room_types": ["kitchen"],
            },
            "ALIFE_research": {
                "functions": {
                    "set_current_tick_ALIFE":       al.set_current_tick_ALIFE          if al else None,
                    "observe_ALIFE":                al.observe_ALIFE                   if al else None,
                    "forward_ALIFE":                al.forward_ALIFE                   if al else None,
                    "backward_ALIFE":               al.backward_ALIFE                  if al else None,
                    "create_new_simulation":        al.create_new_simulation           if al else None,
                    "load_previous_simulation":     al.load_previous_simulation        if al else None,
                    "list_simulations":             al.list_simulations                if al else None,
                    "details_of_simulation":        al.details_of_simulation           if al else None,
                    "update_simulation_name":       al.update_simulation_name          if al else None,
                    "add_simulation_detail":        al.add_simulation_detail           if al else None,
                    #"display_information":          al.display_information             if al else None,
                },
                "definitions": lab_room_tools,
                "room_types": ["ALIFE_research"],
                "display_information": al.display_information if al else None,
                # agent_information intentionally omitted — contains restricted info (see TODO in original)
            },

            # ----------------------------------------------------------------
            # Item-based — inventory only
            # ----------------------------------------------------------------
            "book": {
                "functions": {
                    "list_chapters":        self.book_tools.list_book_chapters,
                    "add_chapter":          self.book_tools.add_book_chapter,
                    "read_chapter":         self.book_tools.read_book_chapter,
                    "delete_chapter":       self.book_tools.delete_book_chapter,
                    "update_book_chapter":  self.book_tools.update_book_chapter,
                },
                "definitions": book_tools,
                "item_types": ["book"],
                "use_level": "inventory_only",
            },
            "art_book": {
                "functions": {
                    "create_svg_image": self.images_lab.create_svg_image,
                    "read_archive":     self.images_lab.read_archive,
                },
                "definitions": art_book_tools,
                "item_types": ["art_book"],
                "use_level": "inventory_only",
            },

            # ----------------------------------------------------------------
            # Item-based — dual use / room only
            # ----------------------------------------------------------------
            "seat": {
                "functions": {"take_a_seat": self.room_tools.living_room.take_a_seat},
                "definitions": seat_tools,
                "item_types": ["seat"],
                "use_level": "dual_use",
            },
            "maze": {
                "functions": {
                    "VMaze-create_maze":        self.maze.create_maze,
                    "VMaze-observe_environment": self.maze.observe_environment,
                    "VMaze-move":               self.maze.move,
                },
                "definitions": maze_tools,
                "item_types": ["maze"],
                "use_level": "room_only",
                "display_information": self.maze.display_information,
                # agent_information intentionally omitted — contains restricted info (see TODO in original)
            },

# Added manually
            "bed": {
                "functions": {
                    "sleep":                self.room_tools.bedroom.sleep,
                    "look_under_bed":       self.room_tools.bedroom.look_under_bed
                },
                "definitions": bedroom_tools,
                "item_types": ["bed"],
                "use_level": "dual_use",
                #"room_types": ["bedroom"] # Left in for reference
            },

            "pillow": {
                "functions": {
                    "hug_pillow":           self.room_tools.bedroom.hug_pillow
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
                    "refill_dispenser": self.dispenser_tools.refill_dispenser,
                    "examine_dispenser": self.dispenser_tools.examine_dispenser
                },
                "definitions": dispenser_tools,
                "item_types": ["dispenser"],
                "use_level": "room_only"
            },
            # ----------------------------------------------------------------
            # Information-only entries (no functions key — availability-gated
            # agent_information sources, not action tools)
            # ----------------------------------------------------------------
            "outdoors_view": {
                # No "functions" key — this entry exists purely to gate access
                # to agent_information based on room type. The ToolAvailabilityChecker
                # will treat missing/empty functions as available (no None check needed)
                # because is_tool_available only None-checks values that exist.
                "definitions": garden_room_tools,
                "room_types": ["outdoors_view"],
                "display_information": self.room_tools.garden.display_information,
                "agent_information": self.room_tools.garden.display_information,
            },
            "power_toggle": { 
                # Power toggle special key, ignores power state. Any item that has this key will be managed by a power toggle to active its functions.
                "functions": {
                    "toggle_item_power": self.item_toggle.toggle_item_power_auto,
                },
                "definitions": [toggle_item_power_tool],
                "item_types": ["toggle_item_power"],
                "use_level": "dual_use",
                "ignore_power_state": True
            }
        }

    def _add_conditional_tools(self, state_manager): # State manager not used for these tools, but kept for consistency
        """Append optional tool entries after the base dict is built."""

        if self.wikipedia_enabled:
            self.tool_definitions["wikipedia"] = {
                "functions": {
                    "computer_search_wikipedia_articles":       self.room_tools.computer.search_wikipedia_articles,
                    "computer_get_wikipedia_article_content":   self.room_tools.computer.get_wikipedia_article_content,
                },
                "definitions": computer_room_tools,
                "item_types": ["wikipedia", "laptop", "desktop_computer"],
                "display_information": self.room_tools.computer.display_information,
                "use_level": "dual_use",
            }
            print("Wikipedia tools added.")

        if self.youtube:
            self.tool_definitions["youtube_playlists"] = {
                "functions": {
                    "youtube_search_video":             self.youtube.search_video,
                    "youtube_create_playlist":          self.youtube.create_playlist,
                    "youtube_add_video_to_playlist":    self.youtube.add_video_to_playlist,
                    "youtube_open_youtube_item":        self.youtube.open_youtube_item,
                },
                "definitions": youtube_playlister_tools,
                "room_types": ["youtube_playlists", "music_room"],
                "item_types": ["youtube_playlists", "iPod"],
                "display_information": self.youtube.get_summary,
                "use_level": "inventory_only",
            }
            print("YouTube tools added.")


        if self.discogs_handle:
            self.tool_definitions["discogs"] = {
                "functions": {
                    "discogs_search_artist_by_name":                self.discogs_handle.search_artist_by_name,
                    "discogs_get_artist_master_releases_overview":  self.discogs_handle.get_artist_master_releases_overview,
                    "discogs_get_master_release_tracklist":         self.discogs_handle.get_master_release_tracklist,
                    "discogs_get_collection_summary":               self.discogs_handle.get_collection_summary,
                    "discogs_get_wantlist_summary":                 self.discogs_handle.get_wantlist_summary,
                    "discogs_search_master_release_by_name":        self.discogs_handle.search_master_release_by_name,
                    "discogs_get_collection_unique_artists":        self.discogs_handle.get_collection_unique_artists,
                    "discogs_get_wantlist_unique_artists":          self.discogs_handle.get_wantlist_unique_artists
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
                    "musicbrainz_get_artist_details_and_works":     self.musicbrainz_.get_artist_details_and_works,
                    "musicbrainz_search_artists_by_name":           self.musicbrainz_.search_artists_by_name,
                    "musicbrainz_get_tracklist":                    self.musicbrainz_.get_tracklist,
                    "musicbrainz_search_release_group":             self.musicbrainz_.search_release_group,
                    "musicbrainz_search_by_raw_lucene":             self.musicbrainz_.search_by_raw_lucene
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
                    "post_bluesky":                 self.bluesky.post_bluesky,
                    "get_posts_needing_responses":  self.bluesky.get_posts_needing_responses,
                    "post_reply":                   self.bluesky.post_reply
                },
                "definitions": bluesky_tools,
                "room_types": ["bluesky_social"],
                "item_types": ["bluesky_social", "cellphone", "laptop"],
                "use_level": "inventory_only"
                # TODO: Think if we want an agent_information key for bluesky 
            }
            print("Bluesky tools added to unified definitions.")
        
        if self.searxng:
            self.tool_definitions["searxng"] = {
                "functions": {
                    "search_searxng":               self.searxng.search,
                    "query_searxng_website":        self.searxng.query_website,
                    "list_searxng_cache":           self.searxng.list_cache
                },
                "definitions": searxng_tools,
                "item_types": ["searxng", "laptop", "desktop_computer"],
                "use_level": "dual_use"
                # TODO: Think if we want an agent_information key for searxng 
            }
            print("SearxNG tools added to unified definitions.")


    def _add_lighthouse_tools(self):
        """Add lighthouse tool entries after self.lighthouse is initialized."""
        lh = self.lighthouse  # shorthand

        self.tool_definitions["iov_pressure"] = {
            "functions": {
                "iov_pump_air":                         lh.IOV_pump_air,
                "iov_tank_add_kerosene":                lh.IOV_kerosene_refill,
                "iov_pressure_room_status":             lh.lighthouse_manager.get_service_room_status,
                "iov_pressure_open_air_service_valve":  lh.open_air_service_valve,
                "iov_pressure_close_air_service_valve": lh.close_air_service_valve,
                "iov_pressure_open_main_valve":         lh.open_main_valve,
                "iov_pressure_close_main_valve":        lh.close_main_valve,
            },
            "definitions": iov_pressure_tools,
            "item_types": ["iov_pressure_system"],
            "use_level": "room_only",
            "display_information": lh.lighthouse_manager.get_service_room_status,
            "agent_information":   lh.lighthouse_manager.get_service_room_status,
        }
        self.tool_definitions["accessible_light_viewing_room"] = {
            "functions": {
                "peek_at_lamp_light_output": lh.accessible_room_light_check,
            },
            "definitions": accessible_light_viewing_room_tools,
            "room_types": ["accessible_light_viewing_room"],
            "display_information": lh.accessible_room_light_check,
            "agent_information":   lh.accessible_room_light_check,
        }
        self.tool_definitions["lamp"] = {
            "functions": {
                "lamp_ignite_vapor":        lh.lamp_ignite_vapor,
                "lamp_remove_mantle":       lh.remove_mantle,
                "lamp_place_spirit_pan":    lh.lamp_place_spirit_pan,
                "lamp_remove_spirit_pan":   lh.lamp_remove_spirit_pan,
                "lamp_install_mantle":      lh.lamp_light_install_mantle,
                "lamp_light_spirit_pan":    lh.lamp_light_spirit_pan,
                "lamp_open_control_valve":  lh.open_valve,
                "lamp_close_control_valve": lh.close_valve,
                "analyze_lamp_room":        lh.lighthouse_manager.get_lamp_status,
            },
            "definitions": lamp_tools,
            "item_types": ["iov_lamp_top"],
            "use_level": "room_only",
            "display_information": lh.lighthouse_manager.get_lamp_status,
            "agent_information":   lh.lighthouse_manager.get_lamp_status,
        }
        self.tool_definitions["spirit_pan"] = {
            "functions": {
                "refill_spirit_pan": lh.lamp_refill_spirit_pan,
            },
            "definitions": spirit_pan_tools,
            "item_types": ["iov_spirit_pan"],
            "use_level": "inventory_only",
        }
        self.tool_definitions["lantern_room"] = {
            "functions": {
                "get_lantern_room_interior_status": lh.get_lantern_room_interior_status,
                "clean_condensation":               lh.clean_condensation,
                "place_sheet":                      lh.place_sheet,
                "remove_sheet":                     lh.remove_sheet,
            },
            "definitions": lantern_room_tools,
            "room_types": ["lantern_room"],
            "display_information": lh.get_lantern_room_interior_status,
            "agent_information":   lh.get_lantern_room_interior_status,
        }
        self.tool_definitions["lantern_room_outdoor"] = {
            "functions": {
                "clean_outside_panes":      lh.clean_outside_panes,
                "get_panes_outdoor_status": lh.lighthouse_manager.lantern.get_outdoor_cleanliness,
            },
            "definitions": lantern_room_tools,
            "room_types": ["lighthouse_gallery"],
            "display_information": lh.lighthouse_manager.lantern.get_outdoor_cleanliness,
            "agent_information":   lh.lighthouse_manager.lantern.get_outdoor_cleanliness,
        }
        self.tool_definitions["clockwork_lens"] = {
            "functions": {
                "get_clockwork_status":     lh.lighthouse_manager.lantern.get_clockwork_status,
                "windup_clockwork":         lh.windup_clockwork,
                "oil_clockwork_mechanism":  lh.controller_oil_mechanism,
            },
            "definitions": clockwork_lens_tools,
            "item_types": ["clockwork_lens_apparatus"],
            "use_level": "room_only",
            "display_information": lh.lighthouse_manager.lantern.get_clockwork_status,
            "agent_information":   lh.lighthouse_manager.lantern.get_clockwork_status,
        }
        self.tool_definitions["fresnel_lens_interior"] = {
            "functions": {
                "fresnel_rotation_state": lh.lighthouse_manager.lantern.get_fresnel_rotation,
            },
            "definitions": fresnel_lens_tools,
            "item_types": ["fresnel_lens_apparatus", "fresnel_lens"],
            "use_level": "room_only",
            "room_types": ["fresnel_lens_interior"],
            "display_information": lh.lighthouse_manager.lantern.get_fresnel_rotation,
            "agent_information":   lh.lighthouse_manager.lantern.get_fresnel_rotation,
        }
        self.tool_definitions["spirit_source"] = {
            "functions": {
                "examine_spirit_source": lh.examine_spirit_source,
            },
            "definitions": spirit_source_tools,
            "item_types": ["spirit_source"],
            "use_level": "dual_use",
        }
        print("DEBUG: ToolRegistry: Lighthouse tools added.")