# This is a really particular tool now, it uses the API correctly, and has a clear state management, however, it is doing funny stuff with threading, 
# specifically for get_current_accessible_tv, which is called as a GUI display information tool, it is called in the GUI with a thread, it is a proxy for watch tv
# Claude calls it a "Single-flight coalescing mutex"
# go figure...


# if an affordance that you are creating has a "display information tool" that requires a long time to respond, expensive process or state editing**, 
# you should use a "single-flight coalescing mutex" pattern to prevent multiple threads from generating the same content.

# "display information tools" should not edit state! here we are... populating state with it if it is not yet populated, which might not be a great idea.** 

from __future__ import annotations
from typing import TYPE_CHECKING, List

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

    def _get_tv_data(self, tv_id: int) -> tuple[bool, dict | str]:
        """
        Validate the TV item and return its data.
        Returns (True, item_data) on success or (False, error_message) on failure.
        """
        found_response = self.state_manager.find_item(
            item_id=tv_id, required_type="tv", required_location="accessible"
        )
        if found_response.error:
            return False, found_response.error
        return True, found_response.item_data

    def _set_current_channel(self, tv_id: int, channel_name: str) -> None:
        """Write the current channel back to the inventory item."""
        self.state_manager.set_item_attribute(
            item_id=tv_id,
            key="current_channel",
            value=channel_name,
        )

    def _format_on_screen(self, channel_name: str, program_name: str, section: str) -> str:
        """Format what is currently on screen into a readable string."""
        return (
            f"Channel: {channel_name}\n"
            f"Program: {program_name}\n"
            f"On screen: {section}"
        )

    def _filter_tvs(self, item_data: List[InventoryItemEntry]):
        tvs = []
        for item in item_data:
            if "tv" in item.item_data.get("type", ""):
                tvs.append(item)
        return tvs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def watch_tv(self, tv_id: int) -> str:
        """
        Watch the TV. Resolves the TV type and current channel from the inventory item.
        If no channel is set, defaults to the first channel for this tv_type and saves it.
        Generates content for the channel if none exists, then returns what is on screen.
        If generation is already in flight on another thread, returns a "warming up" message.
        """
        flag, data = self._get_tv_data(tv_id)
        if not flag:
            return f"Could not access TV: {data}"

        tv_type = data["tv_type"]
        current_channel = data.get("current_channel")

        # If the TV has no channel set, default to the first one and save it
        if not current_channel:
            current_channel = self.tv_manager.get_first_channel_name(tv_type)
            if not current_channel:
                return "This TV has no channels available."
            self._set_current_channel(tv_id, current_channel)

        program_name, section = self.tv_manager.get_current_section(tv_type, current_channel)
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/tv_icon.png"})
        return self._format_on_screen(current_channel, program_name, section)

    def browse_channels(self, tv_id: int) -> str:
        """
        List all channels for this TV's type, with their descriptions.
        Marks the currently watched channel. Does not generate any content.
        """
        flag, data = self._get_tv_data(tv_id)
        if not flag:
            return f"Could not access TV: {data}"

        tv_type = data["tv_type"]
        current_channel = data.get("current_channel")
        channels = self.tv_manager.get_all_channels(tv_type)

        if not channels:
            return "This TV has no channels available."

        lines = ["Available channels:\n"]
        for channel in channels:
            marker = " ◄ [WATCHING]" if channel.name == current_channel else ""
            # now_airing = f"Now airing: {channel.program_name}" if channel.has_content() else "Now airing: —"
            lines.append(
                f"  {channel.name}{marker}\n"
                f"    {channel.description}\n"
                # f"    {now_airing}\n"
            )
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/tv_icon.png"})

        return "\n".join(lines)

    def change_channel(self, tv_id: int, channel_name: str) -> str:
        """
        Switch the TV to a different channel, saving the choice to the inventory item.
        Generates content for the new channel if none exists.
        Returns what is currently on screen on the new channel.
        If generation is already in flight on another thread, returns a "loading" message.
        """
        flag, data = self._get_tv_data(tv_id)
        if not flag:
            return f"Could not access TV: {data}"

        tv_type = data["tv_type"]

        if not self.tv_manager.is_valid_channel(tv_type, channel_name):
            channels = self.tv_manager.get_all_channels(tv_type)
            valid_names = ", ".join(c.name for c in channels)
            return f"Channel '{channel_name}' not found. Available channels: {valid_names}"

        self._set_current_channel(tv_id, channel_name)
        program_name, section = self.tv_manager.get_current_section(tv_type, channel_name)
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/tv_icon.png"})
        return self._format_on_screen(channel_name, program_name, section)

    def tv_tick(self) -> None:
        """
        Advance all TV channels across all registered tv_types by one tick.
        Progresses indexes, exhausts finished programs, and updates none_ticks.
        Returns None.
        """
        self.tv_manager.tick()

    def get_current_accessible_tv(self) -> str:
        """
        Returns the current accessible TV.
        """
        inventory: InventoryStateResult = self.state_manager.get_inventory_state()

        current_inventory = inventory.inventory_items
        current_room_items = inventory.room_items

        check_all = current_inventory + current_room_items
        tvs = self._filter_tvs(check_all)

        if not tvs:
            return "No TVs found."

        display_string = "TVs around you:\n"

        for tv in tvs:
            data = tv.item_data
            tv_id = tv.item_id
            tv_name = tv.name
            tv_type = data.get("tv_type")
            current_chan = data.get("current_channel")

            display_string += f"  {tv_name} (ID: {tv_id})\n"
            result = self.tv_manager.get_current_section(tv_type, data.get("current_channel") or self.tv_manager.get_first_channel_name(tv_type), blocking=False)
            program_info = self._format_on_screen(data.get("current_channel") or "", *result) if result else ""
            display_string += f"Currently playing: {program_info}\n"
            display_string += "=" * 30 + "\n"

        return display_string