# store_logic.py
# ─────────────────────────────────────────────────────────────────────────────
# Pure store logic — no state_manager, no game-state I/O.
# Builds its catalog from item blueprints (item_store.get_items_by_type) and
# exposes query/display methods consumed by StoreController.
#
# Discovery: any item with "store_entry" in its type list and a valid
# "store_entry_data" dict is automatically included in the catalog.
# No path configuration needed.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Optional

from inventory_items.items_provider.items_scanner import FuzzyMatcher

from tools.tools_folder.tools_helpers.store_helpers.store_types import (
    StoreEntryData,
    TradeMode,
    get_store_type_display,
    get_store_type_description,
)
from tools.tools_folder.tools_helpers.store_helpers.store_type_definitions import (
    STORE_TYPE_DEFINITIONS,
)

STORE_ENTRY_TYPE = "store_entry"
PAGE_SIZE = 20


class StoreLogic:
    """
    Catalog builder and query engine for the store system.

    Lifecycle: constructed once at startup (or on demand), reads item blueprints
    via item_store, and holds the result in memory.  The controller never touches
    the catalog directly — it calls the public methods on this class.
    """

    def __init__(self, item_store):
        self.item_store = item_store

        # name → (blueprint dict, StoreEntryData)
        self._catalog: dict[str, tuple[dict, StoreEntryData]] = {}

        # case-insensitive lookup  lowercase → actual name
        self._lower_map: dict[str, str] = {}

        self._build_catalog()
        self._fuzzy = FuzzyMatcher(list(self._catalog.keys()))

    # ─────────────────────────────────────────────────────────────────────────
    # Catalog construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_catalog(self) -> None:
        """
        Reads every item of type 'store_entry' from the blueprint catalogue
        and indexes it by name.  Items with malformed store_entry_data are
        skipped with a warning rather than crashing startup.
        """
        blueprints: list[dict] = self.item_store.get_items_by_type(STORE_ENTRY_TYPE)

        for bp in blueprints:
            name = bp.get("name")
            raw_entry = bp.get("store_entry_data")

            if not name or not raw_entry:
                print(
                    f"[StoreLogic] Skipping blueprint '{name}': "
                    "missing name or store_entry_data."
                )
                continue

            try:
                entry_data = StoreEntryData(**raw_entry)
            except Exception as exc:
                print(
                    f"[StoreLogic] Skipping '{name}': "
                    f"invalid store_entry_data — {exc}"
                )
                continue

            self._catalog[name] = (bp, entry_data)
            self._lower_map[name.lower()] = name

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_name(self, item_name: str) -> Optional[str]:
        """Case-insensitive exact match. Returns actual name or None."""
        return self._lower_map.get(item_name.lower())

    def _items_for_endpoint(
        self, store_types: list[str]
    ) -> list[tuple[str, dict, StoreEntryData]]:
        """All catalog entries whose store_type is in the endpoint's list."""
        return [
            (name, bp, entry)
            for name, (bp, entry) in self._catalog.items()
            if entry.store_type in store_types
        ]

    def _items_for_category(
        self, store_type: str
    ) -> list[tuple[str, dict, StoreEntryData]]:
        return [
            (name, bp, entry)
            for name, (bp, entry) in self._catalog.items()
            if entry.store_type == store_type
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # Resolution (used by controller before buy/sell)
    # ─────────────────────────────────────────────────────────────────────────

    def resolve_buyable_item(
        self, item_name: str, store_types: list[str]
    ) -> tuple[bool, tuple[dict, StoreEntryData] | str]:
        """
        Finds a buyable item by name within the endpoint's categories.
        Returns (True, (blueprint, StoreEntryData)) or (False, error_string).
        """
        actual = self._resolve_name(item_name)

        if actual and actual in self._catalog:
            bp, entry = self._catalog[actual]
            if entry.store_type not in store_types:
                return False, (
                    f"'{actual}' is not sold at this store location."
                )
            if not entry.is_buyable:
                return False, (
                    f"'{actual}' is a sell-only item — the store does not stock it."
                )
            return True, (bp, entry)

        # Fuzzy fallback
        suggestions = self._fuzzy.find_suggestions(item_name)
        if suggestions:
            names = ", ".join(s.item_name for s in suggestions)
            return False, f"'{item_name}' not found. Did you mean: {names}?"
        return False, f"'{item_name}' not found in the store."

    def resolve_sellable_item(
        self, item_name: str, store_types: list[str]
    ) -> tuple[bool, tuple[dict, StoreEntryData] | str]:
        """
        Finds a sellable item by name within the endpoint's categories.
        Returns (True, (blueprint, StoreEntryData)) or (False, error_string).
        """
        actual = self._resolve_name(item_name)

        if actual and actual in self._catalog:
            bp, entry = self._catalog[actual]
            if entry.store_type not in store_types:
                return False, (
                    f"'{actual}' is not accepted at this store location."
                )
            if not entry.is_sellable:
                return False, (
                    f"'{actual}' is buy-only — this store does not purchase it."
                )
            return True, (bp, entry)

        suggestions = self._fuzzy.find_suggestions(item_name)
        if suggestions:
            names = ", ".join(s.item_name for s in suggestions)
            return False, (
                f"'{item_name}' is not accepted by this store. "
                f"Similar items that are: {names}."
            )
        return False, f"'{item_name}' is not accepted by this store."

    # ─────────────────────────────────────────────────────────────────────────
    # Display / formatting
    # ─────────────────────────────────────────────────────────────────────────

    def get_category_summary(self, store_types: list[str]) -> list[str]:
        """
        Returns one line per category the endpoint carries, with item counts.
        Shown in open_store().
        """
        lines = []
        for st in sorted(store_types):
            items = self._items_for_category(st)
            buyable = sum(1 for _, _, e in items if e.is_buyable)
            sellable = sum(1 for _, _, e in items if e.is_sellable)
            display = get_store_type_display(st)
            desc = get_store_type_description(st)
            lines.append(
                f"[{display}]  {buyable} for sale, {sellable} accepted — {desc}"
            )
        return lines

    def format_category_listing(
        self, store_type: str, page: int = 0
    ) -> str:
        """
        Paginated listing of all items in a category, showing buy/sell prices
        and trade direction.
        """
        items = sorted(self._items_for_category(store_type), key=lambda x: x[0])
        display_name = get_store_type_display(store_type)

        total = len(items)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = items[start:end]

        if not page_items:
            if total == 0:
                return f"No items are registered under '{display_name}'."
            return "No more items on this page."

        lines = [f"--- {display_name} (Page {page + 1} of {total_pages}) ---"]

        for name, _, entry in page_items:
            if entry.trade_mode == TradeMode.BUY_AND_SELL:
                lines.append(
                    f"  {name}  —  Buy {entry.price} | Sell {entry.sell_price} currency"
                )
            elif entry.trade_mode == TradeMode.BUY_ONLY:
                lines.append(
                    f"  {name}  —  Buy {entry.price} currency  (buy-only)"
                )
            else:  # SELL_ONLY
                lines.append(
                    f"  {name}  —  Sell {entry.sell_price} currency  (sell-only)"
                )

        remaining = total - end
        if remaining > 0:
            lines.append(
                f"\n--- {remaining} more item(s). "
                f"Call browse_category with page={page + 1} to continue. ---"
            )
        else:
            lines.append("--- End of category. ---")

        return "\n".join(lines)

    def lookup_item(self, item_name: str, store_types: list[str]) -> str:
        """
        Detailed single-item lookup. Respects endpoint category filtering
        but shows the result even for sell-only or buy-only items.
        """
        actual = self._resolve_name(item_name)

        if not actual or actual not in self._catalog:
            suggestions = self._fuzzy.find_suggestions(item_name)
            if suggestions:
                names = ", ".join(s.item_name for s in suggestions)
                return f"'{item_name}' not found. Similar items: {names}."
            return f"'{item_name}' not found in this store."

        bp, entry = self._catalog[actual]

        if entry.store_type not in store_types:
            return f"'{actual}' is not available at this store location."

        lines = [f"Item: {actual}"]
        lines.append(f"Category: {get_store_type_display(entry.store_type)}")
        lines.append(f"Trade mode: {entry.trade_mode.value}")

        if entry.is_buyable:
            lines.append(f"Buy price: {entry.price} currency")
        else:
            lines.append("Buy price: Not available (sell-only)")

        if entry.is_sellable:
            lines.append(f"Sell price: {entry.sell_price} currency")
        else:
            lines.append("Sell price: Not available (buy-only)")

        return "\n".join(lines)