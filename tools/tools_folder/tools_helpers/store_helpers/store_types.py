# store_types.py
# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models and type aliases for the store system.
#
# Import pattern mirrors TV channels / plant types:
#   - STORE_TYPE_DEFINITIONS  → store_type_definitions.py  (data you own)
#   - StoreType Literal        → built here from that data
#   - StoreEntryFields         → ContractMixin for items that participate in trade
#   - StoreEndpointFields      → ContractMixin for the store_endpoint item itself
#
# Usage in item_pydantic_models.py:
#   from tools.tools_folder.tools_helpers.store_helpers.store_types import (
#       StoreEntryFields,
#       StoreEndpointFields,
#   )
#   TYPE_FIELD_CONTRACTS: Dict[str, Type[ContractMixin]] = {
#       ...
#       "store_entry":    StoreEntryFields,
#       "store_endpoint": StoreEndpointFields,
#   }
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from enum import Enum
from typing import ClassVar, List

from pydantic import BaseModel, Field

# Local import — only the data dict, no circular risk
from tools.tools_folder.tools_helpers.store_helpers.store_type_definitions import (
    STORE_TYPE_DEFINITIONS,
    STORE_TYPES,
)

# ---------------------------------------------------------------------------
# StoreType Literal — built exactly like TVType / PlantType
# ---------------------------------------------------------------------------
# Import this wherever you need the validated string type.
#
#   from tools.tools_folder.tools_helpers.store_helpers.store_types import (
#       StoreType,
#       store_type_names,
#   )
#
# In item_pydantic_models.py register it with:
#   _store_type_keys = tuple(STORE_TYPES)
#   StoreType = Literal[_store_type_keys]

_store_type_keys = tuple(STORE_TYPES)

try:
    from typing import Literal
    StoreType = Literal[_store_type_keys]  # type: ignore[valid-type]
except Exception:
    StoreType = str  # fallback — should never trigger

store_type_names: str = ", ".join(_store_type_keys)

# Human-readable lookup for display strings in agent output
def get_store_type_display(store_type: str) -> str:
    """Returns the human-readable display name for a store type key."""
    return STORE_TYPE_DEFINITIONS.get(store_type, {}).get("display_name", store_type)

def get_store_type_description(store_type: str) -> str:
    """Returns the agent-facing description for a store type key."""
    return STORE_TYPE_DEFINITIONS.get(store_type, {}).get("description", "")


# ---------------------------------------------------------------------------
# TradeMode — replaces the confusing sellable: bool
# ---------------------------------------------------------------------------

class TradeMode(str, Enum):
    BUY_AND_SELL = "buy_and_sell"
    """The store stocks this item and will also buy it back from the agent."""

    BUY_ONLY = "buy_only"
    """The store stocks this item but will not buy it back (e.g. premium goods)."""

    SELL_ONLY = "sell_only"
    """The agent can sell this item to the store, but the store does not stock it
    (e.g. harvest produce — the store is a buyer, not a supplier)."""


# ---------------------------------------------------------------------------
# StoreEntryData — embedded in every item that participates in trade
# ---------------------------------------------------------------------------

class StoreEntryData(BaseModel):
    """
    Declared on any item blueprint that should be tradeable in a store.
    The store logic reads these fields directly — no path-based inference,
    no runtime stat calculations.
    """

    price: float = Field(
        gt=0,
        description=(
            "Base price of the item in in-game currency. "
            "For SELL_ONLY items this is still the reference value: "
            "the agent receives price * sell_discount when selling."
        ),
    )

    store_type: str = Field(
        description=(
            f"The store category (aisle) this item belongs to. "
            f"Must match one of the keys in STORE_TYPE_DEFINITIONS. "
            f"Available types: {store_type_names}. "
            f"A store_endpoint will only trade this item if its own "
            f"store_types list contains this value."
        ),
    )

    trade_mode: TradeMode = Field(
        default=TradeMode.BUY_AND_SELL,
        description=(
            "Controls which directions of trade are permitted. "
            "'buy_and_sell' — store stocks it and buys it back. "
            "'buy_only' — store stocks it, agent cannot sell back. "
            "'sell_only' — agent can sell to store, store does not stock it."
        ),
    )

    sell_discount: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction of price the agent receives when selling to the store. "
            "0.5 means the agent gets half the buy price. "
            "Ignored when trade_mode is 'buy_only'."
        ),
    )

    @property
    def sell_price(self) -> float:
        return round(self.price * self.sell_discount, 2)

    @property
    def is_buyable(self) -> bool:
        return self.trade_mode in (TradeMode.BUY_AND_SELL, TradeMode.BUY_ONLY)

    @property
    def is_sellable(self) -> bool:
        return self.trade_mode in (TradeMode.BUY_AND_SELL, TradeMode.SELL_ONLY)


# ---------------------------------------------------------------------------
# StoreEndpointFields — ContractMixin for the store_endpoint item type
# ---------------------------------------------------------------------------
# Import ContractMixin only inside item_pydantic_models.py to avoid circulars.
# This file re-exports the model so item_pydantic_models.py can import it cleanly.

class StoreEndpointData(BaseModel):
    """
    Runtime data for a store_endpoint item.
    Stored as 'store_endpoint_data' on the item blueprint.
    """

    store_name: str = Field(
        description="Display name of this store shown to the agent (e.g. 'Riverside Market').",
    )

    store_types: List[str] = Field(
        description=(
            "Which store categories (aisles) this endpoint carries. "
            f"Each value must be a key from STORE_TYPE_DEFINITIONS. "
            f"Available: {store_type_names}. "
            "The store controller will only surface items whose "
            "store_entry_data.store_type appears in this list."
        ),
    )

    welcome_message: str = Field(
        default="Welcome to the store.",
        description="Short flavour text shown to the agent when they open the store.",
    )