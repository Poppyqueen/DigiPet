from __future__ import annotations
from pydantic import BaseModel
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

