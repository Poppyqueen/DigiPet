# tool_availability.py
# Centralized tool availability logic.
# This module is intentionally stateless — it receives context via callables,
# so it has no imports from state_manager, services, or tool definitions.
# It can be tested in isolation.


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
        return any(
            item.get("id") == item_id
            for item in self.inventory_items
            if isinstance(item, dict)
        )

    def is_item_powered_on(self, item_id):
        return item_id not in self.powered_off_items

    def get_item(self, item_id):
        return self.all_items.get(item_id)

    def get_items_by_type(self, item_types, location=None):
        """
        Get items matching any of the given types.

        Args:
            item_types: List of item type strings to match
            location: 'inventory', 'room', or None for both
        """
        if location == "inventory":
            items_to_check = self.inventory_items
        elif location == "room":
            items_to_check = self.room_items
        else:
            items_to_check = list(self.all_items.values())

        matching = []
        for item in items_to_check:
            if not isinstance(item, dict):
                continue
            if any(itype in item.get("type", []) for itype in item_types):
                matching.append(item)
        return matching


class ToolAvailabilityChecker:
    """Determines whether a tool_config entry is available in the current context."""

    def __init__(self, item_context: ItemContext, current_room_types: list):
        self.item_context = item_context
        self.current_room_types = current_room_types

    def is_tool_available(self, tool_config: dict) -> bool:
        """
        Returns True if the tool should be available given the current context.

        Checks (in order):
          1. All function values must be non-None (i.e. service initialized correctly)
          2. 'always_available' use_level → always True
          3. Room type match OR item type match
        """
        functions = tool_config.get("functions", {})
        if any(func is None for func in functions.values()):
            return False

        if tool_config.get("use_level") == "always_available":
            return True

        return self._check_room_match(tool_config) or self._check_item_match(tool_config)

    def _check_room_match(self, tool_config: dict) -> bool:
        room_types = tool_config.get("room_types", [])
        if not room_types:
            return False
        return any(rt in self.current_room_types for rt in room_types)

    def _check_item_match(self, tool_config: dict) -> bool:
        item_types = tool_config.get("item_types", [])
        if not item_types:
            return False

        use_level = tool_config.get("use_level", "")
        ignore_power = tool_config.get("ignore_power_state", False)  # ← read flag

        if use_level == "inventory_only":
            candidates = self.item_context.get_items_by_type(item_types, location="inventory")
        elif use_level == "room_only":
            candidates = self.item_context.get_items_by_type(item_types, location="room")
        else:
            candidates = self.item_context.get_items_by_type(item_types)

        return any(
            (ignore_power or self.item_context.is_item_powered_on(item.get("id")))
            for item in candidates
            if item.get("id")
        )


class ItemToolMapper:
    """Maps item IDs to the tool function names they provide."""

    def __init__(self, tool_definitions: dict, item_context: ItemContext):
        self.tool_definitions = tool_definitions
        self.item_context = item_context

    def get_tools_for_item(self, item_id) -> list:
        """
        Returns all tool function names an item provides.
        Empty list if the item is powered off or not found.
        """
        item = self.item_context.get_item(item_id)
        if not item:
            return []
        if not self.item_context.is_item_powered_on(item_id):
            return []

        item_types = item.get("type", [])
        is_in_inventory = self.item_context.is_item_in_inventory(item_id)
        provided_tools = []

        for tool_key, tool_config in self.tool_definitions.items():
            tool_item_types = tool_config.get("item_types", [])
            if not tool_item_types:
                continue
            if not any(itype in tool_item_types for itype in item_types):
                continue

            use_level = tool_config.get("use_level", "")
            can_provide = False

            if use_level == "inventory_only":
                can_provide = is_in_inventory
            elif use_level == "room_only":
                can_provide = not is_in_inventory
            elif use_level in ["dual_use", "room_type"]:
                can_provide = True

            if can_provide:
                provided_tools.extend(tool_config.get("functions", {}).keys())

        return provided_tools

    def get_all_items_tool_map(self) -> dict:
        """Returns {item_id: [tool_names]} for every known item."""
        return {
            item_id: self.get_tools_for_item(item_id)
            for item_id in self.item_context.all_items.keys()
        }


# ---------------------------------------------------------------------------
# Factory — the main export for services that need availability queries
# ---------------------------------------------------------------------------

def make_toolset_checker(get_context_fn, tool_definitions: dict):
    """
    Returns a callable: (tool_key: str) -> bool

    Designed to be injected into services (e.g. LighthouseController) so they
    can query tool availability without holding a reference to FunctionBuilder
    or any state directly.

    Args:
        get_context_fn: Zero-arg callable that returns (room_types, ItemContext).
                        Typically FunctionBuilder._get_current_context.
        tool_definitions: The live tool_definitions dict from ToolRegistry.
                          Passed by reference, so mutations are reflected automatically.

    Example usage in FunctionBuilder.__init__:
        toolset_checker = make_toolset_checker(
            get_context_fn=self._get_current_context,
            tool_definitions=self.tool_definitions,
        )
        self.lighthouse = LighthouseController(
            self.state_manager,
            self._signal_callback,
            self.open_meteo,
            is_toolset_available=toolset_checker,
        )

    Example usage inside LighthouseController:
        if self.is_toolset_available and self.is_toolset_available("lantern_room"):
            ...
    """
    def check(tool_key: str) -> bool:
        tool_config = tool_definitions.get(tool_key)
        if not tool_config:
            return False
        current_room_types, item_context = get_context_fn()
        checker = ToolAvailabilityChecker(item_context, current_room_types)
        return checker.is_tool_available(tool_config)

    return check