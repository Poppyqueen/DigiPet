from __future__ import annotations

from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider


class WalledWindowProvider(OutdoorsProvider):
    """
    Default fallback provider for rooms/apertures with no outdoors_type
    defined. Represents a window (or the absence of one) that looks out
    onto nothing but a wall — no weather, no wildlife, no sky.

    Purely static text. No audio, no popups, no ticking state.
    """

    outdoors_type = "walled-window"
    tick_every = 1

    def get_limited_perception(self) -> tuple[str, str | None]:
        return "There's nothing to see outside — just a wall.", None

    def get_full_perception(self) -> tuple[str, str | None, tuple[bytes, int] | None]:
        return "You look outside, but there's nothing there — just a blank wall.", None, None