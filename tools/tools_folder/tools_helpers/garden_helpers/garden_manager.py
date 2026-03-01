"""
Garden Manager
==============

Thin persistence layer for the garden.

Responsibilities:
- Load / save state to JSON  (own implementation, no GenericJsonTool)
- Initialize plots from room definitions supplied by the caller
- Delegate all simulation logic to GardenSimulation
- Track the logical tick counter and rain cooldown timestamps
- IDs are treated as ints throughout; plot_ids remain "plot1", "plot2", etc.

Architecture:
    GardenManager (persistence + orchestration)
        └─> GardenSimulation
                ├─> GardenPlot
                └─> HarvestCalculator
"""

from __future__ import annotations

import json
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


class GardenManager:
    """
    Persistence + orchestration layer for the garden.
    Mirrors the role of LighthouseManager.
    """

    _JSON_FILENAME = "garden_data.json"

    def __init__(self, open_meteo, room_definitions: list[dict], base_path: str):
        """
        Args:
            open_meteo:        Weather provider (has .get_structured_weather()).
            room_definitions:  List of room dicts from the state store
                               (each may have "room_types" and "plot_number").
            base_path:         Root path for save data.
        """
        self.open_meteo    = open_meteo
        self.settings      = GARDEN_SETTINGS

        # Build the path mirroring LighthouseManager's pattern
        save_dir       = Path(base_path) / "Garden_Data"
        save_dir.mkdir(parents=True, exist_ok=True)
        self._filepath = save_dir / self._JSON_FILENAME

        # Simulation facade
        self.simulation = GardenSimulation(plant_types, self.settings)

        # Load persisted state (or start fresh)
        self._state: dict[str, Any] = self._load()

        # Ensure global counters exist
        if "_last_rain_applied_timestamp" not in self._state:
            self._state["_last_rain_applied_timestamp"] = datetime.now().isoformat()
        self._logical_tick: int = self._state.get("_garden_logical_tick_counter", 0)

        # Sync plot structure from current room definitions
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
            # Coerce room_id keys back to int, leave internal keys alone
            coerced = {}
            for k, v in raw.items():
                try:
                    coerced[int(k)] = v
                except (ValueError, TypeError):
                    coerced[k] = v  # preserve non-room keys like "_last_rain_applied_timestamp"
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
    # Plot initialisation
    # -----------------------------------------------------------------------


    def _initialize_plots(self, room_definitions: list[RoomDataResult]) -> None:
        for room in room_definitions:
            if not (
                "planting_garden" in room.room_types
                and isinstance(room.extra_data.get("plot_number"), int)
                and room.extra_data.get("plot_number") > 0
            ):
                continue

            plot_number = room.extra_data["plot_number"]
            room_key = room.id

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
        """Returns (plot_dict, index) or (None, -1)."""
        garden = self._get_garden(room_id)
        if not garden:
            return None, -1
        for i, plot in enumerate(garden.get("plots", [])):
            if plot.get("plot_id") == plot_id:
                return plot, i
        return None, -1

    def _get_plant(self, room_id, plot_id: str) -> PlantState | None:
        plot, _ = self._get_plot(room_id, plot_id)
        if not plot or not plot.get("plants"):
            return None
        return PlantState.from_dict(plot["plants"][0])

    def _save_plant(self, room_id, plot_id: str, plant: PlantState) -> None:
        plot, _ = self._get_plot(room_id, plot_id)
        if plot is not None:
            plot["plants"] = [plant.to_dict()]

    def _remove_plant(self, room_id, plot_index: int) -> None:
        garden = self._get_garden(room_id)
        if garden:
            garden["plots"][plot_index]["plants"] = []

    def _all_existing_uids(self) -> set[str]:
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
    # Game loop
    # -----------------------------------------------------------------------

    def tick(self) -> dict[str, list[GardenEvent]]:
        """
        Advance all plants by one logical tick.
        Returns a dict mapping room_id → list of GardenEvents that occurred.
        """
        self._logical_tick += 1
        tick = self._logical_tick

        # Rain cooldown (real-time based, as in original)
        now              = datetime.now()
        last_rain_str    = self._state.get("_last_rain_applied_timestamp")
        last_rain_dt     = datetime.fromisoformat(last_rain_str) if last_rain_str else now
        rain_level       = self._get_rain()
        cooldown         = timedelta(minutes=self.settings["RAIN_COOLDOWN_MINUTES"])
        apply_rain       = (
            rain_level > 0.0
            and (now - last_rain_dt) >= cooldown
        )
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

                plant  = PlantState.from_dict(plot["plants"][0])
                plant, events = self.simulation.tick_plant(plant, tick, rain_level, apply_rain)
                plot["plants"] = [plant.to_dict()]
                room_events.extend(events)

            if room_events:
                all_events[room_key] = room_events

        self._save()
        return all_events

    # -----------------------------------------------------------------------
    # Player actions
    # -----------------------------------------------------------------------

    def plant_seed(
        self,
        room_id,
        plot_id: str,
        plant_type: str,
    ) -> tuple[str, bool]:
        """
        Validate and place a new plant in a plot.
        Returns (message, success).
        The controller is responsible for consuming the seed item.
        """
        garden = self._get_garden(room_id)
        if not garden:
            return f"Room '{room_id}' is not a registered garden.", False

        plot, _ = self._get_plot(room_id, plot_id)
        if plot is None:
            return f"Plot '{plot_id}' not found in garden '{room_id}'.", False

        if plot.get("plants"):
            return f"Plot '{plot_id}' is occupied. Harvest before planting.", False

        plant, err = self.simulation.create_plant(plant_type, self._logical_tick, self._all_existing_uids())
        if err:
            return err, False

        plot["plants"] = [plant.to_dict()]
        self._save()

        return (
            f"Planted {plant_type} (UID: {plant.plant_uid}) in plot {plot_id} "
            f"(garden {room_id}). Stage: '{plant.current_stage_name}'.",
            True,
        )

    def water_plot(
        self,
        room_id,
        plot_id: str,
        water_level_type: str,
    ) -> tuple[str, bool]:
        """Returns (message, success)."""
        plant = self._get_plant(room_id, plot_id)
        if plant is None:
            plot, _ = self._get_plot(room_id, plot_id)
            if plot is None:
                return f"Plot '{plot_id}' not found.", False
            return f"Plot '{plot_id}' is empty.", False

        plant, msg, _, success = self.simulation.apply_water(plant, water_level_type)
        if success:
            self._save_plant(room_id, plot_id, plant)
            self._save()
        return msg, success

    def check_plant_state(
        self,
        room_id,
        plot_id: str,
    ) -> tuple[str, bool]:
        """Returns (message, success)."""
        garden = self._get_garden(room_id)
        if not garden:
            return f"Room '{room_id}' is not a registered garden.", False

        plot, _ = self._get_plot(room_id, plot_id)
        if plot is None:
            return f"Plot '{plot_id}' not found in garden '{room_id}'.", False

        if not plot.get("plants"):
            return f"Plot '{plot_id}' is empty.", True

        plant   = PlantState.from_dict(plot["plants"][0])
        elapsed = self._logical_tick - plant.planted_logical_tick
        w_desc  = self.simulation.describe_water_status(plant)
        w_state = self.simulation.get_water_state(plant)
        w_label = {0: "Low", 1: "Optimal", 2: "High"}.get(w_state, "Unknown")

        msg = (
            f"{plant.plant_type} (UID: {plant.plant_uid}) in plot {plot_id} — "
            f"stage: {plant.current_stage_name} ({elapsed} logical ticks elapsed). "
            f"Water: {plant.water_level:.2f} ({w_label}) — {w_desc}"
        )
        return msg, True

    def harvest_plant(
        self,
        room_id,
        plot_id: str,
    ) -> tuple[str, list[dict], bool]:
        """
        Returns (message, harvested_items_with_quantities, success).
        The controller handles inventory placement.
        """
        garden = self._get_garden(room_id)
        if not garden:
            return f"Room '{room_id}' is not a registered garden.", [], False

        plot, plot_index = self._get_plot(room_id, plot_id)
        if plot is None:
            return f"Plot '{plot_id}' not found.", [], False
        if not plot.get("plants"):
            return f"Plot '{plot_id}' is empty.", [], False

        plant = PlantState.from_dict(plot["plants"][0])

        harvest_result, err = self.simulation.calculate_harvest(plant)
        if err:
            return err, [], False

        items    = harvest_result["harvested_items_with_quantities"]
        quality  = harvest_result["life_cycle_quality"]
        penalty  = harvest_result["penalty"]
        bonus    = harvest_result["bonus"]

        q_msg   = self.simulation.get_quality_messages().get(quality, "")
        quality_line = (
            f"Life cycle quality: '{quality}'. {q_msg} "
            f"Penalty: {penalty:.0f}, Bonus: {bonus:.0f}."
        )

        info         = self.simulation.get_plant_types().get(plant.plant_type, {})
        life_cycle   = info.get("life_cycle", "annual")

        if life_cycle == "perennial":
            updated, err = self.simulation.reset_perennial(plant, self._logical_tick)
            if err:
                self._remove_plant(room_id, plot_index)
                self._save()
                return (
                    f"Harvested {plant.plant_type} (UID: {plant.plant_uid}) from {plot_id}. "
                    f"{quality_line} Plot cleared (perennial reset failed: {err}).",
                    items,
                    True,
                )
            self._save_plant(room_id, plot_id, updated)
            self._save()
            suffix = "Plant reset to 'mature' stage and will regrow."
        else:
            self._remove_plant(room_id, plot_index)
            self._save()
            suffix = "Annual plant removed. Plot is now empty."

        msg = (
            f"Harvested {plant.plant_type} (UID: {plant.plant_uid}) from plot {plot_id} "
            f"(garden {room_id}). {quality_line} {suffix}"
        )
        return msg, items, True

    def remove_plant(
        self,
        room_id,
        plot_id: str,
    ) -> tuple[str, bool]:
        """Forcibly clear a plot. Returns (message, success)."""
        plot, plot_index = self._get_plot(room_id, plot_id)
        if plot is None:
            return f"Plot '{plot_id}' not found.", False
        if not plot.get("plants"):
            return f"Plot '{plot_id}' is already empty.", False

        plant_type = plot["plants"][0].get("plant_type", "unknown")
        plant_uid  = plot["plants"][0].get("_plant_UID", "N/A")
        self._remove_plant(room_id, plot_index)
        self._save()
        return (
            f"Removed {plant_type} (UID: {plant_uid}) from plot {plot_id} "
            f"(garden {room_id}). Plot is now empty.",
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
        tick  = self._logical_tick

        for plot in garden.get("plots", []):
            pid = plot.get("plot_id", "?")
            if not plot.get("plants"):
                lines.append(f"  Plot {pid}: Empty.")
                continue

            plant   = PlantState.from_dict(plot["plants"][0])
            elapsed = tick - plant.planted_logical_tick
            w_state = self.simulation.get_water_state(plant)
            w_label = {0: "Low Water", 1: "Optimal Water", 2: "High Water"}.get(w_state, "Unknown")

            lines.append(
                f"  Plot {pid}:\n"
                f"    Plant : {plant.plant_type} (UID: {plant.plant_uid})\n"
                f"    Stage : {plant.current_stage_name} ({elapsed} logical ticks)\n"
                f"    Water : {plant.water_level:.2f} ({w_label})"
            )

        return "\n".join(lines)