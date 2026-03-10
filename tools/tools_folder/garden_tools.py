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

Unified API:
- Every player action (plant, water, check, harvest, remove) has one public
  method with an optional pot_id parameter.
- No pot_id  → room plot path (requires cultivation_zone room).
- pot_id set → pot slot path (requires accessible planter_pot item).
- The controller handles reading/writing pot_state to the item.
  GardenManager handles saving room state to JSON.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.tools_folder.tools_helpers.garden_helpers.garden_manager import GardenManager

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager
    from inventory_items.services.return_objects import ItemLookupResult


# ---------------------------------------------------------------------------
# Stat costs
# ---------------------------------------------------------------------------

PLANT_SEED_COSTS     = {"energy": -0.5,  "hydration": -0.5,  "fullness": -0.5}
CHECK_PLANT_COSTS    = {"energy": -0.05, "hydration": -0.025, "fullness": -0.025}
WATER_PLANT_COSTS    = {"energy": -0.15, "hydration": -0.15, "fullness": -0.15}
HARVEST_COSTS        = {"energy": -2.5,  "hydration": -2.5,  "fullness": -2.5}
GARDEN_SUMMARY_COSTS = {"energy": -0.25,  "hydration": -0.25,  "fullness": -0.25}

CULTIVATION_ZONE_TYPE = "open_soil_zone"
POT_TYPE              = "planter_pot"
OUTDOORS_AREA_TYPE    = "outdoors_area"


class GardenController:
    """
    Thin shell — mirrors LighthouseController.
    The game engine instantiates this and calls its public methods.
    """

    def __init__(self, state_manager, signal, open_meteo):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal_callback = signal

        rooms_data = self.state_manager.get_all_rooms_data()

        self.garden_manager = GardenManager(
            open_meteo=open_meteo,
            room_definitions=[r for r in rooms_data if CULTIVATION_ZONE_TYPE in r.room_types],
            base_path=self.state_manager.base_path,
        )

    # -----------------------------------------------------------------------
    # Private helpers — general
    # -----------------------------------------------------------------------

    def _send_signal(self, signal_data: dict) -> None:
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as exc:
                print(f"GardenController: signal error — {exc}")

    def _adjust_stats(self, cost_dict: dict) -> str:
        parts = []
        for stat, amount in cost_dict.items():
            self.state_manager.adjust_stat(stat, amount)
            parts.append(f"{amount:+.2f} {stat}")
        return ", ".join(parts)

    def _require_garden_room(self) -> tuple[object | None, str]:
        try:
            room_data = self.state_manager.get_current_room_data()
        except ValueError:
            return None, "Where are you?"
        if CULTIVATION_ZONE_TYPE not in room_data.room_types:
            return None, "This wouldn't be a good place to do that."
        return room_data, ""

    def _room_name(self, room_id) -> str:
        return self.state_manager.get_room_data(room_id).name

    # -----------------------------------------------------------------------
    # Private helpers — pots
    # -----------------------------------------------------------------------

    def _init_pot_state(self, item_data: dict) -> dict:
        """Assemble pot_state from flat LLM-generated fields on first access."""
        return {
            "capacity":        item_data.get("capacity", 1),
            "size_multiplier": item_data.get("size_multiplier", 1.0),
            "slots":           [],
        }

    def _get_pot_state(self, pot_id: int) -> tuple[bool, dict | str]:
        """
        Validate the pot item and return its pot_state dict.
        If pot_state is absent (new flat-schema item), assembles and saves it.
        Returns (True, pot_state_dict) or (False, error_message).
        """
        found = self.state_manager.find_item(
            item_id=pot_id,
            required_type=POT_TYPE,
            required_location="accessible",
        )
        if not found.success:
            return False, found.error

        pot_state = found.item_data.get("pot_state")
        if pot_state is None:
            pot_state = self._init_pot_state(found.item_data)
            self._save_pot_state(pot_id, pot_state)

        return True, pot_state

    def _save_pot_state(self, pot_id: int, pot_state: dict) -> None:
        """Write the updated pot_state back onto the inventory item."""
        self.state_manager.set_item_attribute(
            item_id=pot_id,
            key="pot_state",
            value=pot_state,
        )

    def _collect_all_pot_uids(self, all_pot_items: list) -> set[str]:
        uids: set[str] = set()
        for item_entry in all_pot_items:
            pot_state = item_entry.item_data.get("pot_state", {})
            for slot in pot_state.get("slots", []):
                plant = slot.get("plant")
                if plant and (uid := plant.get("_plant_UID")):
                    uids.add(uid)
        return uids

    def _maybe_save_pot(self, pot_id: int, updated: dict | None) -> None:
        """Write pot_state back to the item only if the manager returned one."""
        if updated is not None:
            self._save_pot_state(pot_id, updated)

    # -----------------------------------------------------------------------
    # Game loop
    # -----------------------------------------------------------------------

    def tick(self) -> str:
        """
        Called once per logical game minute by the orchestrator.
        Advances room garden plots and all pot plants across every room.
        """
        events_by_room = self.garden_manager.tick()
        lines = []
        for room_id, events in events_by_room.items():
            for ev in events:
                lines.append(ev.message)

        outdoor_room_ids: set = {
            room.id
            for room in self.state_manager.get_all_rooms_data()
            if OUTDOORS_AREA_TYPE in room.room_types
        }
        rain_level = self.garden_manager._get_rain()

        all_pots = self.state_manager.get_all_items_by_type(POT_TYPE)
        for item_entry in all_pots:
            pot_id    = item_entry.item_id
            pot_state = item_entry.item_data.get("pot_state")
            if not pot_state:
                continue

            pot_gets_rain = (
                item_entry.location == "room"
                and item_entry.location_id in outdoor_room_ids
            )
            updated, events = self.garden_manager.tick_pot(
                pot_state,
                rain_level=rain_level if pot_gets_rain else 0.0,
                apply_rain=pot_gets_rain,
            )
            self._save_pot_state(pot_id, updated)
            for ev in events:
                lines.append(ev.message)

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Unified player actions
    # pot_id=None  → room plot path
    # pot_id set   → pot slot path
    # -----------------------------------------------------------------------

    def plant_seed(self, plot_id: str, seed_id: int, pot_id: int | None = None) -> str:
        seed_result: ItemLookupResult = self.state_manager.find_item(
            seed_id,
            required_type="seed",
            required_location="inventory",
        )
        if not seed_result.success:
            return seed_result.error

        item_data  = seed_result.item_data
        item_name  = item_data.get("name", "unknown item")
        plant_type = item_data.get("plant_type")
        if not plant_type:
            return f"Seed item {seed_id} ({item_name}) does not specify a 'plant_type'."

        all_pots   = self.state_manager.get_all_items_by_type(POT_TYPE)
        known_uids = (
            self.garden_manager._all_existing_uids()
            | self._collect_all_pot_uids(all_pots)
        )

        if pot_id is not None:
            ok, pot_state = self._get_pot_state(pot_id)
            if not ok:
                return pot_state
            updated, msg, success = self.garden_manager.plant_seed(
                plot_id=plot_id,
                plant_type=plant_type,
                known_uids=known_uids,
                pot_state=pot_state,
            )
        else:
            room_data, err = self._require_garden_room()
            if err:
                return err
            updated, msg, success = self.garden_manager.plant_seed(
                plot_id=plot_id,
                plant_type=plant_type,
                known_uids=known_uids,
                room_id=room_data.id,
            )

        if not success:
            return msg

        if pot_id is not None:
            self._maybe_save_pot(pot_id, updated)

        self.state_manager.remove_item(seed_id)
        stats = self._adjust_stats(PLANT_SEED_COSTS)
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/seed.png", "popup_type": 2})
        return f"{msg}\nSeed consumed. {stats}."

    def water_plant(self, plot_id: str, water_level_type: str, pot_id: int | None = None) -> str:
        if pot_id is not None:
            ok, pot_state = self._get_pot_state(pot_id)
            if not ok:
                return pot_state
            updated, msg, success = self.garden_manager.water_plant(
                plot_id=plot_id,
                water_level_type=water_level_type,
                pot_state=pot_state,
            )
        else:
            room_data, err = self._require_garden_room()
            if err:
                return err
            updated, msg, success = self.garden_manager.water_plant(
                plot_id=plot_id,
                water_level_type=water_level_type,
                room_id=room_data.id,
            )

        if not success:
            return msg

        self._maybe_save_pot(pot_id, updated)
        stats = self._adjust_stats(WATER_PLANT_COSTS)
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/watering_can.png"})
        return f"{msg} {stats}."

    def check_plant(self, plot_id: str, pot_id: int | None = None) -> str:
        if pot_id is not None:
            ok, pot_state = self._get_pot_state(pot_id)
            if not ok:
                return pot_state
            _, msg, _ = self.garden_manager.check_plant(
                plot_id=plot_id,
                pot_state=pot_state,
            )
        else:
            room_data, err = self._require_garden_room()
            if err:
                return err
            _, msg, _ = self.garden_manager.check_plant(
                plot_id=plot_id,
                room_id=room_data.id,
            )

        stats = self._adjust_stats(CHECK_PLANT_COSTS)
        return f"{msg} {stats}."

    def harvest_plant(self, plot_id: str, pot_id: int | None = None) -> str:
        if pot_id is not None:
            ok, pot_state = self._get_pot_state(pot_id)
            if not ok:
                return pot_state
            updated, msg, items, success = self.garden_manager.harvest_plant(
                plot_id=plot_id,
                pot_state=pot_state,
            )
        else:
            room_data, err = self._require_garden_room()
            if err:
                return err
            updated, msg, items, success = self.garden_manager.harvest_plant(
                plot_id=plot_id,
                room_id=room_data.id,
            )

        if not success:
            return msg

        self._maybe_save_pot(pot_id, updated)

        placed_lines = []
        for entry in items:
            item_def = entry.get("item")
            quantity = entry.get("quantity", 0)
            if item_def and quantity > 0:
                result = self.state_manager.create_item("inventory", None, item_def, quantity=quantity)
                placed_lines.append(f"  {quantity}× {item_def.get('name', '?')} → {result.message}")

        stats        = self._adjust_stats(HARVEST_COSTS)
        item_summary = "\n".join(placed_lines) if placed_lines else "  No items yielded."
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/harvest.png", "popup_type": 2})
        return f"{msg}\nItems received:\n{item_summary}\n{stats}."

    def remove_plant(self, plot_id: str, pot_id: int | None = None) -> str:
        if pot_id is not None:
            ok, pot_state = self._get_pot_state(pot_id)
            if not ok:
                return pot_state
            updated, msg, success = self.garden_manager.remove_plant(
                plot_id=plot_id,
                pot_state=pot_state,
            )
        else:
            room_data, err = self._require_garden_room()
            if err:
                return err
            updated, msg, success = self.garden_manager.remove_plant(
                plot_id=plot_id,
                room_id=room_data.id,
            )

        if not success:
            return msg

        self._maybe_save_pot(pot_id, updated)
        return msg


    # -----------------------------------------------------------------------
    # Contextual awareness
    # -----------------------------------------------------------------------

    def _get_accessible_garden_data(self) -> str:
        sections = []

        try:
            room_data = self.state_manager.get_current_room_data()
            if CULTIVATION_ZONE_TYPE in room_data.room_types:
                sections.append(self.garden_manager.get_garden_summary(
                    room_id=room_data.id,
                    room_name=self._room_name(room_data.id),
                ))
        except ValueError:
            pass

        inventory = self.state_manager.get_inventory_state()
        all_items = inventory.inventory_items + inventory.room_items
        pots      = [item for item in all_items if POT_TYPE in item.item_data.get("type", [])]

        for item_entry in pots:
            ok, pot_state = self._get_pot_state(item_entry.item_id)
            if not ok:
                continue
            sections.append(self.garden_manager.get_pot_summary(
                pot_state=pot_state,
                pot_name=f"{item_entry.name} (ID: {item_entry.item_id})",
            ))

        return "\n\n".join(sections) if sections else "No garden plots or plant pots nearby."

    def get_current_accessible_garden_agent(self) -> str:
        summary = self._get_accessible_garden_data()
        stats   = self._adjust_stats(GARDEN_SUMMARY_COSTS)
        return f"{summary}\n{stats}."

    def get_current_accessible_garden_gui(self) -> str:
        return self._get_accessible_garden_data()