from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider
from tools.tools_folder.tools_helpers.outdoors_helpers.earth_weather_prov import EarthWeatherProvider
from tools.tools_folder.tools_helpers.outdoors_helpers.marine_weather_prov import MarineWeatherProvider
from tools.tools_folder.tools_helpers.outdoors_helpers.walled_window_prov import WalledWindowProvider

from tools.tools_folder.tools_helpers.outdoors_helpers.lunar_dome_provider import LunarDomeViewProvider

from tools.tools_folder.tools_helpers.outdoors_helpers.outdoors_type_definitions import OUTDOORS_TYPES

import os

_PROVIDER_SEPARATOR = "\n" + "-" * 30 + "\n"
_DEFAULT_OUTDOORS_TYPE = ["walled-window"]


@dataclass
class PerceptionResult:
    text: str
    popup: str | None = None
    audio: tuple | None = None


class OutdoorsPerception:

    def __init__(self, state_manager, signal=None, open_meteo=None, config_manager=None):
        self._signal_callback = signal
        self.state_manager    = state_manager
        self.open_meteo       = open_meteo
        self.config_manager   = config_manager
        self._tick_count: int = 0

        self.lat  = config_manager.get_config("location", "latitude")
        self.long = config_manager.get_config("location", "longitude")
        if not self.lat or not self.long:
            self.lat  = os.getenv("LATITUDE")
            self.long = os.getenv("LONGITUDE")

        self._providers: dict[str, OutdoorsProvider] = {}
        self._register_provider(EarthWeatherProvider(open_meteo))
        self._register_provider(MarineWeatherProvider(open_meteo))
        self._register_provider(WalledWindowProvider())
        self._register_provider(LunarDomeViewProvider(self.config_manager, self.lat,self.long))
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

    def _load_conditionals(self) -> None:
        canto_key = os.getenv("XENO_CANTO_API_KEY")
        if canto_key and self.config_manager.get_config("outdoors_perception", "enable_xeno_canto"):
            from utils.xeno_canto_api import XenoCantoLoc
            from tools.tools_folder.tools_helpers.outdoors_helpers.xeno_canto_prov import XenoCantoProvider
            self.xeno_canto = XenoCantoLoc(self.lat, self.long, api_key=canto_key)

            wildlife_abundance = self.config_manager.get_config("outdoors_perception", "xenocanto_abundance")
            self._register_provider(XenoCantoProvider(self.xeno_canto, self.open_meteo, wildlife_abundance=wildlife_abundance))

        if self.config_manager.get_config("outdoors_perception", "enable_astro_views"): # Add flag or something for the sky thing
            from .tools_helpers.outdoors_helpers.sky_provider import EarthAstroViews
            
            self._register_provider(EarthAstroViews(self.open_meteo, self.config_manager, self.lat, self.long))

    def _register_provider(self, provider: OutdoorsProvider) -> None:
        self._providers[provider.outdoors_type] = provider

    def _resolve_providers(self, outdoors_types: list[str]) -> list[tuple[str, OutdoorsProvider | None]]:
        return [(t, self._providers.get(t)) for t in outdoors_types]

    # ------------------------------------------------------------------
    # Core data layer — pure, no side effects
    # ------------------------------------------------------------------

    def _gather_provider_outputs(
        self, outdoors_types: list[str], level: str
    ) -> Generator[PerceptionResult, None, None]:
        """
        Pure generator. Fetches perception data from each provider and yields
        PerceptionResult objects. Never fires signals or plays audio.
        """
        for type_name, provider in self._resolve_providers(outdoors_types):
            if provider is None:
                yield PerceptionResult(
                    text=f"" # Quietly skip.
                )
                continue
            try:
                if level == "limited":
                    text, popup = provider.get_limited_perception()
                    yield PerceptionResult(text=text, popup=popup)
                else:
                    text, popup, audio = provider.get_full_perception()
                    yield PerceptionResult(text=text, popup=popup, audio=audio)
            except Exception as e:
                yield PerceptionResult(
                    text=f"[Perception source '{type_name}' encountered an error: {e}]"
                )

    # ------------------------------------------------------------------
    # Callers opt into exactly the side effects they need
    # ------------------------------------------------------------------

    def _collect_text(self, outdoors_types: list[str], level: str) -> str:
        """Returns joined perception text. No side effects."""
        parts = [r.text for r in self._gather_provider_outputs(outdoors_types, level)]
        return _PROVIDER_SEPARATOR.join(parts) if parts else "[No perception available.]"

    def _collect_with_popups(self, outdoors_types: list[str], level: str) -> str:
        """Returns joined perception text and fires popup signals as a side effect."""
        parts = []
        for result in self._gather_provider_outputs(outdoors_types, level):
            if result.popup:
                self._send_signal({"type": "show_message_popup", "message": result.popup})
            parts.append(result.text)
        return _PROVIDER_SEPARATOR.join(parts) if parts else "[No perception available.]"

    def _play_audio(self, outdoors_types: list[str]) -> None:
        """Fires audio signals only. Ignores text and popups."""
        for result in self._gather_provider_outputs(outdoors_types, level="full"):
            if result.audio:
                audio_bytes, sample_rate = result.audio
                self._send_signal({
                    "type":           "play_sound",
                    "raw_audio_data": audio_bytes,
                    "sample_rate":    sample_rate,
                    "override":       False,
                })

    # ------------------------------------------------------------------
    # Tick & ambient audio
    # ------------------------------------------------------------------
    def tick(self) -> None:
        self._tick_count += 1
        for provider in self._providers.values():
            if self._tick_count % provider.tick_every == 0:
                try:
                    provider.tick()
                except Exception as e:
                    print(f"[OutdoorsPerception] tick error in '{provider.outdoors_type}': {e}")

        outdoors_types = self._get_outdoors_types_from_room()
        # This replaces the separate _play_audio and _collect_with_popups calls
        self._process_full_perception(outdoors_types)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_signal(self, signal_data: dict) -> None:
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from {self.__class__.__name__}: {e}")

    def _get_raw_room_outdoors_type(self, room_id: int | None = None) -> list[str]:
        """
        Returns whatever outdoors_type list is defined on the room, with no
        defaulting applied. Empty list means the room genuinely has none.
        room_id=None means "current room".
        """
        room_data = (
            self.state_manager.get_current_room_data()
            if room_id is None
            else self.state_manager.get_room_data(room_id)
        )
        raw = room_data.extra_data.get("outdoors_type", [])
        if isinstance(raw, list) and raw:
            return raw
        return []

    def _get_outdoors_types_from_item(self, location_id: int | None) -> list[str]:
        """
        Items no longer carry their own outdoors_type — the room is canon.
        A window in a room with no outdoors_type defined has nothing to see:
        falls back to walled-window.
        """
        raw = self._get_raw_room_outdoors_type(location_id)
        return raw if raw else _DEFAULT_OUTDOORS_TYPE

    def _get_outdoors_types_from_room(self, room_id: int | None = None) -> list[str]:
        raw = self._get_raw_room_outdoors_type(room_id)
        return raw if raw else _DEFAULT_OUTDOORS_TYPE

# ------------------------------------------------------------------
    # The "Single-Pass" Helper
    # ------------------------------------------------------------------
    def _process_full_perception(self, outdoors_types: list[str]) -> str:
        """
        Unified loop that handles text, popups, and audio in a single pass
        to prevent redundant provider calls.
        """
        text_parts = []
        for result in self._gather_provider_outputs(outdoors_types, level="full"):
            # 1. Handle Audio Side Effect
            if result.audio:
                audio_bytes, sample_rate = result.audio
                self._send_signal({
                    "type":           "play_sound",
                    "raw_audio_data": audio_bytes,
                    "sample_rate":    sample_rate,
                    "override":       False,
                })

            # 2. Handle Popup Side Effect
            if result.popup:
                self._send_signal({"type": "show_message_popup", "message": result.popup})

            # 3. Accumulate Text
            text_parts.append(result.text)

        return _PROVIDER_SEPARATOR.join(text_parts) if text_parts else "[No perception available.]"
    # ------------------------------------------------------------------
    # Public perception methods
    # ------------------------------------------------------------------

    def gui_outdoors_perception(self) -> str:
        """Called by the GUI. Triggers audio/popups once and returns text."""
        outdoors_types = self._get_outdoors_types_from_room()
        return self._process_full_perception(outdoors_types)

    def outdoors_perception(self) -> str:
        """
        Full perception text with no side effects.
        Used for environment awareness in outdoors_area rooms.
        """
        return self._collect_text(self._get_outdoors_types_from_room(), level="full")

    def window_perception(self) -> str:
        """
        Limited perception from fenestration apertures in the current room.
        No side effects — windows don't fire popups or audio on passive observation.
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
            outdoors_types = self._get_outdoors_types_from_item(window.location_id)
            parts.append(self._collect_text(outdoors_types, level="limited"))
        return _PROVIDER_SEPARATOR.join(parts)

    def look_through_aperture(self, aperture_id: int) -> str:
        """
        Active inspection of a specific aperture. Accessible apertures fire
        popups and audio; inaccessible ones remain silent.
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
        item_name          = self.state_manager.format_item_for_display(item_details, False)

        outdoors_types = self._get_outdoors_types_from_item(item_object.location_id)

        if accessibility_flag:
            weather_info = self._process_full_perception(outdoors_types)
            accessibility_message = (
                f"You walk right besides the {item_name}, standing there it allows "
                f"you to see everything outside, with clarity"
            )
        else:
            weather_info = self._collect_text(outdoors_types, level="limited")
            accessibility_message = (
                f"You can't walk close enough to the {item_name}, however you focus "
                f"all your attention into it for a second,"
            )

        self._send_signal({
            "type":      "show_icon_popup",
            "icon_path": "style/images/action_icons/window_icon.png",
        })

        return "\n".join([
            f"You move towards the views of the {item_name};",
            accessibility_message,
            "\n".join(descriptions),
            "As you peer outwards, you notice the outside world with absolute precision:",
            weather_info,
        ])