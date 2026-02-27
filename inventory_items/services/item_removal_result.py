# ============================================================================
# item_removal_result.py
# Place alongside item_lookup_result.py and item_creation_result.py
# ============================================================================

from __future__ import annotations
from pydantic import BaseModel, model_validator


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

