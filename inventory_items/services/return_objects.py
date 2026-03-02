# return_objects.py

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, model_validator

from utils.time_manager import get_time_tag_from_now
# ============================================================
# ADD TO: inventory_items/services/return_objects.py
# Place after the existing ItemLookupResult class definition.
# ============================================================



class InventoryItemEntry(BaseModel):
    """
    A single validated, located item as returned by inventory state queries.

    This is NOT an operation result — it carries no success/error semantics.
    Every instance in a list is guaranteed to have passed validation.
    Location context is embedded so callers never need to know which list
    an entry came from.

    Fields
    ------
    item_id         : Integer ID of the item.
    name            : Display name of the item.
    display_string  : Pre-formatted string ready for GUI, signals, and agent
                      responses. Example: "Apple (ID:000042) x3"
    item_data       : Full validated raw item dict. Use this for tool logic,
                      AI agent reasoning, or any attribute access.
    location        : "inventory" or "room".
    location_id     : Room ID when location == "room", else None.
    location_name   : Room name when location == "room", else None.
    """

    item_id: int
    name: str
    display_string: str
    item_data: dict
    location: Literal["inventory", "room"]
    location_id: int | None = None
    location_name: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _check_room_fields_consistent(self) -> "InventoryItemEntry":
        if self.location == "room":
            assert self.location_id is not None, (
                "InventoryItemEntry with location='room' must have location_id."
            )
        if self.location == "inventory":
            assert self.location_id is None, (
                "InventoryItemEntry with location='inventory' must not have location_id."
            )
        return self


class InventoryStateResult(BaseModel):
    """
    The single return type for full inventory state queries.

    Captures both the player inventory and the current room's item list in
    one fetch. All items have been validated — invalid raw dicts are silently
    dropped during construction.

    Pre-computed derived views mean callers never need to re-format data:

    - For GUI / signals      → inventory_display_strings, room_display_strings
    - For AI agent strings   → inventory_summary, room_summary
    - For tool / logic use   → inventory_items, room_items (typed entries)
    - For raw dict access    → entry.item_data on any InventoryItemEntry

    Fields
    ------
    inventory_items             : Validated inventory entries.
    room_items                  : Validated room entries for the current room.
    room_id                     : ID of the current room at query time.
    room_name                   : Name of the current room at query time.
    inventory_display_strings   : Pre-formatted display strings for each
                                  inventory item. Ready for prepare_inventory_item_data().
    room_display_strings        : Pre-formatted display strings for each
                                  room item. Ready for prepare_inventory_item_data().
    inventory_summary           : Human-readable sentence for agent/tool responses.
                                  E.g. "Items in your inventory: Apple (ID:000042)"
                                  or "Your inventory is empty."
    room_summary                : Human-readable sentence for agent/tool responses.
                                  E.g. "Items in the Kitchen (ID:000001): Knife (ID:000007)"
                                  or "There are no items in the Kitchen (ID:000001)."
    """

    inventory_items: list[InventoryItemEntry] = []
    room_items: list[InventoryItemEntry] = []
    room_id: int
    room_name: str

    # Derived views — always populated, computed by the service before construction.
    inventory_display_strings: list[str] = []
    room_display_strings: list[str] = []
    inventory_summary: str = ""
    room_summary: str = ""

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _check_derived_views_consistent(self) -> "InventoryStateResult":
        assert len(self.inventory_display_strings) == len(self.inventory_items), (
            "inventory_display_strings length must match inventory_items length."
        )
        assert len(self.room_display_strings) == len(self.room_items), (
            "room_display_strings length must match room_items length."
        )
        assert self.inventory_summary != "", (
            "inventory_summary must always be populated (use empty message, not empty string)."
        )
        assert self.room_summary != "", (
            "room_summary must always be populated (use empty message, not empty string)."
        )
        return self

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        inventory_items: list[InventoryItemEntry],
        room_items: list[InventoryItemEntry],
        room_id: int,
        room_name: str,
        room_display: str,  # formatted "Room Name (ID:000001)" string
    ) -> "InventoryStateResult":
        """
        Preferred constructor. Derives all display strings and summaries
        from the item lists automatically.

        Parameters
        ----------
        inventory_items : Validated InventoryItemEntry list for inventory.
        room_items      : Validated InventoryItemEntry list for current room.
        room_id         : Current room ID.
        room_name       : Current room name (plain, for the model field).
        room_display    : Formatted room string e.g. "Kitchen (ID:000001)"
                          used inside the room_summary sentence.
        """
        inv_display_strings = [entry.display_string for entry in inventory_items]
        room_display_strings = [entry.display_string for entry in room_items]

        if inv_display_strings:
            inventory_summary = f"Items in your inventory: {', '.join(inv_display_strings)}"
        else:
            inventory_summary = "Your inventory is empty."

        if room_display_strings:
            room_summary = f"Items in the {room_display}: {', '.join(room_display_strings)}"
        else:
            room_summary = f"There are no items in the {room_display}."

        return cls(
            inventory_items=inventory_items,
            room_items=room_items,
            room_id=room_id,
            room_name=room_name,
            inventory_display_strings=inv_display_strings,
            room_display_strings=room_display_strings,
            inventory_summary=inventory_summary,
            room_summary=room_summary,
        )

class ItemLookupResult(BaseModel):
    """
    The single return type for all item lookup operations.

    On success:  success=True,  item_data is populated, error is None.
    On failure:  success=False, item_data is None,      error describes why.

    Fields
    ------
    success         : Whether the lookup passed all requested filters.
    item_data       : The raw item dict (mutable reference into state). None on failure.
    location        : "inventory" or "room". None on failure.
    location_id     : Room ID if location=="room", else None.
    location_name   : Room name if location=="room", else None.
    error           : Human-readable failure reason. None on success.
    """

    success: bool
    item_data: dict | None = None
    location: Literal["inventory", "room"] | None = None
    location_id: int | None = None
    location_name: str | None = None
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _check_consistency(self) -> ItemLookupResult:
        if self.success:
            assert self.item_data is not None, "Successful result must have item_data."
            assert self.location is not None,  "Successful result must have location."
            assert self.error is None,         "Successful result must not have an error."
        else:
            assert self.error is not None,     "Failed result must have an error message."
        return self

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def ok(
        cls,
        item_data: dict,
        location: Literal["inventory", "room"],
        location_id: int | None = None,
        location_name: str | None = None,
    ) -> ItemLookupResult:
        """Build a successful result."""
        return cls(
            success=True,
            item_data=item_data,
            location=location,
            location_id=location_id,
            location_name=location_name,
            error=None,
        )

    @classmethod
    def fail(cls, error: str) -> ItemLookupResult:
        """Build a failed result."""
        return cls(
            success=False,
            item_data=None,
            location=None,
            location_id=None,
            location_name=None,
            error=error,
        )




class ItemCreationResult(BaseModel):
    """
    The single return type for all item creation operations.

    On success:  success=True,  created_ids is populated, error is None.
    On failure:  success=False, created_ids is empty,     error describes why.

    The message field is ALWAYS populated — on success it is a human-readable
    summary of what was created; on failure it mirrors the error. Callers that
    only need to append a string to a parts list can always use result.message
    without checking success first.

    Fields
    ------
    success      : Whether at least one item was created.
    created_ids  : List of integer IDs for every item/stack created or merged into.
    location     : Where items were placed ("inventory" or "room"). None on failure.
    message      : Human-readable summary. Always populated.
    error        : Failure reason. None on success.
    """

    success: bool
    created_ids: list[int] = []
    location: Literal["inventory", "room"] | None = None
    message: str = ""
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _check_consistency(self) -> ItemCreationResult:
        if self.success:
            assert len(self.created_ids) > 0, "Successful result must have at least one created ID."
            assert self.location is not None,  "Successful result must have a location."
            assert self.error is None,         "Successful result must not have an error."
        else:
            assert self.error is not None,     "Failed result must have an error message."
        return self

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def ok(
        cls,
        created_ids: list[int],
        location: Literal["inventory", "room"],
        message: str,
    ) -> ItemCreationResult:
        """Build a successful result."""
        return cls(
            success=True,
            created_ids=created_ids,
            location=location,
            message=message,
            error=None,
        )

    @classmethod
    def fail(cls, error: str) -> ItemCreationResult:
        """Build a failed result. message mirrors error for easy appending."""
        return cls(
            success=False,
            created_ids=[],
            location=None,
            message=error,
            error=error,
        )




class ItemRemovalResult(BaseModel):
    """
    The single return type for all item removal operations.

    On success:  success=True,  error is None.
    On failure:  success=False, error describes why.

    message is ALWAYS populated — mirrors error on failure, describes
    what was removed on success. Safe to append to a parts list without
    checking success first.
    """

    success: bool
    message: str
    error: str | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> ItemRemovalResult:
        if self.success:
            assert self.error is None, "Successful result must not have an error."
        else:
            assert self.error is not None, "Failed result must have an error message."
        return self

    @classmethod
    def ok(cls, message: str) -> ItemRemovalResult:
        return cls(success=True, message=message, error=None)

    @classmethod
    def fail(cls, error: str) -> ItemRemovalResult:
        return cls(success=False, message=error, error=error)


ROOM_BASE_KEYS = {"id", "name", "image", "music", "room_types", "descriptions", "items"}

class RoomDataResult(BaseModel):
    id: int
    name: str
    image: str
    music: str
    description: str
    room_types: list[str]
    extra_data: dict = {}

    @classmethod
    def from_room_dict(cls, room: dict) -> RoomDataResult:
        time_tag = get_time_tag_from_now()
        descriptions_by_time = room.get("descriptions", {})
        descriptions = descriptions_by_time.get(time_tag, [])
        if not isinstance(descriptions, list):
            descriptions = []

        return cls(
            id=room["id"],
            name=room.get("name", "Unknown Room"),
            image=room.get("image", ""),
            music=room.get("music", ""),
            description=" ".join(descriptions),
            room_types=room.get("room_types", []),
            extra_data={k: v for k, v in room.items() if k not in ROOM_BASE_KEYS},
        )

# Expand on this
class SetItemAttributeResult(BaseModel):
    """
    The single return type for all set_item_attribute operations.

    On success:  success=True,  message is None.
    On failure:  success=False, message describes why.

    Fields
    ------
    success         : Whether the lookup passed all requested filters.
    message         : Human-readable failure reason. None on success.
    """

    success: bool
    message: str 

