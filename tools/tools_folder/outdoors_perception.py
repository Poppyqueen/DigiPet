from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager  # just for typing

from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider
from tools.tools_folder.tools_helpers.outdoors_helpers.earth_weather_prov import EarthWeatherProvider
from tools.tools_folder.tools_helpers.outdoors_helpers.marine_weather_prov import MarineWeatherProvider


from tools.tools_folder.tools_helpers.outdoors_helpers.outdoors_type_definitions import OUTDOORS_TYPES

_PROVIDER_SEPARATOR = "\n" + "-" * 30 + "\n"
_DEFAULT_OUTDOORS_TYPE = ["earth-weather"]


class OutdoorsPerception:
    def __init__(self, state_manager, signal=None, open_meteo=None):
        self._signal_callback = signal
        self.state_manager: InventoryHouseManager = state_manager
        self.open_meteo = open_meteo

        # Registry: outdoors_type string → provider instance
        self._providers: dict[str, OutdoorsProvider] = {}
    
        self._register_provider(EarthWeatherProvider(open_meteo))

        self._register_provider(MarineWeatherProvider(open_meteo))

        # Warn at init if any defined type has no registered provider.
        # Catches mismatches between outdoors_type_definitions.py and the
        # providers wired up here before they surface as runtime fallbacks.
        for type_name in OUTDOORS_TYPES:
            if type_name not in self._providers:
                print(f"[OutdoorsPerception] WARNING: outdoors_type '{type_name}' is defined but has no registered provider.")

    # ------------------------------------------------------------------
    # Provider registry
    # ------------------------------------------------------------------

    def _register_provider(self, provider: OutdoorsProvider) -> None:
        self._providers[provider.outdoors_type] = provider

    def _resolve_providers(self, outdoors_types: list[str]) -> list[tuple[str, OutdoorsProvider | None]]:
        """
        Walk the outdoors_type list and return (type_name, provider_or_None)
        pairs. Unknown types get None so callers can emit an inline note.
        """
        return [(t, self._providers.get(t)) for t in outdoors_types]

    def _collect_perception(self, outdoors_types: list[str], level: str) -> str:
        """
        Walk all requested providers and collect their perception output at
        the given level ("limited" or "full"). Unknown types produce an inline
        note. Outputs are joined with a separator.

        Parameters
        ----------
        outdoors_types : list of outdoors_type strings read from item/room data.
        level          : "limited" → get_limited_perception()
                         "full"    → get_full_perception()
        """
        parts = []
        for type_name, provider in self._resolve_providers(outdoors_types):
            if provider is None:
                parts.append(f"[Perception source '{type_name}' is currently unavailable.]")
                continue
            try:
                if level == "limited":
                    parts.append(provider.get_limited_perception())
                else:
                    parts.append(provider.get_full_perception())
            except Exception as e:
                parts.append(f"[Perception source '{type_name}' encountered an error: {e}]")

        return _PROVIDER_SEPARATOR.join(parts) if parts else "[No perception available.]"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_signal(self, signal_data):
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from {self.__class__.__name__}: {e}")

    def _get_outdoors_types_from_item(self, item_data: dict) -> list[str]:
        """
        Read the outdoors_type list from a flat item dict.
        Falls back to the default if the key is absent or not a list.
        """
        raw = item_data.get("outdoors_type", _DEFAULT_OUTDOORS_TYPE)
        if isinstance(raw, list) and raw:
            return raw
        return _DEFAULT_OUTDOORS_TYPE

    def _get_outdoors_types_from_room(self) -> list[str]:
        """
        Read the outdoors_type list from the current room's extra_data.
        Falls back to the default if absent.
        """
        room_data = self.state_manager.get_current_room_data()
        raw = room_data.extra_data.get("outdoors_type", _DEFAULT_OUTDOORS_TYPE)
        if isinstance(raw, list) and raw:
            return raw
        return _DEFAULT_OUTDOORS_TYPE

    # ------------------------------------------------------------------
    # Public perception methods  (same surface as before)
    # ------------------------------------------------------------------

    def outdoors_perception(self) -> str:
        """
        Full perception of the outdoors. Used for environment awareness in
        outdoors_area rooms, and as the backing call for look_through_aperture
        when the aperture is accessible.

        Reads outdoors_type from the current room's extra_data.
        """
        outdoors_types = self._get_outdoors_types_from_room()
        return self._collect_perception(outdoors_types, level="full")

    def window_perception(self) -> str:
        """
        Limited perception of the outdoors. Used as agent_information when
        the agent is in a room that contains one or more fenestration apertures.

        Mirrors _get_accessible_tv_data — walks the current room's items,
        filters for fenestration_aperture type, and collects each window's
        limited perception independently. Each window contributes its own
        block, separated by the provider separator.

        Windows with no outdoors_type key fall back to ["earth-weather"].
        """
        inventory = self.state_manager.get_inventory_state()

        windows = [
            item for item in inventory.room_items
            if "fenestration_aperture" in item.item_data.get("type", [])
        ]

        if not windows:
            return ""  # No windows in room — caller should not be invoking this

        parts = []
        for window in windows:
            outdoors_types = self._get_outdoors_types_from_item(window.item_data)
            perception = self._collect_perception(outdoors_types, level="limited")
            parts.append(perception)

        return _PROVIDER_SEPARATOR.join(parts)

    def look_through_aperture(self, aperture_id: int) -> str:
        """
        Returns a string describing what the agent perceives by looking through
        a specific fenestration aperture.

        The aperture's own `accessible` flag determines whether the agent gets
        full or limited perception — inaccessible apertures (glass ceilings,
        high windows) still only yield limited perception regardless of type.

        outdoors_type is read as a flat key from the aperture's item_data,
        falling back to the room's extra_data value, then to the default.
        """
        item_object = self.state_manager.find_item(
            item_id=aperture_id,
            required_type="fenestration_aperture",
            required_location="room",
        )
        if not item_object.success:
            return item_object.error

        item_details = item_object.item_data
        descriptions = item_details.get("descriptions", [])
        accessibility_flag = item_details.get("accessible", True)

        # Resolve outdoors_type: item first, then room, then default.
        if "outdoors_type" in item_details:
            outdoors_types = self._get_outdoors_types_from_item(item_details)
        else:
            outdoors_types = self._get_outdoors_types_from_room()

        if accessibility_flag:
            weather_info = self._collect_perception(outdoors_types, level="full")
            accessibility_message = f"You walk right besides the {item_details["name"]}, standing there it allows you to see everything outside, with clarity"
        else:
            weather_info = self._collect_perception(outdoors_types, level="limited")
            accessibility_message = f"You can't walk close enough to the {item_details["name"]}, however you focus all your attention into it for a second,"

        message = "\n".join([
            f"You get as close as you can to the {item_details["name"]};",
            accessibility_message,
            "\n".join(descriptions),
            "As you peer outwards, you notice the outside world with absolute precision:",
            weather_info,
        ])

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/window_icon.png"})

        return message