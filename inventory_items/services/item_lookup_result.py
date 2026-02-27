from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, model_validator


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