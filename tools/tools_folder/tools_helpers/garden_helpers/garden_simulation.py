"""
Garden Simulation
=================

Pure garden logic. No I/O, no file system, no state manager calls.

Architecture:
    GardenSimulation (orchestration)
        ├─> GardenPlot     (per-plot/plant tick, growth, water logic)
        └─> HarvestCalculator (pure yield math)
"""

from __future__ import annotations

import math
import random
import string
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@dataclass
class GardenEvent:
    message: str
    event_type: str  # e.g. "stage_change", "overwatered", "ready_to_harvest"


# ---------------------------------------------------------------------------
# Plant state  (the living record stored per plant)
# ---------------------------------------------------------------------------

@dataclass
class PlantState:
    plant_type: str
    plant_uid: str
    planted_logical_tick: int
    water_level: float
    current_stage_index: int
    current_stage_name: str
    water_history: list[int]
    last_ticked_logical_tick: int
    last_water_history_recorded_logical_tick: int

    def to_dict(self) -> dict:
        return {
            "plant_type": self.plant_type,
            "_plant_UID": self.plant_uid,
            "planted_logical_tick": self.planted_logical_tick,
            "water_level": self.water_level,
            "current_stage_index": self.current_stage_index,
            "current_stage_name": self.current_stage_name,
            "water_history": self.water_history,
            "_last_ticked_logical_tick": self.last_ticked_logical_tick,
            "_last_water_history_recorded_logical_tick": self.last_water_history_recorded_logical_tick,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlantState":
        return cls(
            plant_type=d["plant_type"],
            plant_uid=d["_plant_UID"],
            planted_logical_tick=d["planted_logical_tick"],
            water_level=d.get("water_level", 0.5),
            current_stage_index=d.get("current_stage_index", 0),
            current_stage_name=d.get("current_stage_name", ""),
            water_history=d.get("water_history", []),
            last_ticked_logical_tick=d.get("_last_ticked_logical_tick", 0),
            last_water_history_recorded_logical_tick=d.get("_last_water_history_recorded_logical_tick", 0),
        )


# ---------------------------------------------------------------------------
# Harvest Calculator  (pure math, no side effects)
# ---------------------------------------------------------------------------

class HarvestCalculator:
    """
    Stateless yield calculator.  All settings injected at construction.
    """

    def __init__(self, settings: dict):
        self._s = settings

    def calculate(self, plant: PlantState, plant_type_info: dict) -> dict:
        """
        Returns:
            {
                "harvested_items_with_quantities": [{"item": ..., "quantity": int}, ...],
                "life_cycle_quality": str,
                "penalty": int,
                "bonus": int,
            }
        """
        history = plant.water_history
        optimal   = history.count(1)
        low       = history.count(0)
        high      = history.count(2)
        non_opt   = low + high

        penalty = math.floor(
            math.log(
                1 + non_opt / self._s["PENALTY_SENSITIVITY_FACTOR"],
                self._s["PENALTY_LOG_BASE"],
            )
        )
        bonus = math.floor(
            math.log(
                1 + optimal / self._s["BONUS_SENSITIVITY_FACTOR"],
                self._s["BONUS_LOG_BASE"],
            ) * self._s["BONUS_PER_LOG_STEP"]
        )

        items = []
        for harvest_def in plant_type_info.get("harvest_items", []):
            item_def   = harvest_def.get("item")
            base_yield = harvest_def.get("base_harvest_yield", 1)
            if not item_def:
                continue
            if base_yield > 0:
                final = max(1, math.floor(base_yield + bonus - penalty))
            else:
                final = 0
            if final > 0:
                items.append({"item": item_def, "quantity": final})

        return {
            "harvested_items_with_quantities": items,
            "life_cycle_quality": self._describe_quality(penalty, bonus),
            "penalty": penalty,
            "bonus": bonus,
        }

    @staticmethod
    def _describe_quality(penalty: int, bonus: int) -> str:
        if penalty == 0 and bonus > 0:
            return "excellent"
        elif bonus == 0 and penalty > 0:
            return "bad"
        elif penalty > bonus:
            return "poor"
        elif penalty < bonus:
            return "good"
        else:
            return "average"


# ---------------------------------------------------------------------------
# Garden Plot  (single-plot simulation: tick, water, growth)
# ---------------------------------------------------------------------------

class GardenPlot:
    """
    Encapsulates all logic for one plot's plant.
    The manager creates one GardenPlot per plot and delegates ticks and
    mutations to it.  The plot itself is stateless between calls — all
    mutable state lives in PlantState dicts which the manager serialises.
    """

    def __init__(self, plant_types: dict, settings: dict):
        self._plant_types = plant_types
        self._s = settings
        self.harvest_calculator = HarvestCalculator(settings)

    # --- Stage helpers ---------------------------------------------------

    def get_current_stage_index(self, plant_type_info: dict, elapsed_ticks: int) -> int:
        cumulative = 0
        stages = plant_type_info["stages"]
        for i, stage in enumerate(stages):
            if i == len(stages) - 1 and stage["duration_ticks"] == 0:
                if elapsed_ticks >= cumulative:
                    return i
            cumulative += stage["duration_ticks"]
            if elapsed_ticks < cumulative:
                return i
        return len(stages) - 1

    def get_water_state(self, plant: PlantState, plant_type_info: dict) -> int:
        """0=low, 1=optimal, 2=overwatered"""
        idx = min(plant.current_stage_index, len(plant_type_info["stages"]) - 1)
        lo, hi = plant_type_info["stages"][idx]["optimal_water_level_range"]
        if plant.water_level < lo:
            return 0
        elif plant.water_level > hi:
            return 2
        return 1

    # --- UID generation --------------------------------------------------

    def generate_uid(self, existing_uids: set[str]) -> str:
        while True:
            uid = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if uid not in existing_uids:
                return uid

    # --- Plant creation --------------------------------------------------

    def create_plant(
        self,
        plant_type: str,
        current_logical_tick: int,
        existing_uids: set[str],
    ) -> tuple[PlantState | None, str]:
        """
        Returns (PlantState, error_message).  error_message is empty on success.
        """
        if plant_type not in self._plant_types:
            known = ", ".join(self._plant_types.keys())
            return None, f"Plant type '{plant_type}' is not recognised. Available: {known}."

        info  = self._plant_types[plant_type]
        idx   = self.get_current_stage_index(info, 0)
        uid   = self.generate_uid(existing_uids)

        state = PlantState(
            plant_type=plant_type,
            plant_uid=uid,
            planted_logical_tick=current_logical_tick,
            water_level=self._s["DEFAULT_INITIAL_WATER_LEVEL"],
            current_stage_index=idx,
            current_stage_name=info["stages"][idx]["name"],
            water_history=[],
            last_ticked_logical_tick=current_logical_tick,
            last_water_history_recorded_logical_tick=current_logical_tick,
        )
        return state, ""

    # --- Watering --------------------------------------------------------

    def apply_water(
        self,
        plant: PlantState,
        water_level_type: str,
    ) -> tuple[PlantState, str, str, bool]:
        """
        Returns (updated_plant, result_message, water_status_desc, success).
        """
        amounts: dict[str, float] = self._s["WATERING_AMOUNTS"]
        amount = amounts.get(water_level_type.lower())
        if amount is None:
            return plant, f"Invalid water type '{water_level_type}'. Choose from: {', '.join(amounts)}.", "", False

        plant.water_level = min(1.0, max(0.0, plant.water_level + amount))

        info  = self._plant_types.get(plant.plant_type)
        state = self.get_water_state(plant, info) if info else -1
        descs = {0: "still needs more water.", 1: "now has optimal water levels.", 2: "is now overwatered."}
        desc  = descs.get(state, "optimal water level is unknown.")

        msg = (
            f"Applied {water_level_type} water to {plant.plant_type} (UID: {plant.plant_uid}). "
            f"Water level is now {plant.water_level:.2f} — it {desc}"
        )
        return plant, msg, desc, True

    # --- Tick a single plant ---------------------------------------------

    def tick_plant(
        self,
        plant: PlantState,
        current_logical_tick: int,
        rain_level: float,
        apply_rain: bool,
    ) -> tuple[PlantState, list[GardenEvent]]:
        """
        Advances one plant by however many ticks have elapsed.
        Returns the mutated PlantState and any events that occurred.
        """
        events: list[GardenEvent] = []

        ticks_elapsed = current_logical_tick - plant.last_ticked_logical_tick
        if ticks_elapsed <= 0:
            plant.last_ticked_logical_tick = current_logical_tick
            return plant, events

        plant.last_ticked_logical_tick = current_logical_tick

        info = self._plant_types.get(plant.plant_type)
        if not info:
            return plant, events

        # Rain
        if apply_rain:
            gain = rain_level * self._s["RAIN_WATER_APPLY_MULTIPLIER"] * ticks_elapsed
            plant.water_level = min(1.0, plant.water_level + gain)
            events.append(GardenEvent(
                message=f"Plant {plant.plant_uid} gained water from rain → {plant.water_level:.2f}",
                event_type="rain_applied",
            ))

        # Depletion
        rate = info.get("water_depletion_rate_per_tick", self._s["DEFAULT_WATER_DEPLETION_RATE_PER_TICK"])
        plant.water_level = max(0.0, plant.water_level - rate * ticks_elapsed)

        # Growth / stage
        elapsed_total = current_logical_tick - plant.planted_logical_tick
        old_idx = plant.current_stage_index
        new_idx = self.get_current_stage_index(info, elapsed_total)
        plant.current_stage_index = new_idx
        plant.current_stage_name  = info["stages"][new_idx]["name"]

        if new_idx > old_idx:
            plant.water_level = max(0.0, plant.water_level - self._s["WATER_LOSS_ON_STAGE_CHANGE"])
            events.append(GardenEvent(
                message=f"Plant {plant.plant_uid} advanced to stage '{plant.current_stage_name}'.",
                event_type="stage_change",
            ))
            if plant.current_stage_name == "harvestable":
                events.append(GardenEvent(
                    message=f"Plant {plant.plant_uid} ({plant.plant_type}) is ready to harvest!",
                    event_type="ready_to_harvest",
                ))

        # Water history
        water_state = self.get_water_state(plant, info)
        history     = plant.water_history
        ticks_since_record = current_logical_tick - plant.last_water_history_recorded_logical_tick

        if not history:
            history.append(water_state)
            plant.last_water_history_recorded_logical_tick = current_logical_tick
        elif ticks_since_record >= self._s["RECORD_WATER_HISTORY_INTERVAL_TICKS"]:
            history.append(water_state)
            plant.last_water_history_recorded_logical_tick = current_logical_tick
        elif history and history[-1] != water_state:
            history[-1] = water_state

        plant.water_history = history
        return plant, events

    # --- Harvest ---------------------------------------------------------

    def calculate_harvest(
        self,
        plant: PlantState,
    ) -> tuple[dict | None, str]:
        """
        Returns (harvest_result_dict, error_message).
        """
        if plant.current_stage_name != "harvestable":
            return None, (
                f"Plant {plant.plant_type} (UID: {plant.plant_uid}) is not yet harvestable. "
                f"Currently in stage '{plant.current_stage_name}'."
            )
        info = self._plant_types.get(plant.plant_type)
        if not info:
            return None, f"Plant type '{plant.plant_type}' is not recognised."

        result = self.harvest_calculator.calculate(plant, info)
        return result, ""

    def reset_perennial(
        self,
        plant: PlantState,
        current_logical_tick: int,
    ) -> tuple[PlantState | None, str]:
        """
        Resets a perennial plant to its 'mature' stage after harvest.
        Returns (updated_plant, error_message).
        """
        info = self._plant_types.get(plant.plant_type)
        if not info:
            return None, f"Plant type '{plant.plant_type}' not recognised."

        mature_idx = -1
        ticks_to_mature = 0
        for i, stage in enumerate(info["stages"]):
            if stage["name"] == "mature":
                mature_idx = i
                break
            ticks_to_mature += stage["duration_ticks"]

        if mature_idx == -1:
            return None, f"Perennial plant '{plant.plant_type}' has no 'mature' stage defined."

        plant.planted_logical_tick = current_logical_tick - ticks_to_mature
        plant.current_stage_index  = mature_idx
        plant.current_stage_name   = info["stages"][mature_idx]["name"]
        plant.water_level          = self._s["DEFAULT_INITIAL_WATER_LEVEL"]
        plant.water_history        = []
        plant.last_water_history_recorded_logical_tick = current_logical_tick
        plant.last_ticked_logical_tick                 = current_logical_tick
        return plant, ""

    # --- Inspection helpers ----------------------------------------------

    def describe_water_status(self, plant: PlantState) -> str:
        info = self._plant_types.get(plant.plant_type)
        if not info:
            return "Water status unknown."
        state = self.get_water_state(plant, info)
        return {0: "needs more water.", 1: "has optimal water levels.", 2: "is overwatered."}.get(state, "")

    def get_quality_messages(self) -> dict[str, str]:
        return self._s.get("LIFE_CYCLE_QUALITY_MESSAGES", {})


# ---------------------------------------------------------------------------
# GardenSimulation  (top-level facade the manager talks to)
# ---------------------------------------------------------------------------

class GardenSimulation:
    """
    Coordinates GardenPlot and HarvestCalculator.
    The manager passes raw plot/plant dicts in and gets them back mutated;
    serialisation lives entirely in the manager.
    """

    def __init__(self, plant_types: dict, settings: dict):
        self.plot = GardenPlot(plant_types, settings)
        self._plant_types = plant_types
        self._s = settings

    # Delegate everything through self.plot so the manager only needs one reference.

    def create_plant(self, plant_type, tick, existing_uids):
        return self.plot.create_plant(plant_type, tick, existing_uids)

    def apply_water(self, plant: PlantState, water_level_type: str):
        return self.plot.apply_water(plant, water_level_type)

    def tick_plant(self, plant: PlantState, tick, rain_level, apply_rain):
        return self.plot.tick_plant(plant, tick, rain_level, apply_rain)

    def calculate_harvest(self, plant: PlantState):
        return self.plot.calculate_harvest(plant)

    def reset_perennial(self, plant: PlantState, tick):
        return self.plot.reset_perennial(plant, tick)

    def get_water_state(self, plant: PlantState):
        info = self._plant_types.get(plant.plant_type)
        if not info:
            return -1
        return self.plot.get_water_state(plant, info)

    def describe_water_status(self, plant: PlantState) -> str:
        return self.plot.describe_water_status(plant)

    def get_quality_messages(self) -> dict:
        return self.plot.get_quality_messages()

    def get_plant_types(self) -> dict:
        return self._plant_types