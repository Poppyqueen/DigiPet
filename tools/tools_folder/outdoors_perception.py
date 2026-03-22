from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager  # just for typing

from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider
from tools.tools_folder.tools_helpers.outdoors_helpers.earth_weather_prov import EarthWeatherProvider
from tools.tools_folder.tools_helpers.outdoors_helpers.marine_weather_prov import MarineWeatherProvider

from tools.tools_folder.tools_helpers.outdoors_helpers.outdoors_type_definitions import OUTDOORS_TYPES

import os

_PROVIDER_SEPARATOR = "\n" + "-" * 30 + "\n"
_DEFAULT_OUTDOORS_TYPE = ["earth-weather"]


class OutdoorsPerception:

    def __init__(self, state_manager, signal=None, open_meteo=None, config_manager=None):
        """
        Args:
            state_manager  : InventoryHouseManager
            signal         : optional signal callback
            open_meteo     : OpenMeteoLoc instance (for earth-weather provider)
        """
        self._signal_callback = signal
        self.state_manager    = state_manager
        self.open_meteo       = open_meteo
        self.config_manager   = config_manager

        self._tick_count: int = 0

        # Load config
        self.lat  = config_manager.get_config("location", "latitude")
        self.long = config_manager.get_config("location", "longitude")
        _env_lat  = os.getenv("LATITUDE")
        _env_long = os.getenv("LONGITUDE")
        if not self.lat or not self.long:
            self.lat, self.long = _env_lat, _env_long

        self._providers: dict[str, OutdoorsProvider] = {}

        self._register_provider(EarthWeatherProvider(open_meteo))
        self._register_provider(MarineWeatherProvider(open_meteo))

        self._load_conditionals()

        for type_name in OUTDOORS_TYPES:
            if type_name not in self._providers:
                print(
                    f"[OutdoorsPerception] WARNING: outdoors_type '{type_name}' "
                    f"is defined but has no registered provider."
                )

    # ------------------------------------------------------------------
    # Provider registry
    # ------------------------------------------------------------------

    def _load_conditionals(self):
        canto_key = os.getenv("XENO_CANTO_API_KEY")
        if canto_key:
            from utils.xeno_canto_api import XenoCantoLoc
            from tools.tools_folder.tools_helpers.outdoors_helpers.xeno_canto_prov import XenoCantoProvider
            self.xeno_canto = XenoCantoLoc(self.lat, self.long, api_key=canto_key)
            self._register_provider(XenoCantoProvider(self.xeno_canto))

    def _register_provider(self, provider: OutdoorsProvider) -> None:
        self._providers[provider.outdoors_type] = provider

    def _resolve_providers(self, outdoors_types: list[str]) -> list[tuple[str, OutdoorsProvider | None]]:
        """
        Walk the outdoors_type list and return (type_name, provider_or_None)
        pairs. Unknown types get None so callers can emit an inline note.
        """
        return [(t, self._providers.get(t)) for t in outdoors_types]

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self) -> None:
        self._tick_count += 1
        for provider in self._providers.values():
            if self._tick_count % provider.tick_every == 0:
                try:
                    provider.tick()
                except Exception as e:
                    print(f"[OutdoorsPerception] tick error in '{provider.outdoors_type}': {e}")
        self.tick_audio()
                    
    def tick_audio(self) -> None:
        """Fire audio/popup signals for the current room — called from tick, independent of lore panel."""
        outdoors_types = self._get_outdoors_types_from_room()
        self._collect_perception(outdoors_types, level="full")

    # ------------------------------------------------------------------
    # Perception collection
    # ------------------------------------------------------------------

    def _collect_perception(
        self,
        outdoors_types: list[str],
        level: str,
    ) -> str:
        """
        Walk all requested providers and collect their perception output at
        the given level ("limited" or "full"). Unknown types produce an inline
        note. Perception texts are joined with a separator.

        At the "full" level, also fires play_sound and show_message_popup
        signals for any provider that returns audio or a popup string.
        """
        parts: list[str] = []

        for type_name, provider in self._resolve_providers(outdoors_types):
            if provider is None:
                parts.append(f"[Perception source '{type_name}' is currently unavailable.]")
                continue
            try:
                if level == "limited":
                    text, popup = provider.get_limited_perception()
                else:
                    text, popup, audio = provider.get_full_perception()
                    if audio:
                        audio_bytes, sample_rate = audio
                        self._send_signal({
                            "type":           "play_sound",
                            "raw_audio_data": audio_bytes,
                            "sample_rate":    sample_rate,
                            "override":       False,
                        })
                    if popup:
                        self._send_signal({"type": "show_message_popup", "message": popup})

                parts.append(text)

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
    # Public perception methods
    # ------------------------------------------------------------------
    def outdoors_perception_text_only(self) -> str:
        """
        Full perception of the outdoors, text only.
        Same as outdoors_perception but suppresses all play_sound
        and show_message_popup signals — returns plain text only.
        """
        outdoors_types = self._get_outdoors_types_from_room()
        parts: list[str] = []

        for type_name, provider in self._resolve_providers(outdoors_types):
            if provider is None:
                parts.append(f"[Perception source '{type_name}' is currently unavailable.]")
                continue
            try:
                text, _popup, _audio = provider.get_full_perception()
                parts.append(text)
            except Exception as e:
                parts.append(f"[Perception source '{type_name}' encountered an error: {e}]")

        return _PROVIDER_SEPARATOR.join(parts) if parts else "[No perception available.]"
    
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
            return ""

        parts = []
        for window in windows:
            outdoors_types = self._get_outdoors_types_from_item(window.item_data)
            perception     = self._collect_perception(outdoors_types, level="limited")
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

        At the "full" level, _collect_perception fires play_sound signals for
        any provider that returns audio bytes, and any popup strings (e.g.
        Xeno-canto recording attribution) are fired as show_message_popup
        signals — one per provider. Neither fires for inaccessible apertures.
        """
        item_object = self.state_manager.find_item(
            item_id=aperture_id,
            required_type="fenestration_aperture",
            required_location="room",
        )
        if not item_object.success:
            return item_object.error

        item_details       = item_object.item_data
        descriptions       = item_details.get("descriptions", [])
        accessibility_flag = item_details.get("accessible", True)

        item_name = self.state_manager.format_item_for_display(item_details, False)

        # Resolve outdoors_type: item first, then room, then default.
        if "outdoors_type" in item_details:
            outdoors_types = self._get_outdoors_types_from_item(item_details)
        else:
            outdoors_types = self._get_outdoors_types_from_room()

        if accessibility_flag:
            weather_info = self._collect_perception(outdoors_types, level="full")
            accessibility_message = (
                f"You walk right besides the {item_name}, standing there it allows "
                f"you to see everything outside, with clarity"
            )
        else:
            weather_info = self._collect_perception(outdoors_types, level="limited")
            accessibility_message = (
                f"You can't walk close enough to the {item_name}, however you focus "
                f"all your attention into it for a second,"
            )

        message = "\n".join([
            f"You move towards the views of the {item_name};",
            accessibility_message,
            "\n".join(descriptions),
            "As you peer outwards, you notice the outside world with absolute precision:",
            weather_info,
        ])

        self._send_signal({
            "type":      "show_icon_popup",
            "icon_path": "style/images/action_icons/window_icon.png",
        })

        return message