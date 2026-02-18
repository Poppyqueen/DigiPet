from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ActionInternalResponse:
    """
    Standard response object returned by all LighthouseManager action methods.

    Fields:
        message         Player-facing string describing what happened.
        formatted_events  Pre-joined string of event messages, or None if no events fired.
        events          Raw event list, if the caller needs to inspect individual events.
        success         Whether the action completed successfully. None = not applicable.
        data            Arbitrary action-specific payload for the controller to act on.
                        Only populated when the controller needs structured info beyond
                        success/failure to decide what to do next (e.g. item state after removal).
                        Leave as None for actions where success alone is sufficient.
    """
    message: str
    formatted_events: Optional[str] = None
    events: Optional[List] = None
    success: Optional[bool] = None
    data: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class Event:
    event_affordances_keys: list[str]
    type: str
    message: str
    data: Dict = None

    def __post_init__(self):
        if self.data is None:
            object.__setattr__(self, 'data', {})
