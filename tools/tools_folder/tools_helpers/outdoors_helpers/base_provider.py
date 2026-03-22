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
        Should be short and narratively undetailed — no fine species or
        weather detail.

    - get_full_perception()
        Complete, deliberate awareness. Used when the agent either actively
        looks through an aperture (look_through_aperture action) or is
        standing inside an outdoors_area room. May be rich and detailed.

    An optional tick() method is provided for providers that need to advance
    internal state over time (e.g. cycling through a selection of recordings).
    Providers that have no time-driven state simply leave it as the no-op.
    tick_every controls how often OutdoorsPerception.tick() delegates here —
    a value of 1 means every tick, 3 means every third tick, and so on.
    """

    outdoors_type: str  # Subclasses must set this at class level.
    tick_every:    int = 1

    @abstractmethod
    def get_limited_perception(self) -> tuple[str, str | None]:
        """
        Return (perception_text, popup_text).

        Called by window_perception() — the agent is near a window but has
        not actively looked through it. popup_text is usually None here.
        """
        ...

    @abstractmethod
    def get_full_perception(self) -> tuple[str, str | None, tuple[bytes, int] | None]:
        """
        Return (perception_text, popup_text, audio).

        Called by look_through_aperture() or outdoors_perception() when the
        agent has full access to the outside view. audio is (bytes, sample_rate)
        if the provider has a sound to play, or None if it does not.
        """
        ...

    def tick(self) -> None:
        """
        Called by OutdoorsPerception.tick() at the cadence defined by tick_every.

        Override this to advance internal state between perception calls —
        for example, cycling a playback index or expiring a cached value.
        The default implementation is a no-op; providers that have no
        time-driven state do not need to override it.
        """