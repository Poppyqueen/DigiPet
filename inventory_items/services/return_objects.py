from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, model_validator

from utils.time_manager import get_time_tag_from_now


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

