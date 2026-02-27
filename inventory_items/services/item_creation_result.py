from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, model_validator


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