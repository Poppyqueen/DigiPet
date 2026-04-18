# tv_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager
    from inventory_items.services.return_objects import InventoryStateResult, InventoryItemEntry

from tools.tools_folder.tools_helpers.tv_utils.tv_manager import TVManager


class TVController:
    """
    Public-facing API for all TV interactions.
    All methods return descriptive strings except tv_tick(), which returns None.

    current_channel lives on the inventory item itself and is read/written
    via state_manager — TVManager never owns per-TV state.
    """

    def __init__(self, state_manager, signal_callback=None, config_manager=None):
        self.state_manager: InventoryHouseManager = state_manager
        base_path = self.state_manager.base_path
        self.tv_manager: TVManager = TVManager(base_path=base_path, config_manager=config_manager)
        self._signal_callback = signal_callback

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_signal(self, signal_data: dict) -> None:
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Signal error in {self.__class__.__name__}: {e}")

    def _get_tv_state(self, tv_id: int) -> tuple[bool, dict | str]:
        """
        Validate the TV, resolve its current channel (writing the default back if
        none is set), and return all fields needed by the public API in one shot.

        Returns (True, state_dict) on success or (False, error_message) on failure.

        state_dict keys:
            tv_type         – str, e.g. "bad tv"
            current_channel – str, resolved and guaranteed to be valid
        """
        found_response = self.state_manager.find_item(
            item_id=tv_id, required_type="tv", required_location="accessible"
        )
        if found_response.error:
            return False, found_response.error

        ts = found_response.item_data.get("toggle_state", {})
        if isinstance(ts, dict) and ts.get("toggle_state") == "off":
            return False, f"TV {tv_id} is turned off."

        tv_state = found_response.item_data.get("tv_state", {})
        tv_type = tv_state.get("tv_type")
        if not tv_type:
            return False, f"TV {tv_id} has no tv_type configured."

        current_channel = tv_state.get("current_channel")

        # If the TV has no channel set yet, default to the first one and persist it.
        if not current_channel:
            current_channel = self.tv_manager.get_first_channel_name(tv_type)
            if not current_channel:
                return False, "This TV has no channels available."
            self._set_current_channel(tv_id, current_channel)

        return True, {
            "tv_type": tv_type,
            "current_channel": current_channel,
        }

    def _set_current_channel(self, tv_id: int, channel_name: str) -> None:
        self.state_manager.set_item_attribute(
            item_id=tv_id,
            key="current_channel",
            value=channel_name,
            path=["tv_state"],
        )

    def _format_on_screen(self, channel_name: str, program_name: str, section: str) -> str:
        """Format what is currently on screen into a readable string."""
        return (
            f"Channel: {channel_name}\n"
            f"Program: {program_name}\n"
            f"On screen: {section}"
        )

    def _send_tv_signal(self) -> None:
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/tv_icon.png"})

    def _filter_tvs(self, item_data: list[InventoryItemEntry]):
        return [item for item in item_data if "tv" in item.item_data.get("type", "")]

    def _get_accessible_tv_data(self, blocking: bool) -> str:
        """
        Returns a display string for all accessible TVs.
        """
        inventory: InventoryStateResult = self.state_manager.get_inventory_state()

        check_all = inventory.inventory_items + inventory.room_items
        tvs = self._filter_tvs(check_all)

        if not tvs:
            return "No TVs found."

        display_string = "TVs around you:\n"

        for tv in tvs:
            tv_id = tv.item_id
            tv_name = tv.name

            flag, state = self._get_tv_state(tv_id)
            if not flag:
                display_string += f"  {self.state_manager.format_item_for_display(tv)}  — unavailable: {state}\n"
                display_string += "=" * 30 + "\n"
                continue

            tv_type = state["tv_type"]
            current_channel = state["current_channel"]

            display_string += f"  {self.state_manager.format_item_for_display(tv)}\n"
            result = self.tv_manager.get_current_section(tv_type, current_channel, blocking=blocking)
            program_info = self._format_on_screen(current_channel, *result) if result else ""
            display_string += f"Currently playing: {program_info}\n"
            display_string += "=" * 30 + "\n"

        return display_string

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def watch_tv(self, tv_id: int) -> str:
        """
        Watch the TV. Resolves tv_type and current_channel in a single inventory
        read, defaulting and persisting the channel if none is set.
        Generates content for the channel if none exists.
        """
        flag, state = self._get_tv_state(tv_id)
        if not flag:
            return f"Could not access TV: {state}"

        tv_type = state["tv_type"]
        current_channel = state["current_channel"]

        program_name, section = self.tv_manager.get_current_section(tv_type, current_channel)
        self._send_tv_signal()
        return self._format_on_screen(current_channel, program_name, section)

    def browse_channels(self, tv_id: int) -> str:
        """
        List all channels for this TV's type with their descriptions.
        Marks the currently watched channel. Does not generate any content.
        """
        flag, state = self._get_tv_state(tv_id)
        if not flag:
            return f"Could not access TV: {state}"

        tv_type = state["tv_type"]
        current_channel = state["current_channel"]
        channels = self.tv_manager.get_all_channels(tv_type)

        if not channels:
            return "This TV has no channels available."

        lines = ["Available channels:\n"]
        for channel in channels:
            marker = " ◄ [WATCHING]" if channel.name == current_channel else ""
            lines.append(f"  {channel.name}{marker}\n    {channel.description}\n")

        self._send_tv_signal()
        return "\n".join(lines)

    def change_channel(self, tv_id: int, channel_name: str) -> str:
        """
        Switch the TV to a different channel, saving the choice to the inventory item.
        Generates content for the new channel if none exists.
        """
        flag, state = self._get_tv_state(tv_id)
        if not flag:
            return f"Could not access TV: {state}"

        tv_type = state["tv_type"]

        if not self.tv_manager.is_valid_channel(tv_type, channel_name):
            channels = self.tv_manager.get_all_channels(tv_type)
            valid_names = ", ".join(c.name for c in channels)
            return f"Channel '{channel_name}' not found. Available channels: {valid_names}"

        self._set_current_channel(tv_id, channel_name)
        program_name, section = self.tv_manager.get_current_section(tv_type, channel_name)
        self._send_tv_signal()
        return self._format_on_screen(channel_name, program_name, section)

    def tv_tick(self) -> None:
        """
        Advance all TV channels across all registered tv_types by one tick.
        Progresses indexes, exhausts finished programs, and updates none_ticks.
        Returns None.
        """
        self.tv_manager.tick()

    # ------------------------------------------------------------------
    # Perception and GUI methods
    # ------------------------------------------------------------------

    def get_current_accessible_tv_agent(self) -> str:
        """Returns the current accessible TV for agent perception. (blocking)"""
        return self._get_accessible_tv_data(blocking=True)

    def get_current_accessible_tv_gui(self) -> str:
        """Returns the current accessible TV for GUI display. (non-blocking)"""
        return self._get_accessible_tv_data(blocking=False)