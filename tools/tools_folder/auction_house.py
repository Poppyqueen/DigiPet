# store_controller.py
# ─────────────────────────────────────────────────────────────────────────────
# Thin controller shell — owns the state_manager reference and all game-state
# I/O.  Pure store logic lives in store_logic.py (no state_manager there).
#
# Agent-facing methods follow the framework contract:
#   - Accept an endpoint_id (int) as the first argument
#   - Validate the store_endpoint item is accessible before doing anything
#   - Delegate computation to StoreLogic
#   - Write state back (currency adjustments, inventory mutations) via facade
#   - Return plain str for the agent
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

from tools.tools_folder.tools_helpers.store_helpers.store_logic import StoreLogic
from tools.tools_folder.tools_helpers.store_helpers.store_types import StoreEndpointData

STORE_ENDPOINT_TYPE = "store_endpoint"


class StoreController:
    def __init__(self, state_manager, signal_callback, item_store=None):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal_callback = signal_callback
        self.item_store = item_store
        self._logic = StoreLogic(item_store) if item_store else None

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_endpoint(self, endpoint_id: int) -> tuple[bool, StoreEndpointData | str]:
        """
        Validates that endpoint_id is an accessible store_endpoint item.
        Returns (True, StoreEndpointData) or (False, error_message).
        """
        result = self.state_manager.find_item(
            item_id=endpoint_id,
            required_type=STORE_ENDPOINT_TYPE,
            required_location="accessible",
        )
        if not result.success:
            return False, (
                f"Store endpoint {endpoint_id} is not accessible. "
                f"{result.error}"
            )
        
        if result.toggle_state is False:
            return False, f"Store endpoint {endpoint_id} is currently turned off."

        raw = result.item_data.get("store_endpoint_data")
        if not raw:
            return False, (
                f"Store endpoint {endpoint_id} has no configuration data. "
                "The item may be missing 'store_endpoint_data' in its blueprint."
            )

        try:
            endpoint_data = StoreEndpointData(**raw)
        except Exception as exc:
            return False, f"Store endpoint configuration is invalid: {exc}"

        return True, endpoint_data

    def _ensure_logic(self) -> bool:
        """Returns True if StoreLogic is ready (item_store was injected)."""
        return self._logic is not None

    # ─────────────────────────────────────────────────────────────────────────
    # Agent-facing tool methods
    # ─────────────────────────────────────────────────────────────────────────

    def open_store(self, endpoint_id: int) -> str:
        """
        Entry point — shows the welcome message, available categories, and
        a short item count per category for this store endpoint.
        """
        endpoint_id = int(endpoint_id)

        ok, result = self._get_endpoint(endpoint_id)
        if not ok:
            return result  # error string

        endpoint: StoreEndpointData = result

        if not self._ensure_logic():
            return "Store is unavailable (item catalogue not loaded)."

        parts = [
            f"--- {endpoint.store_name} ---",
            endpoint.welcome_message,
            "",
        ]

        category_summary = self._logic.get_category_summary(endpoint.store_types)
        if category_summary:
            parts.append("Available categories:")
            for line in category_summary:
                parts.append(f"  {line}")
        else:
            parts.append("This store currently has no items available.")

        currency_result = self.state_manager.get_currency()
        parts.append(f"\nYour balance: {currency_result.currency} currency.")

        return "\n".join(parts)

    def browse_category(self, endpoint_id: int, store_type: str, page: int = 0) -> str:
        """
        Lists items available to buy or sell in a specific category of this
        store endpoint, paginated (20 items per page, 0-indexed).
        """
        endpoint_id = int(endpoint_id)

        ok, result = self._get_endpoint(endpoint_id)
        if not ok:
            return result

        endpoint: StoreEndpointData = result

        if store_type not in endpoint.store_types:
            available = ", ".join(endpoint.store_types)
            return (
                f"Category '{store_type}' is not carried by {endpoint.store_name}. "
                f"Available categories: {available}."
            )

        if not self._ensure_logic():
            return "Store is unavailable (item catalogue not loaded)."

        return self._logic.format_category_listing(store_type, page)

    def lookup_item(self, endpoint_id: int, item_name: str) -> str:
        """
        Returns price, sell price, trade mode, and availability for a named item
        within this store endpoint. Supports fuzzy matching on the name.
        """
        endpoint_id = int(endpoint_id)

        ok, result = self._get_endpoint(endpoint_id)
        if not ok:
            return result

        endpoint: StoreEndpointData = result

        if not self._ensure_logic():
            return "Store is unavailable (item catalogue not loaded)."

        return self._logic.lookup_item(item_name, endpoint.store_types)

    def buy_item(self, endpoint_id: int, item_name: str, quantity: int = 1) -> str:
        """
        Purchase one or more units of an item from the store.
        Deducts currency and adds items to the agent's inventory.
        """
        endpoint_id = int(endpoint_id)
        quantity = int(quantity)

        if quantity <= 0:
            return "Quantity must be greater than 0."

        ok, result = self._get_endpoint(endpoint_id)
        if not ok:
            return result

        endpoint: StoreEndpointData = result

        if not self._ensure_logic():
            return "Store is unavailable (item catalogue not loaded)."

        # Resolve item through logic (handles fuzzy + category filtering)
        resolve_ok, resolve_result = self._logic.resolve_buyable_item(
            item_name, endpoint.store_types
        )
        if not resolve_ok:
            return resolve_result  # error / suggestion string

        item_blueprint, entry_data = resolve_result
        actual_name = item_blueprint["name"]
        total_cost = entry_data.price * quantity

        currency_result = self.state_manager.get_currency()
        if currency_result.currency < total_cost:
            return (
                f"Not enough currency to buy {quantity}x {actual_name}. "
                f"Required: {total_cost}, available: {currency_result.currency}."
            )

        parts = []
        for _ in range(quantity):
            create_result = self.state_manager.create_item(
                "inventory", None, self.item_store.get_item(actual_name)
            )
            if not create_result.success:
                return f"Purchase failed partway through: {create_result.error}"
            parts.append(create_result.message)

        self.state_manager.adjust_currency(-total_cost)
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/shop.png"})

        if quantity == 1:
            return f"Bought {actual_name} for {entry_data.price} currency. {' '.join(parts)}"
        return (
            f"Bought {quantity}x {actual_name} for {total_cost} currency total "
            f"({entry_data.price} each). {' '.join(parts)}"
        )

    def sell_item(self, endpoint_id: int, item_id: int, quantity: int = 1) -> str:
        """
        Sell one or more units of an inventory item to the store.
        Adds currency and removes items from the agent's inventory.
        """
        endpoint_id = int(endpoint_id)
        item_id = int(item_id)
        quantity = int(quantity)

        if quantity <= 0:
            return "Quantity must be greater than 0."

        ok, result = self._get_endpoint(endpoint_id)
        if not ok:
            return result

        endpoint: StoreEndpointData = result

        # Find the item in inventory
        item_result = self.state_manager.find_item(
            item_id=item_id,
            required_type=None,
            required_location="inventory",
        )
        if not item_result.success:
            return f"Could not find item {item_id} in inventory: {item_result.error}"

        item_data = item_result.item_data
        item_name = item_data.get("name", "Unknown")
        item_quantity = item_data.get("quantity", 1)

        if quantity > item_quantity:
            return (
                f"Cannot sell {quantity}x {item_name}. "
                f"Only {item_quantity} available in inventory."
            )

        if not self._ensure_logic():
            return "Store is unavailable (item catalogue not loaded)."

        # Validate item is sellable in this endpoint's categories
        resolve_ok, resolve_result = self._logic.resolve_sellable_item(
            item_name, endpoint.store_types
        )
        if not resolve_ok:
            return resolve_result

        _, entry_data = resolve_result
        total_earned = round(entry_data.sell_price * quantity, 2)

        remove_result = self.state_manager.remove_item(item_id, quantity=quantity)
        if not remove_result.success:
            return f"Failed to remove item from inventory: {remove_result.error}"

        self.state_manager.adjust_currency(total_earned)
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/shop.png"})

        if quantity == 1:
            return (
                f"Sold {item_name} for {entry_data.sell_price} currency. "
                f"{remove_result.message}"
            )
        return (
            f"Sold {quantity}x {item_name} for {total_earned} currency total "
            f"({entry_data.sell_price} each). {remove_result.message}"
        )

    def get_balance(self) -> str:
        """Returns the agent's current currency balance."""
        currency_result = self.state_manager.get_currency()
        return f"Your current balance is {currency_result.currency:.2f} currency."

    # ─────────────────────────────────────────────────────────────────────────
    # Perception
    # ─────────────────────────────────────────────────────────────────────────

    def agent_perceive(self) -> str:
        """
        Called at turn start. Surfaces any accessible store endpoints so the
        agent knows a store is nearby without needing to probe.
        """
        inventory = self.state_manager.get_inventory_state()
        all_items = inventory.inventory_items + inventory.room_items
        endpoints = [
            item for item in all_items
            if STORE_ENDPOINT_TYPE in item.item_data.get("type", [])
        ]
        if not endpoints:
            return ""

        parts = ["Nearby stores:"]
        for ep in endpoints:
            raw = ep.item_data.get("store_endpoint_data", {})
            name = raw.get("store_name", ep.name)
            ep_id = ep.item_id
            parts.append(f"  - {name} (use endpoint ID {ep_id} to browse or trade)")
        return "\n".join(parts)

    def gui_perceive(self) -> str:
        """GUI overlay — mirrors agent_perceive without ID numbers."""
        inventory = self.state_manager.get_inventory_state()
        all_items = inventory.inventory_items + inventory.room_items
        endpoints = [
            item for item in all_items
            if STORE_ENDPOINT_TYPE in item.item_data.get("type", [])
        ]
        if not endpoints:
            return ""

        names = []
        for ep in endpoints:
            raw = ep.item_data.get("store_endpoint_data", {})
            names.append(raw.get("store_name", ep.name))
        return "Store: " + ", ".join(names)