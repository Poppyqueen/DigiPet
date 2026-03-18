# construct_tools.py
# more aptly named context builder, or construct_context, there is a method called that, but it is the idea that is the main thing here.
# FunctionBuilder — runtime mechanics only.
#
# Responsibilities:
#   - construct_map()      build the live function_map from tool_definitions
#   - construct_tools()    build the list of tool defs the LLM sees
#   - call_function()      dispatch a named tool call
#   - construct_context()  build the full LLM context string
#   - get_current_tools_info()  collect display/agent information from active tools
#
# What it does NOT own (delegated to ToolRegistry):
#   - Service instantiation (garden_manager, lighthouse, etc.)
#   - The tool_definitions dict
#   - Availability logic (ToolAvailabilityChecker, ItemContext, etc.)

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager #just for typing

import inspect
from utils.loc_datetime import datetime
from utils.time_manager import get_time_tag_from_now


from .tool_registry import ToolRegistry
from .tool_availability import (
    ItemContext,
    ToolAvailabilityChecker,
    ItemToolMapper,
)

from inventory_items.items_validation.item_pydantic_models import TYPE_FIELD_CONTRACTS

import random


class FunctionBuilder:

    def __init__(self, state_manager=None, signal=None, subdirectory=None,
                 memory_manager=None, config_manager=None, open_meteo=None):

        self.state_manager : InventoryHouseManager = state_manager
        self._signal_callback = signal
        self.open_meteo = open_meteo

        # ToolRegistry handles all service init and tool_definitions construction.
        # We pass _get_current_context as the live context provider so the
        # toolset_checker inside ToolRegistry always reads current state.
        print(f"DEBUG: FunctionBuilder: Initializing ToolRegistry")
        self.registry = ToolRegistry(
            state_manager=state_manager,
            signal=signal,
            subdirectory=subdirectory,
            memory_manager=memory_manager,
            config_manager=config_manager,
            open_meteo=open_meteo,
            get_context_fn=self._get_current_context,
        )

        # Convenient aliases — FunctionBuilder code reads these directly
        self.tool_definitions = self.registry.tool_definitions

        # Wire the self-referential function that couldn't be set in ToolRegistry
        # (examine_item needs get_item_details_with_tools which lives here)
        self.tool_definitions["base_functions"]["functions"]["examine_item"] = (
            self.get_item_details_with_tools
        )

        self.function_map = {}



    @classmethod
    async def create(
        cls,
        state_manager,
        signal       = None,
        subdirectory = None,
        memory_manager  = None,
        config_manager  = None,
        open_meteo      = None,
    ) -> "FunctionBuilder":
        """
        Async factory method. Replaces direct FunctionBuilder(...) calls
        when MCP support is needed.
 
        Builds the instance synchronously via __init__ (unchanged), then
        upgrades the registry to the async-initialised ToolRegistry so
        MCP tool entries are present before any tool map is built.
 
        The examine_item self-reference is re-wired after the upgrade
        because ToolRegistry.create() constructs a fresh tool_definitions
        dict that doesn't yet have it.
        """
        # Step 1 — normal sync init (builds registry via ToolRegistry.__init__)
        instance = cls(
            state_manager  = state_manager,
            signal         = signal,
            subdirectory   = subdirectory,
            memory_manager = memory_manager,
            config_manager = config_manager,
            open_meteo     = open_meteo,
        )
 
        # Step 2 — upgrade to async-initialised ToolRegistry (runs _connect_mcp)
        instance.registry = await ToolRegistry.create(
            state_manager  = state_manager,
            signal         = signal,
            subdirectory   = subdirectory,
            memory_manager = memory_manager,
            config_manager = config_manager,
            open_meteo     = open_meteo,
            get_context_fn = instance._get_current_context,
        )
 
        # Step 3 — re-point tool_definitions at the upgraded registry's dict
        instance.tool_definitions = instance.registry.tool_definitions
 
        # Step 4 — re-wire the self-referential examine_item function
        # (this was set in __init__ against the old registry; do it again)
        instance.tool_definitions["base_functions"]["functions"]["examine_item"] = (
            instance.get_item_details_with_tools
        )
 
        return instance
    # -----------------------------------------------------------------------
    # Context helpers
    # -----------------------------------------------------------------------

    def _get_current_context(self):
        """Returns (room_types, ItemContext) for the current state."""
        current_room_types = self.get_current_room_types()
        current_items_state = self.state_manager.get_inventory_state()

        items_in_room = [entry.item_data for entry in current_items_state.room_items]
        inventory_items = [entry.item_data for entry in current_items_state.inventory_items]
        
        item_context = ItemContext(inventory_items, items_in_room)
        return current_room_types, item_context

    def get_current_room_types(self):
        return self.state_manager.get_current_room_data().room_types

    def construct_map(self):
        """Rebuild function_map from tool_definitions given current context."""
        self.function_map = {}
        _, item_context = self._get_current_context()
        current_room_types, _ = self._get_current_context()
        checker = ToolAvailabilityChecker(item_context, current_room_types)

        # Static tool functions
        for tool_key, tool_config in self.tool_definitions.items():
            if checker.is_tool_available(tool_config):
                self.function_map.update(tool_config.get("functions", {}))


        print(f"DEBUG: function_map has {len(self.function_map)} functions")
        print(f"DEBUG: function_map keys: {list(self.function_map.keys())}")

    def construct_tools(self) -> list:
        """Return the list of tool definitions visible to the LLM."""
        self.construct_map()

        all_definitions = []
        seen_names = set()
        available_names = set(self.function_map.keys())

        current_room_types, item_context = self._get_current_context()
        checker = ToolAvailabilityChecker(item_context, current_room_types)

        # # Toggle tools first
        # for toggle_def in self._generate_power_toggle_tools(item_context):
        #     all_definitions.append(toggle_def)
        #     seen_names.add(toggle_def["name"])

        # Static tool definitions
        for tool_key, tool_config in self.tool_definitions.items():
            if not checker.is_tool_available(tool_config):
                continue
            for definition in tool_config.get("definitions", []):
                name = definition.get("name")
                if name and name not in seen_names and name in available_names:
                    all_definitions.append(definition)
                    seen_names.add(name)

        return all_definitions

    async def call_function(self, name, args):
        """Dispatch a named tool call with the given args."""
        self.construct_map()
        func = self.function_map.get(name)

        if func:
            try:
                print(f"Calling {name} with args: {args}")
                if not isinstance(args, dict):
                    print(f"Warning: args for {name} were not a dict.")
                    result = await func(args) if inspect.iscoroutinefunction(func) else func(args) if args else (await func() if inspect.iscoroutinefunction(func) else func())
                else:
                    result = await func(**args) if inspect.iscoroutinefunction(func) else func(**args)
                print(f"{name} returned: {result}")
                return result
            except TypeError as e:
                print(f"Argument mismatch calling {name}: {e}")
                return f"Error: Invalid arguments for '{name}'. Details: {e}"
            except Exception as e:
                print(f"Unexpected error in {name}: {e}")
                return f"Error executing '{name}'. Details: {e}"
        else:
            try:
                current_room_data = self.state_manager.get_current_room_data()
            except ValueError:
                return "Error: Could not find current room."
            room_name = current_room_data.name
            print(f"Warning: Unknown function '{name}' in room '{room_name}'")
            return f"Error: '{name}' is not available in {room_name} with your current inventory."

    # -----------------------------------------------------------------------
    # Context / display information
    # -----------------------------------------------------------------------

    def get_current_tools_info(self, flag="display") -> dict:
        """
        Collect display_information or agent_information from all currently
        active tool entries.

        Args:
            flag: "display" → uses display_information key
                  "agent"   → uses agent_information key
        """
        try:
            current_room_data = self.state_manager.get_current_room_data()
        except ValueError:
            return {"title": "Unknown Room", "body": "Could not retrieve room information."}

        room_name = current_room_data.name
        room_description = current_room_data.description

        function_id = "agent_information" if flag == "agent" else "display_information"
        body_parts = [] if flag == "agent" else ([room_description] if room_description else [])

        current_room_types, item_context = self._get_current_context()
        checker = ToolAvailabilityChecker(item_context, current_room_types)

        for tool_key, tool_config in self.tool_definitions.items():
            info_fn = tool_config.get(function_id)
            if not info_fn:
                continue
            if not checker.is_tool_available(tool_config):
                continue
            try:
                info = info_fn()
                if info:
                    display_name = tool_key.replace("_", " ").title()
                    body_parts.append(f"\n--- {display_name} Details ---\n{info}")
            except Exception as e:
                display_name = tool_key.replace("_", " ").title()
                body_parts.append(f"\n--- {display_name} Details ---\n(Error: {e})")

        body_content = "\n".join(p for p in body_parts if p)
        if not body_content:
            body_content = "No specific information available for this room."

        return {"title": room_name, "body": body_content}


    def get_current_tools_info_streaming(self, post_event_fn):
        """
        Calls post_event_fn immediately with room info,
        then appends each tool's display_information as it arrives.
        """
        try:
            current_room_data = self.state_manager.get_current_room_data()
        except ValueError:
            post_event_fn({"title": "Unknown Room", "body": "Could not retrieve room information."})
            return

        room_name = current_room_data.name
        room_description = current_room_data.description
        body_parts = [room_description] if room_description else []

        post_event_fn({"title": room_name, "body": "\n".join(p for p in body_parts if p)})

        current_room_types, item_context = self._get_current_context()
        checker = ToolAvailabilityChecker(item_context, current_room_types)

        for tool_key, tool_config in self.tool_definitions.items():
            info_fn = tool_config.get("display_information")
            if not info_fn or not checker.is_tool_available(tool_config):
                continue
            try:
                info = info_fn()
                if info:
                    display_name = tool_key.replace("_", " ").title()
                    body_parts.append(f"\n--- {display_name} Details ---\n{info}")
            except Exception as e:
                display_name = tool_key.replace("_", " ").title()
                body_parts.append(f"\n--- {display_name} Details ---\n(Error: {e})")
            
            post_event_fn({"title": room_name, "body": "\n".join(p for p in body_parts if p)})
        
    def construct_context(self) -> str:
        """Build the full context string injected into the LLM system prompt."""
        try:
            current_room_data = self.state_manager.get_current_room_data()
        except ValueError:
            return "Error: Could not find current room?????"


        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        room_description = current_room_data.description
        room_name = current_room_data.name

        inventory_state = self.state_manager.get_inventory_state()

        inv_string = inventory_state.inventory_summary
        room_string = inventory_state.room_summary

        possible_emotes = '\n'.join(self.state_manager.get_emotes_data().possible_emotes)

        
        context = [
            "MAIN SOURCE OF UNIVERSAL TRUTH:",
            "This source at any point seen, is the most up to date grounded state.",
            "#############",
            "Current State:",
            f"Current time: {now}, {get_time_tag_from_now()}",
            f"Currently, you are in: {room_name}\nRoom Description: {room_description}\n",
            "\n#############\n",
            self.state_manager.get_emotes_data().message,
            "\n#############\n",
            f"Possible emotes: {possible_emotes}",
            "\n#############\n",
            "In your inventory the current items are:",
            inv_string,
            "\n#############\n",
            "Available items in the room: ",
            room_string,
            "\n#############\n",
            "Current stats:",
            self.state_manager.get_stats().message,
            "\n#############\n",
            "Current perception information:",
            self.get_current_tools_info("agent")["body"],
        ]


        context.append("#############")
        context.append("END OF MAIN SOURCE OF UNIVERSAL TRUTH")

        return "\n".join(str(c) for c in context)

    # -----------------------------------------------------------------------
    # Item-tool relationship queries (public API, used by examine_item etc.)
    # -----------------------------------------------------------------------

    def get_all_item_tools_map(self) -> dict:
        _, item_context = self._get_current_context()
        mapper = ItemToolMapper(self.tool_definitions, item_context)
        return mapper.get_all_items_tool_map()

    def get_item_info_with_tools(self, item_id) -> dict:
        item_result = self.state_manager.find_item(item_id)
        if not item_result.success:
            return {"error": item_result.error}
        item_data = item_result.item_data
        _, item_context = self._get_current_context()
        mapper = ItemToolMapper(self.tool_definitions, item_context)
        return {
            "item_name":       item_data.get("name", "Unknown"),
            "has_power_switch": "toggle_state" in item_data,
            "is_powered_on":   item_context.is_item_powered_on(item_id),
            "provided_tools":  mapper.get_tools_for_item(item_id),
        }

    def get_item_details_with_tools(self, item_id) -> str:
        info = self.get_item_info_with_tools(item_id)
        if "error" in info:
            return info["error"]

        item_object = self.state_manager.find_item(item_id)
        if not item_object.success:
            return item_object.error
        data = item_object.item_data

        item_display = self.state_manager.inventory_service._format_item_for_display(data)
        descriptions = data.get("descriptions", [])

        output = f"{item_display}\n\n"
        if descriptions and isinstance(descriptions, list):
            output += random.choice(descriptions)
        else:
            output += "(No description available.)"

        # Collect type-specific examine sections
        type_sections = []
        for type_str in data.get("type", []):
            contract = TYPE_FIELD_CONTRACTS.get(type_str)
            if contract is None:
                continue
            section = contract.render_examine_section(data)
            if section:
                type_sections.append(section)

        if type_sections:
            output += "\n\n" + "\n".join(type_sections)

        # Tool info (power-gated)
        tools = info["provided_tools"]
        if tools:
            output += f"\n\nProvides tools: {', '.join(tools)}"
        elif info["has_power_switch"] and not info["is_powered_on"]:
            output += "\n\nTurn the power on to use this item's tools."

        return output