"""
Garden Controller
=================

Top-level shell that the game engine calls directly.
Mirrors the role of LighthouseController.

Responsibilities:
- Validate player location and room type
- Interact with the state manager (items, stats, signals, room data)
- Delegate all simulation / persistence work to GardenManager
- Format final strings returned to the AI agent

Nothing in this file touches JSON or garden maths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.tools_folder.tools_helpers.garden_helpers.garden_manager import GardenManager

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager
    from inventory_items.services.item_lookup_result import ItemLookupResult


# ---------------------------------------------------------------------------
# Stat costs
# ---------------------------------------------------------------------------

PLANT_SEED_COSTS    = {"energy": -2.5,  "hydration": -2.5,  "fullness": -2.5}
CHECK_PLANT_COSTS   = {"energy": -0.25, "hydration": -0.25, "fullness": -0.25}
WATER_PLOT_COSTS    = {"energy": -0.15, "hydration": -0.15, "fullness": -0.15}
HARVEST_COSTS       = {"energy": -2.5,  "hydration": -2.5,  "fullness": -2.5}
GARDEN_SUMMARY_COSTS = {"energy": -1.5, "hydration": -1.5,  "fullness": -1.5}


class GardenController:
    """
    Thin shell — mirrors LighthouseController.
    The game engine instantiates this and calls its public methods.
    """

    def __init__(self, state_manager, signal, open_meteo):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal_callback = signal

        # Pull room definitions once so GardenManager can initialise plots.
        # TODO: Get a public method for this
        rooms_data = self.state_manager.get_all_rooms_data()

        self.garden_manager = GardenManager(
            open_meteo=open_meteo,
            room_definitions=rooms_data,
            base_path=self.state_manager.base_path,
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _send_signal(self, signal_data: dict) -> None:
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as exc:
                print(f"GardenController: signal error — {exc}")

    def _adjust_stats(self, cost_dict: dict, multiplier: float = 1.0) -> str:
        parts = []
        for stat, amount in cost_dict.items():
            total = amount * multiplier
            self.state_manager.adjust_stat(stat, total)
            parts.append(f"{total:+.2f} {stat}")
        return ", ".join(parts)

    def _require_garden_room(self) -> tuple[object | None, str]:
        """
        Returns (room_data, error).  error is empty string on success.
        """
        try:
            room_data = self.state_manager.get_current_room_data()
        except ValueError:
            return None, "You are not in a valid room."

        if "planting_garden" not in room_data.room_types:
            return None, "You are not in a planting garden room."

        return room_data, ""

    def _room_name(self, room_id) -> str:
        return self.state_manager.get_room_data(room_id).name

    # -----------------------------------------------------------------------
    # Game loop
    # -----------------------------------------------------------------------

    def tick(self) -> str:
        """Called once per logical game minute by the orchestrator."""
        events_by_room = self.garden_manager.tick()

        lines = []
        for room_id, events in events_by_room.items():
            for ev in events:
                lines.append(ev.message)

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Player actions
    # -----------------------------------------------------------------------

    def plant_seed(self, plot_id: str, item_id: int) -> str:
        room_data, err = self._require_garden_room()
        if err:
            return err

        # Validate seed item in inventory
        seed_result: ItemLookupResult = self.state_manager.find_item(
            item_id,
            required_type="seed",
            required_location="inventory",
        )
        if not seed_result.success:
            return seed_result.error

        item_data  = seed_result.item_data
        item_name  = item_data.get("name", "unknown item")
        plant_type = item_data.get("plant_type")

        if not plant_type:
            return f"Seed item {item_id} ({item_name}) does not specify a 'plant_type'."

        msg, success = self.garden_manager.plant_seed(
            room_id=room_data.id,
            plot_id=plot_id,
            plant_type=plant_type,
        )
        if not success:
            return msg

        self.state_manager.remove_item(item_id)
        stats = self._adjust_stats(PLANT_SEED_COSTS)
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/seed.png", "popup_type": 2})

        return f"{msg}\nSeed consumed. {stats}."

    def water_plot(self, plot_id: str, water_level_type: str) -> str:
        room_data, err = self._require_garden_room()
        if err:
            return err

        msg, success = self.garden_manager.water_plot(
            room_id=room_data.id,
            plot_id=plot_id,
            water_level_type=water_level_type,
        )
        if not success:
            return msg

        stats = self._adjust_stats(WATER_PLOT_COSTS)
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/watering_can.png"})

        return f"{msg} {stats}."

    def check_plant_state(self, plot_id: str) -> str:
        room_data, err = self._require_garden_room()
        if err:
            return err

        msg, _ = self.garden_manager.check_plant_state(
            room_id=room_data.id,
            plot_id=plot_id,
        )
        stats = self._adjust_stats(CHECK_PLANT_COSTS)
        return f"{msg} {stats}."

    def harvest_plant(self, plot_id: str) -> str:
        room_data, err = self._require_garden_room()
        if err:
            return err

        msg, items, success = self.garden_manager.harvest_plant(
            room_id=room_data.id,
            plot_id=plot_id,
        )
        if not success:
            return msg

        # Place harvested items into inventory
        placed_lines = []
        if items:
            for entry in items:
                item_def = entry.get("item")
                quantity = entry.get("quantity", 0)
                if item_def and quantity > 0:
                    result = self.state_manager.create_item("inventory", None, item_def, quantity=quantity)
                    placed_lines.append(f"  {quantity}× {item_def.get('name', '?')} → {result.message}")

        stats = self._adjust_stats(HARVEST_COSTS)
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/harvest.png", "popup_type": 2})

        item_summary = "\n".join(placed_lines) if placed_lines else "  No items yielded."
        return f"{msg}\nItems received:\n{item_summary}\n{stats}."

    def remove_plant_from_plot(self, plot_id: str) -> str:
        room_data, err = self._require_garden_room()
        if err:
            return err

        msg, _ = self.garden_manager.remove_plant(
            room_id=room_data.id,
            plot_id=plot_id,
        )
        return msg

    # -----------------------------------------------------------------------
    # Status queries
    # -----------------------------------------------------------------------

    def get_garden_summary(self) -> str:
        room_data, err = self._require_garden_room()
        if err:
            return err

        return self.garden_manager.get_garden_summary(
            room_id=room_data.id,
            room_name=self._room_name(room_data.id),
        )

    def ai_get_garden_summary(self) -> str:
        """Entry point for the AI agent — adds stat cost on top of the summary."""
        summary = self.get_garden_summary()
        stats   = self._adjust_stats(GARDEN_SUMMARY_COSTS)
        return f"{summary}\n{stats}."