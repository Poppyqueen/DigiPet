"""
Garden Manager
==============

Thin persistence layer for the garden.

Responsibilities:
- Load / save state to JSON  (own implementation, no GenericJsonTool)
- Initialize plots from room definitions supplied by the caller
- Delegate all simulation logic to GardenSimulation
- Track the logical tick counter and rain cooldown timestamps

Unified plant addressing:
- All player actions (water, check, harvest, remove) work on either a room
  plot or a pot slot through the same methods.
- A PlantTarget dataclass abstracts where the plant lives and how to write
  it back.  Room targets save to garden_data.json internally.  Pot targets
  return an updated pot_state dict — the controller writes that back to the
  item via set_item_attribute.
- plot_id is the universal address string ("plot1", "slot1", etc.)
- size_multiplier on pot_state scales harvest yield.

Architecture:
    GardenManager (persistence + orchestration)
        └─> GardenSimulation
                ├─> GardenPlot
                └─> HarvestCalculator
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from tools.tools_folder.tools_helpers.garden_helpers.garden_simulation import (
    GardenSimulation,
    GardenEvent,
    PlantState,
)

from tools.tools_folder.tools_data.harvesting_data import plant_types
from tools.tools_folder.tools_data.garden_settings import GARDEN_SETTINGS
from utils.loc_datetime import datetime


# ---------------------------------------------------------------------------
# PlantTarget — abstracts "where does this plant live"
# ---------------------------------------------------------------------------

@dataclass
class PlantTarget:
    """
    Carries a resolved PlantState and enough context to write it back.

    Room target:  room_id + plot_index are set, pot_state is None.
    Pot target:   pot_state is set, room_id is None.

    After mutating target.plant, pass the target to GardenManager._commit()
    to persist the change to the right place.
    """
    plant: PlantState
    plot_id: str

    # Room path
    room_id: Any = None
    plot_index: int = -1

    # Pot path
    pot_state: dict | None = None

    @property
    def is_pot(self) -> bool:
        return self.pot_state is not None


class GardenManager:
    """
    Persistence + orchestration layer for the garden.
    """

    _JSON_FILENAME = "garden_data.json"

    def __init__(self, open_meteo, room_definitions: list, base_path: str):
        self.open_meteo = open_meteo
        self.settings   = GARDEN_SETTINGS

        save_dir       = Path(base_path) / "Garden_Data"
        save_dir.mkdir(parents=True, exist_ok=True)
        self._filepath = save_dir / self._JSON_FILENAME

        self.simulation = GardenSimulation(plant_types, self.settings)

        self._state: dict[str, Any] = self._load()

        if "_last_rain_applied_timestamp" not in self._state:
            self._state["_last_rain_applied_timestamp"] = datetime.now().isoformat()
        self._logical_tick: int = self._state.get("_garden_logical_tick_counter", 0)

        self._initialize_plots(room_definitions)

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    def _load(self) -> dict:
        if not self._filepath.exists():
            return {}
        try:
            with self._filepath.open("r") as f:
                raw = json.load(f)
            coerced = {}
            for k, v in raw.items():
                try:
                    coerced[int(k)] = v
                except (ValueError, TypeError):
                    coerced[k] = v
            return coerced
        except (json.JSONDecodeError, OSError) as exc:
            print(f"GardenManager: failed to load state ({exc}). Starting fresh.")
            return {}

    def _save(self) -> None:
        self._state["_garden_logical_tick_counter"] = self._logical_tick
        try:
            with self._filepath.open("w") as f:
                json.dump(self._state, f, indent=2)
        except OSError as exc:
            print(f"GardenManager: failed to save state: {exc}")

    # -----------------------------------------------------------------------
    # Plot initialization
    # -----------------------------------------------------------------------

    def _initialize_plots(self, room_definitions: list) -> None:
        for room in room_definitions:
            if not (
                isinstance(room.extra_data.get("plot_number"), int)
                and room.extra_data.get("plot_number") > 0
            ):
                continue

            plot_number = room.extra_data["plot_number"]
            room_key    = room.id

            if room_key not in self._state:
                self._state[room_key] = {"room_id": room.id, "plots": []}
                print(f"GardenManager: added garden '{room.name}' (id={room.id}).")

            garden   = self._state[room_key]
            existing = garden.get("plots", [])

            if len(existing) != plot_number:
                new_plots = []
                for i in range(plot_number):
                    pid   = f"plot{i + 1}"
                    found = next((p for p in existing if p.get("plot_id") == pid), None)
                    new_plots.append(found if found else {"plot_id": pid, "plants": []})
                garden["plots"] = new_plots
                print(f"GardenManager: '{room.name}' re-initialized to {plot_number} plots.")
            else:
                for plot in existing:
                    if not isinstance(plot.get("plants"), list):
                        plot["plants"] = []

        self._save()

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _get_garden(self, room_id) -> dict | None:
        return self._state.get(room_id)

    def _get_plot(self, room_id, plot_id: str) -> tuple[dict | None, int]:
        garden = self._get_garden(room_id)
        if not garden:
            return None, -1
        for i, plot in enumerate(garden.get("plots", [])):
            if plot.get("plot_id") == plot_id:
                return plot, i
        return None, -1

    def _all_existing_uids(self) -> set[str]:
        """Collect all plant UIDs in room gardens. Controller adds pot UIDs."""
        uids: set[str] = set()
        for val in self._state.values():
            if not isinstance(val, dict) or "room_id" not in val:
                continue
            for plot in val.get("plots", []):
                for p in plot.get("plants", []):
                    if uid := p.get("_plant_UID"):
                        uids.add(uid)
        return uids

    def _get_rain(self) -> float:
        try:
            return self.open_meteo.get_structured_weather().get("precipitation", 0.0)
        except Exception as exc:
            print(f"GardenManager: weather error — {exc}")
            return 0.0

    # -----------------------------------------------------------------------
    # PlantTarget — resolve and commit
    # -----------------------------------------------------------------------

    def _resolve(
        self,
        plot_id: str,
        room_id=None,
        pot_state: dict | None = None,
    ) -> tuple[PlantTarget | None, str]:
        """
        Resolve a plot_id into a PlantTarget, reading the plant from either
        the room garden JSON or a pot_state dict.
        Returns (target, error).  error is empty string on success.
        """
        if pot_state is not None:
            slot = next(
                (s for s in pot_state.get("slots", []) if s.get("slot_id") == plot_id),
                None,
            )
            if slot is None:
                return None, f"Slot '{plot_id}' not found in this pot."

            plant_raw = slot.get("plant")
            if not plant_raw:
                return None, f"Slot '{plot_id}' is empty."

            return PlantTarget(
                plant=PlantState.from_dict(plant_raw),
                plot_id=plot_id,
                pot_state=pot_state,
            ), ""

        else:
            garden = self._get_garden(room_id)
            if not garden:
                return None, f"Room '{room_id}' is not a registered garden."

            plot, plot_index = self._get_plot(room_id, plot_id)
            if plot is None:
                return None, f"Plot '{plot_id}' not found in garden '{room_id}'."
            if not plot.get("plants"):
                return None, f"Plot '{plot_id}' is empty."

            return PlantTarget(
                plant=PlantState.from_dict(plot["plants"][0]),
                plot_id=plot_id,
                room_id=room_id,
                plot_index=plot_index,
            ), ""

    def _commit(self, target: PlantTarget) -> dict | None:
        """
        Write the mutated plant back to its source.
        Room: saves to garden_data.json, returns None.
        Pot:  returns updated pot_state dict (controller writes to item).
        """
        if target.is_pot:
            pot_state = dict(target.pot_state)
            pot_state["slots"] = [dict(s) for s in pot_state["slots"]]
            slot = next(
                s for s in pot_state["slots"]
                if s.get("slot_id") == target.plot_id
            )
            slot["plant"] = target.plant.to_dict()
            return pot_state
        else:
            garden = self._get_garden(target.room_id)
            garden["plots"][target.plot_index]["plants"] = [target.plant.to_dict()]
            self._save()
            return None

    def _clear(self, target: PlantTarget) -> dict | None:
        """
        Remove the plant from its plot/slot.
        Room: clears and saves, returns None.
        Pot:  returns updated pot_state dict (controller writes to item).
        """
        if target.is_pot:
            pot_state = dict(target.pot_state)
            pot_state["slots"] = [dict(s) for s in pot_state["slots"]]
            slot = next(
                s for s in pot_state["slots"]
                if s.get("slot_id") == target.plot_id
            )
            slot["plant"] = None
            return pot_state
        else:
            garden = self._get_garden(target.room_id)
            garden["plots"][target.plot_index]["plants"] = []
            self._save()
            return None

    # -----------------------------------------------------------------------
    # Game loop
    # -----------------------------------------------------------------------

    def tick(self) -> dict[str, list[GardenEvent]]:
        """
        Advance all room-garden plants by one logical tick.
        Pot plants are ticked by the controller via tick_pot().
        Returns room_id → list of GardenEvents.
        """
        self._logical_tick += 1
        tick = self._logical_tick

        now           = datetime.now()
        last_rain_str = self._state.get("_last_rain_applied_timestamp")
        last_rain_dt  = datetime.fromisoformat(last_rain_str) if last_rain_str else now
        rain_level    = self._get_rain()
        cooldown      = timedelta(minutes=self.settings["RAIN_COOLDOWN_MINUTES"])
        apply_rain    = rain_level > 0.0 and (now - last_rain_dt) >= cooldown

        if apply_rain:
            self._state["_last_rain_applied_timestamp"] = now.isoformat()

        all_events: dict[str, list[GardenEvent]] = {}

        for room_key, garden in self._state.items():
            if not isinstance(garden, dict) or "room_id" not in garden:
                continue

            room_events: list[GardenEvent] = []
            for plot in garden.get("plots", []):
                if not plot.get("plants"):
                    continue
                plant = PlantState.from_dict(plot["plants"][0])
                plant, events = self.simulation.tick_plant(plant, tick, rain_level, apply_rain)
                plot["plants"] = [plant.to_dict()]
                room_events.extend(events)

            if room_events:
                all_events[room_key] = room_events

        self._save()
        return all_events

    def tick_pot(
        self,
        pot_state: dict,
        rain_level: float = 0.0,
        apply_rain: bool = False,
    ) -> tuple[dict, list[GardenEvent]]:
        """
        Advance all slots in a single pot by one logical tick.
        Rain params supplied by the controller based on room type.
        Returns (updated_pot_state, events).
        """
        all_events: list[GardenEvent] = []
        pot_state     = dict(pot_state)
        updated_slots = []

        for slot in pot_state.get("slots", []):
            slot      = dict(slot)
            plant_raw = slot.get("plant")
            if plant_raw:
                plant = PlantState.from_dict(plant_raw)
                plant, events = self.simulation.tick_plant(
                    plant, self._logical_tick, rain_level=rain_level, apply_rain=apply_rain
                )
                slot["plant"] = plant.to_dict()
                all_events.extend(events)
            updated_slots.append(slot)

        pot_state["slots"] = updated_slots
        return pot_state, all_events

    # -----------------------------------------------------------------------
    # Planting
    # Separate from the unified actions because an empty plot/slot is valid
    # here — it's the starting condition, not an error.
    # -----------------------------------------------------------------------

    def plant_seed(
        self,
        plot_id: str,
        plant_type: str,
        known_uids: set[str],
        room_id=None,
        pot_state: dict | None = None,
    ) -> tuple[dict | None, str, bool]:
        """
        Plant a seed into a room plot or pot slot.
        Returns (updated_pot_state_or_None, message, success).
        Controller consumes the seed item on success.
        """
        if pot_state is not None:
            capacity = pot_state.get("capacity", 1)
            slot     = next(
                (s for s in pot_state.get("slots", []) if s.get("slot_id") == plot_id),
                None,
            )

            if slot is not None and slot.get("plant"):
                return None, f"Slot '{plot_id}' is already occupied. Harvest or remove it first.", False

            if slot is None and len(pot_state.get("slots", [])) >= capacity:
                return None, f"This pot is full ({capacity} slot(s) used).", False

            plant, err = self.simulation.create_plant(plant_type, self._logical_tick, known_uids)
            if err:
                return None, err, False

            pot_state = dict(pot_state)
            pot_state["slots"] = [dict(s) for s in pot_state["slots"]]

            if slot is None:
                pot_state["slots"].append({"slot_id": plot_id, "plant": plant.to_dict()})
            else:
                target_slot = next(s for s in pot_state["slots"] if s["slot_id"] == plot_id)
                target_slot["plant"] = plant.to_dict()

            return (
                pot_state,
                f"Planted {plant_type} (UID: {plant.plant_uid}) in slot {plot_id}. "
                f"Stage: '{plant.current_stage_name}'.",
                True,
            )

        else:
            garden = self._get_garden(room_id)
            if not garden:
                return None, f"Room '{room_id}' is not a registered garden.", False

            plot, _ = self._get_plot(room_id, plot_id)
            if plot is None:
                return None, f"Plot '{plot_id}' not found in garden '{room_id}'.", False
            if plot.get("plants"):
                return None, f"Plot '{plot_id}' is occupied. Harvest before planting.", False

            plant, err = self.simulation.create_plant(plant_type, self._logical_tick, known_uids)
            if err:
                return None, err, False

            plot["plants"] = [plant.to_dict()]
            self._save()

            return (
                None,
                f"Planted {plant_type} (UID: {plant.plant_uid}) in plot {plot_id} "
                f"(garden {room_id}). Stage: '{plant.current_stage_name}'.",
                True,
            )

    # -----------------------------------------------------------------------
    # Unified player actions
    # All return (updated_pot_state_or_None, message, success).
    # updated_pot_state is None for room targets (manager saved internally).
    # Controller writes pot_state back to the item when not None.
    # -----------------------------------------------------------------------

    def water_plant(
        self,
        plot_id: str,
        water_level_type: str,
        room_id=None,
        pot_state: dict | None = None,
    ) -> tuple[dict | None, str, bool]:
        target, err = self._resolve(plot_id, room_id, pot_state)
        if err:
            return None, err, False

        plant, msg, _, success = self.simulation.apply_water(target.plant, water_level_type)
        if not success:
            return None, msg, False

        target.plant = plant
        updated      = self._commit(target)
        return updated, msg, True

    def check_plant(
        self,
        plot_id: str,
        room_id=None,
        pot_state: dict | None = None,
    ) -> tuple[dict | None, str, bool]:
        """
        Check never mutates — updated_pot_state is always None.
        Empty plot/slot returns success=True with a descriptive message.
        """
        target, err = self._resolve(plot_id, room_id, pot_state)
        if err:
            return None, err, "is empty" not in err

        plant   = target.plant
        elapsed = self._logical_tick - plant.planted_logical_tick
        w_desc  = self.simulation.describe_water_status(plant)
        w_state = self.simulation.get_water_state(plant)
        w_label = {0: "Low", 1: "Optimal", 2: "High"}.get(w_state, "Unknown")
        label   = "slot" if pot_state is not None else "plot"

        msg = (
            f"{plant.plant_type} (UID: {plant.plant_uid}) in {label} {plot_id} — "
            f"stage: {plant.current_stage_name} ({elapsed} logical ticks elapsed). "
            f"Water: {plant.water_level:.2f} ({w_label}) — {w_desc}"
        )
        return None, msg, True

    def harvest_plant(
        self,
        plot_id: str,
        room_id=None,
        pot_state: dict | None = None,
    ) -> tuple[dict | None, str, list[dict], bool]:
        """
        Returns (updated_pot_state_or_None, message, harvested_items, success).
        """
        target, err = self._resolve(plot_id, room_id, pot_state)
        if err:
            return None, err, [], False

        harvest_result, err = self.simulation.calculate_harvest(target.plant)
        if err:
            return None, err, [], False

        size_multiplier = float(pot_state.get("size_multiplier", 1.0)) if pot_state else 1.0
        raw_items       = harvest_result["harvested_items_with_quantities"]
        items           = [
            {**entry, "quantity": max(1, round(entry.get("quantity", 1) * size_multiplier))}
            for entry in raw_items
        ]

        quality      = harvest_result["life_cycle_quality"]
        penalty      = harvest_result["penalty"]
        bonus        = harvest_result["bonus"]
        q_msg        = self.simulation.get_quality_messages().get(quality, "")
        quality_line = (
            f"Life cycle quality: '{quality}'. {q_msg} "
            f"Penalty: {penalty:.0f}, Bonus: {bonus:.0f}."
        )
        if size_multiplier != 1.0:
            quality_line += f" Size multiplier: ×{size_multiplier}."

        info       = self.simulation.get_plant_types().get(target.plant.plant_type, {})
        life_cycle = info.get("life_cycle", "annual")
        label      = "slot" if pot_state is not None else "plot"

        if life_cycle == "perennial":
            updated_plant, perennial_err = self.simulation.reset_perennial(
                target.plant, self._logical_tick
            )
            if perennial_err:
                updated = self._clear(target)
                suffix  = f"Cleared (perennial reset failed: {perennial_err})."
            else:
                target.plant = updated_plant
                updated      = self._commit(target)
                suffix       = "Plant reset to 'mature' stage and will regrow."
        else:
            updated = self._clear(target)
            suffix  = f"Annual plant removed. {label.capitalize()} is now empty."

        msg = (
            f"Harvested {target.plant.plant_type} (UID: {target.plant.plant_uid}) "
            f"from {label} {plot_id}. {quality_line} {suffix}"
        )
        return updated, msg, items, True

    def remove_plant(
        self,
        plot_id: str,
        room_id=None,
        pot_state: dict | None = None,
    ) -> tuple[dict | None, str, bool]:
        target, err = self._resolve(plot_id, room_id, pot_state)
        if err:
            return None, err, False

        plant_type = target.plant.plant_type
        plant_uid  = target.plant.plant_uid
        label      = "slot" if pot_state is not None else "plot"
        updated    = self._clear(target)

        return (
            updated,
            f"Removed {plant_type} (UID: {plant_uid}) from {label} {plot_id}.",
            True,
        )

    # -----------------------------------------------------------------------
    # Status queries
    # -----------------------------------------------------------------------

    def get_garden_summary(self, room_id, room_name: str = "") -> str:
        garden = self._get_garden(room_id)
        if not garden:
            return f"Room '{room_id}' is not a registered garden."

        label = room_name or str(room_id)
        lines = [f"--- Garden Summary: {label} (ID: {room_id}) ---"]

        for plot in garden.get("plots", []):
            pid = plot.get("plot_id", "?")
            if not plot.get("plants"):
                lines.append(f"  Plot {pid}: Empty.")
                continue

            plant = PlantState.from_dict(plot["plants"][0])
            lines.append(
                f"  Plot {pid}:\n"
                f"    Plant : {plant.plant_type} (UID: {plant.plant_uid})"
            )

        return "\n".join(lines)

    def get_pot_summary(self, pot_state: dict, pot_name: str = "Pot") -> str:
        capacity        = pot_state.get("capacity", "?")
        size_multiplier = pot_state.get("size_multiplier", 1.0)
        lines = [
            f"--- {pot_name} "
            f"(capacity: {capacity}, size multiplier: ×{size_multiplier}) ---"
        ]

        slots     = pot_state.get("slots", [])
        slots_map = {s.get("slot_id"): s for s in slots}
        cap_int   = capacity if isinstance(capacity, int) else 0

        for i in range(cap_int):
            sid  = f"slot{i + 1}"
            slot = slots_map.get(sid)

            if slot is None or not slot.get("plant"):
                lines.append(f"  Slot {sid}: Empty.")
                continue

            plant = PlantState.from_dict(slot["plant"])
            lines.append(
                f"  Slot {sid}:\n"
                f"    Plant : {plant.plant_type} (UID: {plant.plant_uid})"
            )

        return "\n".join(lines)