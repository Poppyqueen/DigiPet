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


# TODO: Invasive change, move use_level into the item definitions directly. Need to think about how that interacts with rooms.

import shutil

from tools.tools_folder.base_tools import BaseTools


from tools.tools_folder.alife_controller import ALifeController
from tools.tools_folder.plants_controller import GardenController
from tools.tools_folder.rooms_tools import main_tools_handle
from tools.tools_folder.images_lab import ImagesLab
from tools.tools_folder.dispenser_tools import DispenserTools
from tools.tools_folder.auction_house import StoreController
from tools.tools_folder.maze_controller import MazeController
from tools.tools_folder.lighthouse_controller import LighthouseController
from tools.tools_folder.items_toggle import ItemToggleTool

from tools.tools_folder.book_tools import BookTools
from tools.tools_folder.consumables import ConsumablesTools

from tools.tools_folder.tv_controller import TVController

from tools.tools_folder.outdoors_perception import OutdoorsPerception
from tools.tools_folder.comfort_affordances import ComfortAffordances
from tools.tools_folder.water_points import WaterInstallation

from tools.tools_folder.cooking_tool import CookingApparatus

from tools.tools_folder.wikipedia_controller import WikipediaController

from utils.ai_items_crafter import ItemsCrafter




from .my_tools import (
    base_tools,
    book_tools,
    #computer_room_tools,
    lab_room_tools,
    youtube_playlister_tools,
    discogs_tools,
    musicbrainz_tools,
    bluesky_tools,
    art_book_tools,
    #laptop_tools,
    dispenser_tools,
    maze_tools,
    searxng_tools,
    iov_pressure_tools,
    lamp_tools,
    spirit_pan_tools,
    clockwork_lens_tools,
    lantern_room_tools,
    fresnel_lens_tools,
    accessible_light_viewing_room_tools,
    toggle_item_power_tool,

    fenestration_apertures_tools,
    tv_tools,
    creating_books_tools,
    comfort_tools,
    water_source_tools,
    prepare_food_tools,
    plants_tools,
    endpoints_tools,
    store_tools
)

from .tool_availability import make_toolset_checker


from inventory_items.items_validation.item_pydantic_models import get_base_item_types, get_mcp_item_types

from inventory_items.items_provider.item_store import ItemStore

import sys
import os

venv_bin = os.path.dirname(sys.executable)


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
        self._subdirectory = subdirectory
        self._signal = signal
        self._get_context = get_context_fn

        crafter_config_model = config_manager.get_config("AI","cook_model")
        crafter_selected_config_client = config_manager.get_config("AI","cook_provider")


        # agent config was already cloned by BaseChatbot — just read it
        agent_config_path = os.path.join(subdirectory, 'mcp_config.json')
        _base_types = get_base_item_types()
        _mcp_types  = get_mcp_item_types(config_path=agent_config_path)
        _agent_valid_types = _base_types + [t for t in _mcp_types if t not in _base_types]

        self.item_store = ItemStore(valid_types=_agent_valid_types)

        self.items_crafter = ItemsCrafter(
            provider=crafter_selected_config_client,
            model=crafter_config_model,
            valid_types=_agent_valid_types,
        )
        # --- Feature flags ---
        self.youtube_enabled       = config_manager.get_config("Tools", "enable_youtube")
        self.discogs_enabled       = config_manager.get_config("Tools", "enable_discogs")
        self.musicbrainz_enabled   = config_manager.get_config("Tools", "enable_musicbrainz")
        self.bluesky_enabled       = config_manager.get_config("Tools", "enable_bluesky")
        self.wikipedia_enabled     = config_manager.get_config("Tools", "enable_wikipedia")
        self.searxng_enabled       = config_manager.get_config("Tools", "enable_searxng")

        # self.xeno_canto_enabled = True # config_manager.get_config("OutdoorsPerception", "enable_xeno_canto") # TODO: Add config screen or toggle, this flag does nothing right now

        # self.lat  = config_manager.get_config("location", "latitude") # TODO: Cloned code from BaseChatbot, fix this, share it somehow, original in 'ai_managers/agents/abstract_agent.py'
        # self.long = config_manager.get_config("location", "longitude")
        # _env_lat  = os.getenv("LATITUDE") 
        # _env_long = os.getenv("LONGITUDE")
        # if not self.lat or not self.long:
        #     self.lat, self.long  = _env_lat, _env_long

        # self.xeno_canto = None
        # #if self.xeno_canto_enabled:
        # canto_key = os.getenv("XENO_CANTO_API_KEY") # Change this for a toggle on config GUI screen
        # if canto_key:
        #     self.xeno_canto = XenoCantoLoc(self.lat, self.long, api_key=canto_key)



        # =================================================================
        # Phase 1 — services with no availability dependency
        # =================================================================
        self.base_tools     = BaseTools(state_manager)
        self.room_tools     = main_tools_handle(state_manager, signal, memory_manager, config_manager, open_meteo)
        self.garden_manager = GardenController(state_manager, signal, open_meteo)
        self.images_lab     = ImagesLab(state_manager, signal)
        self.dispenser_tools = DispenserTools(state_manager, signal, self.item_store)
        self.store_tools = StoreController(state_manager, signal, item_store=self.item_store)
        self.maze           = MazeController(state_manager, signal)
        self.A_Life         = ALifeController(state_manager=state_manager, signal=signal, base_path=subdirectory)
        self.book_tools     = BookTools(state_manager, signal)
        self.consumables_tools = ConsumablesTools(state_manager, signal)

        self.tv_controller     = TVController(state_manager, signal, config_manager)
        self.outdoors_perception = OutdoorsPerception(state_manager, signal, open_meteo, config_manager)
        self.comfort = ComfortAffordances(state_manager, signal, memory_manager, self.items_crafter, self.item_store)

        self.water_points = WaterInstallation(state_manager, signal)

        self.cook = CookingApparatus(state_manager, signal, config_manager) # Needs config manager to select AI model for runtime generation

        self.item_toggle    = ItemToggleTool(state_manager, signal)

        self.wikipedia_controller = WikipediaController(state_manager, signal, memory_manager)


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
            item_store=self.item_store
        )
        self._add_lighthouse_tools()




    @classmethod
    def create(cls, state_manager, signal, subdirectory, memory_manager,
            config_manager, open_meteo, get_context_fn) -> "ToolRegistry":
        instance = cls(
            state_manager=state_manager, signal=signal,
            subdirectory=subdirectory, memory_manager=memory_manager,
            config_manager=config_manager, open_meteo=open_meteo,
            get_context_fn=get_context_fn,
        )
        instance._connect_mcp()
        return instance

    # ------------------------------------------------------------------
    # _connect_mcp  — two-phase loader
    # ------------------------------------------------------------------
        
    def _connect_mcp(self) -> None:
        from pygame_runtime.async_loop import mcp_loop

        from .mcp_registry import MCPRegistry, load_json_configs, MCP_AVAILABLE
        if not MCP_AVAILABLE:
            self.mcp_registry = None
            return
        
        agent_config_path = os.path.join(self._subdirectory, 'mcp_config.json')
        server_cfgs, affordance_cfgs = load_json_configs(config_path=agent_config_path)

        if not server_cfgs:
            self.mcp_registry = None
            return

        self.mcp_registry = MCPRegistry()

        for server_cfg in server_cfgs:
            try:
                mcp_loop.run_sync(self.mcp_registry.connect_server(server_cfg), timeout=30)
            except Exception as exc:
                print(f"[MCP] WARNING: Could not connect to '{server_cfg.server_key}': {exc}")

        for affordance in affordance_cfgs:
            if not self.mcp_registry.is_connected(affordance.server_key):
                print(f"[MCP] Skipping affordance '{affordance.registry_key}' — "
                    f"server '{affordance.server_key}' not connected.")
                continue
            try:
                entry = self.mcp_registry.build_affordance_entry(affordance)
                self.tool_definitions[affordance.registry_key] = entry
                print(f"[MCP] Affordance '{affordance.registry_key}' registered.")
            except Exception as exc:
                print(f"[MCP] WARNING: Failed to build affordance '{affordance.registry_key}': {exc}")
    # ------------------------------------------------------------------
    # Phase 1 helpers
    # ------------------------------------------------------------------


    def _init_optional_services(self, state_manager, signal): # This is conditional importing, not adding wikipedia here even tho there is a config flag for it as imports are only requests, no specific library, conditional runtime still works thanks to _add_conditional_tools
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
                from tools.tools_folder.bluesky_controller import BlueskyTools
                self.bluesky = BlueskyTools(state_manager, signal, self.images_lab)
                print("BlueskyTools instance created.")
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
                    "list_items_in_current_room":   self.base_tools.list_items_in_current_room,
                    "list_items_in_inventory":      self.base_tools.list_items_in_inventory,
                    "set_current_emote":            self.base_tools.set_current_emote,
                    "move_to_room":                 state_manager.set_current_room,
                    "list_all_rooms":               self.base_tools.get_all_rooms,
                    "pick_up_item":                 self.base_tools.pick_up_item,
                    "examine_item":                 None,  # set by FunctionBuilder (needs self ref)
                    "drop_item":                    self.base_tools.drop_item,
                    #"add_item_description":         self.base_tools.add_item_description, # Sometimes the AI will use this to replace actions or behaviors instead with just making notes into items, that's why it has been removed.
                    "emit_inner_thought":           self.base_tools.emit_inner_thought
                },
                "definitions": base_tools,
                "use_level": "always_available",
            },
            "consumables_tools": {
                "functions": {"consume_item": self.consumables_tools.consume_item},
                "definitions": base_tools,
                "use_level": "inventory_only",
                "item_types": ["consumable"], 
                "display_information": self.consumables_tools.perceive_consumables, 
                "agent_information": self.consumables_tools.perceive_consumables, #
            },
            "ALIFE_research": { # TODO: Update this, create an agent information method that holds the information on the current sim alongside the current tick, maybe do not include the whole state, but metadata
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
                # "room_types": ["ALIFE_research"],
                "item_types": ["ALIFE_interface"],
                "use_level": "dual_use",
                "display_information": al.display_information if al else None,
                # agent_information intentionally omitted — contains restricted info (see TODO in original)
            },
            "dispenser": { # This is mostly fine, however, it is owns candy bags, maybe make candy bags use consume uses left?
                "functions": { # Not sure what to do about this, optimally, this should be a general container? not sure
                    "dispense_candy": self.dispenser_tools.dispense_candy,
                    "refill_dispenser": self.dispenser_tools.refill_dispenser,
                    #"examine_dispenser": self.dispenser_tools.examine_dispenser
                },
                "definitions": dispenser_tools,
                "item_types": ["dispenser"],
                "use_level": "room_only"
            },


    # REFACTOR ZONE:
            "cook_technology": { # It is clean, now what?, if touching this first think about what to do with the consumables
                "functions": {"prepare_food": self.cook.prepare_food},
                "definitions": prepare_food_tools,
                "item_types": ["culinary_equipment"],
                "use_level": "dual_use"
            },

            "tv": { # rename this, could be a TV or a radio, specifically a one to many and channel/station based information reciever device.
                "functions": { # Also add more TV types
                    "watch_tv": self.tv_controller.watch_tv,
                    "browse_channels": self.tv_controller.browse_channels,
                    "change_channel": self.tv_controller.change_channel,
                },
                "definitions": tv_tools,
                "item_types": ["tv"],
                "use_level": "dual_use",
                "display_information": self.tv_controller.get_current_accessible_tv_gui, # non-blocking
                "agent_information": self.tv_controller.get_current_accessible_tv_agent, # blocking
            },


    # New, refactored affordances to be more general:
            "store": {
                "functions": { 
                    "browse_store_category": self.store_tools.browse_category,
                    "store_lookup_item": self.store_tools.lookup_item,
                    "store_buy_item": self.store_tools.buy_item,
                    "store_sell_item": self.store_tools.sell_item,
                    "store_get_balance": self.store_tools.get_balance,
                    "store_hello": self.store_tools.open_store
                },
                "definitions": store_tools,
                "item_types": ["store_endpoint"],
                "use_level": "dual_use"
            },
            "book": {
                "functions": {
                    "list_chapters":        self.book_tools.list_book_chapters, # Now general examine returns a list of the contents, but leaving this function here, maybe remove later?
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
                    "delete_image": self.images_lab.delete_image,
                    "read_image_archive":     self.images_lab.read_image_archive,
                },
                "definitions": art_book_tools,
                "item_types": ["drawing_area"],
                "use_level": "inventory_only",
            },

            "book_creation": { # Bookbinding and other methods
                "functions": {"create_book_item": self.book_tools.create_book_item},
                "definitions": creating_books_tools,
                #"room_types": ["library"],
                "item_types": ["bookmaking_implements"],
                "use_level": "dual_use"
                # No perception tools
            },
            "nook_item": { # Beds, tents, sofas and other places to sleep on
                "functions": {
                    "sleep_on_item":        self.comfort.sleep_on_item,
                },
                "definitions": comfort_tools,
                "item_types": ["sleepable_spot"],
                "use_level": "room_only", # can't sleep while... holding the sleeping bag
            },
            "cranny": { # these items, usually furniture allow you to reach under them sometimes revealing forgotten rewards!
                "functions": { # TODO: Update this to include cranny type in this item object definition, handle returning different types of gleanings based on different types
                    "reach_into_item_crevice": self.comfort.reach_into_item_crevice,
                },
                "definitions": comfort_tools,
                "item_types": ["cranny_host"],
                "use_level": "room_only",
            },

            "seat": { # seatables!
                "functions": {"take_a_seat": self.comfort.take_a_seat},
                "definitions": comfort_tools,
                "item_types": ["seatable"],
                "use_level": "room_only",
            },

            "soft_goods": { # You would want to hug these items
                "functions": {
                    "hug_comfort_object":           self.comfort.hug_comfort_object # maybe if the agent carries an specific item for an extended period of time, its type gets 'comfort_objects'
                },
                "definitions": comfort_tools,
                "item_types": ["comfort_object"],
                "use_level": "dual_use",
                #"room_types": ["bedroom"] # Left in for reference
            },
            "meditation": { # this could be a base tool?... instead maybe for an item? a yoga mat?
                "functions": {"meditate": self.comfort.meditate},
                "definitions": comfort_tools,
                #"room_types": [""], # This should be a base tool? Not sure. Maybe the tool tracks a log of how many times has the agent meditated, and when the count reaches a certain number, meditation is now a base tool- That's messy to implement. Maybe add, a way to edit agent's base affordances in the GUI creation screen of it? Maybe an option to add 1 or 2 select extra functions to base
                "item_types": ["meditation_aid"], # we are not good at it
                "use_level": "dual_use",
                "display_information": self.comfort.get_accessible_meditative_elements,
                "agent_information": self.comfort.get_accessible_meditative_elements,
                },


            "water_feature": { 
                "functions": {
                    "drink_from_water_point": self.water_points.drink_from_water_point,
                    "wash_self_water_feature":   self.water_points.wash_self_water_feature, # It's back!
                },
                "definitions": water_source_tools,
                "item_types": ["water_point"],
                "use_level": "dual_use"
            },
            # Gardening
            "general_planting": {
                "functions": {
                    "plant_seed":                       self.garden_manager.plant_seed,
                    "check_plant":                      self.garden_manager.check_plant, # Detailed plant by plant state.
                    "harvest_plant":                    self.garden_manager.harvest_plant,
                    "water_plant":                      self.garden_manager.water_plant,
                    "remove_plant":                     self.garden_manager.remove_plant
                },
                "definitions": plants_tools,
                "room_types": ["open_soil_zone"], 
                "use_level": "dual_use",
                "item_types": ["planter_pot"], 
            },
            "planting_garden": {
                "definitions": plants_tools,
                "room_types": ["open_soil_zone"],
                "display_information":  self.garden_manager.get_garden_room_gui, 
                "agent_information":    self.garden_manager.get_garden_room_gui, 
            },
            "pot_specific_plant_care": { 
                "functions": {
                    "inspect_pot": self.garden_manager.inspect_pot 
                },
                "definitions": plants_tools,
                "item_types": ["planter_pot"],
                "use_level": "dual_use",
                "display_information": self.garden_manager.get_accessible_pots_gui,
                "agent_information": self.garden_manager.get_accessible_pots_gui,
            },

            "maze": { 
                "functions": {
                    "Maze-create_maze":        self.maze.create_maze,
                    "Maze-observe_environment": self.maze.get_maze_state,
                    "Maze-move":               self.maze.maze_move,
                },
                "definitions": maze_tools,
                "item_types": ["maze_interface"],
                "use_level": "dual_use",
                "display_information": self.maze.percieve_data,
                "agent_information": self.maze.percieve_data,
            },

            "fenestration_apertures": { # Windows, Light wells, portholes
                "definitions": fenestration_apertures_tools,
                "item_types": ["fenestration_aperture"],
                "use_level": "room_only",
                "functions": {
                    "look_outdoors_through_fenestration": self.outdoors_perception.look_through_aperture
                },
                "display_information": self.outdoors_perception.window_perception,
                "agent_information": self.outdoors_perception.window_perception,
            },
            # ----------------------------------------------------------------
            # Information-only entries (no functions key — availability-gated
            # agent_information sources, not action tools)
            # ----------------------------------------------------------------
            "outdoors": {
                # No "functions" key — this entry exists purely to gate access
                # to agent_information based on room type. The ToolAvailabilityChecker
                # will treat missing/empty functions as available (no None check needed)
                # because is_tool_available only None-checks values that exist.
                #"definitions": garden_room_tools,
                "room_types": ["outdoors_area"], # soft link with garden manager, it is looking for room with this type and watering plants that are in them
                "display_information": self.outdoors_perception.gui_outdoors_perception,
                "agent_information": self.outdoors_perception.outdoors_perception,
            },
            # ----------------------------------------------------------------
            # Special toggle, internal, do not touch!
            # ----------------------------------------------------------------
            "item_toggle": { # Power toggle special key, ignores power state. Any item that has this key will be managed by a toggle to actiavte its functions.
                "functions": {
                    "toggle_item": self.item_toggle.toggle_item_power_auto,
                },
                "definitions": [toggle_item_power_tool],
                "item_types": ["toggleable"],
                "use_level": "dual_use",
                "display_information": self.item_toggle.get_access_toggles,
                "agent_information": self.item_toggle.get_access_toggles, 
                "ignore_power_state": True
            }
        }

    def _add_conditional_tools(self, state_manager): # State manager not used for these tools, but kept for consistency
        """Append optional tool entries after the base dict is built."""

        if self.wikipedia_enabled:
            self.tool_definitions["wikipedia"] = {
                "functions": {
                    # Search — returns titles + snippets, lightweight
                    "search_wikipedia_articles":
                        self.wikipedia_controller.search_wikipedia_articles,
                    # Summary — intro section only, no memory danger
                    "get_wikipedia_article_summary":
                        self.wikipedia_controller.get_wikipedia_article_summary,
                    # Full content — returns and counts the article's full text, if too large instead returns a warning that can be bypassed with an optional parameter.
                    "get_wikipedia_article_content":
                        self.wikipedia_controller.get_wikipedia_article_content,
                },
                "definitions": endpoints_tools,
                "item_types": ["wikipedia_endpoint"],
                "use_level": "dual_use",
                # display_information → full content, for the UI ONLY, never feed to agent
                "display_information": self.wikipedia_controller.display_information,
                # agent_information → metadata only (last query + results + fetch status)
                # NO article content; safe to include in agent context
                "agent_information": self.wikipedia_controller.agent_information,
            }

            print("Wikipedia tools added.")

        if self.youtube:
            self.tool_definitions["youtube_playlists"] = {
                "functions": {
                    "youtube_search_video":             self.youtube.search_video,
                    "youtube_create_playlist":          self.youtube.create_playlist,
                    "youtube_add_video_to_playlist":    self.youtube.add_video_to_playlist,
                    #"open_youtube_item":        self.youtube.open_youtube_item,
                    # Add functions to examine an existing playlist, get its details, etc. Maybe playlists can be item based? 
                },
                "definitions": youtube_playlister_tools,
                #"room_types": ["youtube_playlists", "music_room"],
                "item_types": ["youtube_playlists_endpoint"], # Only 'youtube_playlists'
                "display_information": self.youtube.get_summary,
                "use_level": "dual_use",
            }
            print("YouTube tools added.")


        if self.discogs_handle:
            self.tool_definitions["discogs"] = { 
                "functions": {
                    "discogs_search_artist_by_name":                self.discogs_handle.search_artist_by_name,
                    "discogs_get_artist_discography":               self.discogs_handle.get_artist_discography,
                    "discogs_search_master_by_title":               self.discogs_handle.search_master_by_title,
                    "discogs_get_master_tracklist":                 self.discogs_handle.get_master_tracklist,

                    "discogs_get_wantlist_summary":                 self.discogs_handle.get_wantlist_summary,
                    "discogs_get_wantlist_unique_artists":          self.discogs_handle.get_wantlist_unique_artists,

                    "discogs_get_collection_unique_artists":        self.discogs_handle.get_collection_unique_artists,
                    "discogs_get_collection_summary":               self.discogs_handle.get_collection_summary,

                },
                "definitions": discogs_tools,
                "item_types": ["discogs_endpoint"], # Only 'discogs_endpoint', a computer or anything could be discogs endpoint
                "use_level": "dual_use"
            }
            print("Discogs tools added to unified definitions.")

        if self.musicbrainz_:
            self.tool_definitions["musicbrainz"] = { # Does this need anything?
                "functions": {
                    "musicbrainz_get_artist_details_and_works":     self.musicbrainz_.get_artist_details_and_works,
                    "musicbrainz_search_artists_by_name":           self.musicbrainz_.search_artists_by_name,
                    "musicbrainz_get_tracklist":                    self.musicbrainz_.get_tracklist,
                    "musicbrainz_search_release_group":             self.musicbrainz_.search_release_group,
                    "musicbrainz_search_by_raw_lucene":             self.musicbrainz_.search_by_raw_lucene
                },
                "definitions": musicbrainz_tools,
                # "room_types": ["musicbrainz", "music_room"],
                "item_types": ["musicbrainz_endpoint"],
                "use_level": "dual_use"
            }
            print("MusicBrainz tools added to unified definitions.")

        if self.bluesky:
            self.tool_definitions["bluesky_social"] = {
                "functions": {
                    "get_notifications" : self.bluesky.get_notifications,
                    "mark_notifications_seen": self.bluesky.mark_notifications_seen,
                    "list_feeds": self.bluesky.list_feeds,
                    "get_feed": self.bluesky.get_feed,
                    "get_author_posts": self.bluesky.get_author_posts,
                    "get_thread": self.bluesky.get_thread,
                    "get_account_summary": self.bluesky.get_account_summary,
                    "get_posts_needing_responses": self.bluesky.get_posts_needing_responses,
                    "post": self.bluesky.post,
                    "post_with_image": self.bluesky.post_with_image,
                    "respond_to_post": self.bluesky.respond_to_post
                },
                "definitions": bluesky_tools,
                "item_types": ["bluesky_social_endpoint"],
                "use_level": "dual_use",
                # "display_information": self.bluesky.get_notifications, 
                # "agent_information": self.bluesky.get_notifications # Think if we want this here
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
                "item_types": ["searxng_endpoint"],
                "use_level": "dual_use"
                # TODO: Think if we want an agent_information key for searxng, it could return a list of the latest search and their results. 
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
        self.tool_definitions["accessible_light_viewing_room"] = { # This should not be a room type, maybe use the lighthouse manager to look for any existing light source, the lamp, and make it a perception tool... wait, that requires a context... 
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
        # self.tool_definitions["spirit_source"] = {
        #     "functions": {
        #         #"examine_spirit_source": lh.examine_spirit_source,
        #     },
        #     "definitions": spirit_source_tools,
        #     "item_types": ["spirit_source"],
        #     "use_level": "dual_use",
        # }
        print("DEBUG: ToolRegistry: Lighthouse tools added.")
