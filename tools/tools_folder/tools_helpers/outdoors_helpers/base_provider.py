from __future__ import annotations
from abc import ABC, abstractmethod


class OutdoorsProvider(ABC):
    """
    Abstract base class for all outdoors perception providers.

    Each provider is identified by a class-level `outdoors_type` string that
    must match the value used in item data and room extra_data.

    Two perception levels are enforced:

    - get_limited_perception()
        Peripheral / ambient awareness. The agent is in a room that has a
        fenestration aperture nearby but has not actively looked through it.
        Should be short and narratively local — no fine detail.

    - get_full_perception()
        Complete, deliberate awareness. Used when the agent either actively
        looks through an aperture (look_through_aperture action) or is
        standing inside an outdoors_area room.
        May be rich and detailed.
    """

    outdoors_type: str  # Subclasses must set this at class level.

    @abstractmethod
    def get_limited_perception(self) -> str:
        """
        Return a short, ambient perception string.
        Called by window_perception() — the agent is near a window but has
        not actively looked through it.
        """
        ...

    @abstractmethod
    def get_full_perception(self) -> str:
        """
        Return a complete, detailed perception string.
        Called by outdoors_perception() and by look_through_aperture() when
        the aperture is accessible.
        """
        ...