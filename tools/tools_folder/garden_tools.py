# garden_tools.py

# This system is now tick based, the main runtime increments ticks based on a timer of its own

# States: 0 is low water, 1 is optimal, 2 is over-watered

# Inside the data folder there are plant structures that define their behavior, growth, life cycle type and water depletion rate per tick 

# Plants have different stages, they need at least the stage 'harvestable'; If they are perennial, they need a 'mature' stage. Each stage needs a tick lenght. For the harvestable stage the lenght has to be 0

# Plants have a list of nested item structures and base harvest number for each item

# Perennials revert to mature stage after harvesting, while annuals get removed from the plot directly.

from utils import open_meteo_handle
from utils.generic_json_tool import GenericJsonTool
import random
import string
import os
import math
from datetime import datetime, timedelta

from tools.tools_folder.tools_data.harvesting_data import (plant_types)

# Import the new settings from the garden_settings module
from tools.tools_folder.tools_data.garden_settings import GARDEN_SETTINGS


class Garden_Mananger(GenericJsonTool):
    """
    Manages the state of plants in various garden plots across different rooms.
    Uses GenericJsonTool to persist garden data.
    """

    _plant_types = plant_types

    def __init__(self, state_manager, signal):
        """
        Initializes the Garden_Mananger.
        Args:
            state_manager: An instance of the main state manager, used to access
                           room data and the base path for saving garden data,
                           and the current game tick.
        """
        self.json_filename = "garden_data.json"
        self.state_manager = state_manager
        self._signal_callback=signal

        # Load settings from the GARDEN_SETTINGS dictionary
        self.settings = GARDEN_SETTINGS
        
        # _default_state is an empty dictionary because the garden keys (room_ids)
        # are dynamic and populated based on the main state_manager's room definitions.
        self._default_state = {}
        
        base_path = self.state_manager.base_path
        super().__init__(base_path)
        
        # Initialize global rain tracking property if not present in loaded state
        # This key will be stored at the top level of the garden_data.json
        if "_last_rain_applied_timestamp" not in self._state:
            self._state["_last_rain_applied_timestamp"] = datetime.now().isoformat()
            # Persist this new key immediately if it's a new state file
            # or if the key was just added to an existing file.
            self._write_json(self._state) 
        
        # Initialize internal logical tick counter for the garden
        # This counter tracks how many "logical minutes" have passed for garden mechanics.
        self._garden_logical_tick_counter = self._state.get("_garden_logical_tick_counter", 0)

        # After GenericJsonTool initializes self._state (either from file or default),
        # ensure all garden rooms from the main state manager are reflected here.
        self._initialize_garden_plots()
    
    def _send_signal(self, signal_data):
        """Helper method to send signals using the registered callback."""
        if self._signal_callback:
            # print(f"{self.__class__.__name__} signaling: {signal_data}") # Optional: uncomment for debug
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from {self.__class__.__name__}: {e}")
        else:
            # print(f"{self.__class__.__name__} attempted to signal, but no callback registered: {signal_data}") # Optional: uncomment for debug
            pass # Silently fail if no callback is registered, or log loudly
    # ------------------------------------------------------

    def _initialize_garden_plots(self):
        """
        Ensures that all rooms marked as 'planting_garden' in the main state manager
        have corresponding entries in this Garden_Mananger's state file.
        It will add new gardens if they don't exist or adjust plot counts if changed.
        Existing plant data in plots will be preserved where possible.
        """
        rooms_list = self.state_manager._state.get("rooms", [])

        # Make a copy to modify safely, then assign back to self._state.
        # This preserves non-garden specific keys like "_last_rain_applied_timestamp" and "_garden_logical_tick_counter".
        updated_gardens_in_state = self._state.copy() 
        
        for room in rooms_list:
            room_id_raw = room.get("id")
            room_id = str(room_id_raw) # Crucial: Convert room_id to string for consistent key usage
            room_name = room.get("name")
            room_types = room.get("room_types", [])
            plot_count = room.get("plot_number")

            # Validate room as a garden
            if (isinstance(room_types, list) and "planting_garden" in room_types and
                isinstance(plot_count, int) and plot_count > 0):
                
                # If this garden room is new to our state, add its basic structure
                if room_id not in updated_gardens_in_state:
                    updated_gardens_in_state[room_id] = {
                        "room_id": room_id_raw, # Store original type if needed, but use string 'room_id' as key
                        "plots": []
                    }
                    print(f"Garden '{room_name}' (ID: {room_id}) added to garden manager state.")

                current_garden_data = updated_gardens_in_state[room_id]
                existing_plots = current_garden_data.get("plots", [])
                
                # Re-generate plots if the count doesn't match, preserving existing plant data
                if len(existing_plots) != plot_count:
                    new_plots = []
                    for i in range(plot_count):
                        plot_id = f"plot{i+1}"
                        # Try to find if this specific plot_id already exists in existing_plots
                        existing_plot_data = next((p for p in existing_plots if p.get("plot_id") == plot_id), None)
                        
                        if existing_plot_data:
                            # Preserve existing plot data including plants
                            new_plots.append(existing_plot_data)
                        else:
                            # Create a new, empty plot
                            new_plots.append({"plot_id": plot_id, "plants": []})
                    current_garden_data["plots"] = new_plots
                    print(f"Garden '{room_name}' (ID: {room_id}) plots re-initialized to {plot_count}.")
                else:
                    # If plot count matches, just ensure each plot has a 'plants' key as a list
                    for plot in existing_plots:
                        if "plants" not in plot or not isinstance(plot["plants"], list):
                            plot["plants"] = []
                            print(f"Warning: Plot {plot.get('plot_id')} in Garden {room_id} missing 'plants' key, initialized.")

        # Update the manager's state with the processed garden data
        self._state = updated_gardens_in_state
        self._write_json(self._state) # Persist changes immediately after initialization

    def _get_rain(self) -> float:
        """
        Retrieves the current precipitation level from the open_meteo_handle utility.
        Returns:
            float: The precipitation level (e.g., in mm/h), default to 0.0 if not available.
        """
        try:
            weather_data = open_meteo_handle.get_structured_weather()
            return weather_data.get("precipitation", 0.0)
        except Exception as e:
            print(f"Error getting weather data for rain: {e}")
            return 0.0

    def tick(self) -> None:
        """
        Advances the state of all plants in the garden based on logical game ticks.
        This function is intended to be called once per "logical game minute" by the game orchestrator.
        It handles natural water depletion, growth, and rain effects.
        """
        # Retrieve settings from self.settings
        RAIN_COOLDOWN_MINUTES = self.settings["RAIN_COOLDOWN_MINUTES"]
        RECORD_WATER_HISTORY_INTERVAL_TICKS = self.settings["RECORD_WATER_HISTORY_INTERVAL_TICKS"]
        WATER_LOSS_ON_STAGE_CHANGE = self.settings["WATER_LOSS_ON_STAGE_CHANGE"]
        RAIN_WATER_APPLY_MULTIPLIER = self.settings["RAIN_WATER_APPLY_MULTIPLIER"]
        DEFAULT_WATER_DEPLETION_RATE_PER_TICK = self.settings["DEFAULT_WATER_DEPLETION_RATE_PER_TICK"]

        # Increment our internal logical tick counter. This represents one "game minute".
        self._garden_logical_tick_counter += 1 
        current_logical_tick = self._garden_logical_tick_counter

        # Rain cooldown is still based on real-time as per original design.
        current_time_irl = datetime.now() 
        last_rain_applied_str = self._state.get("_last_rain_applied_timestamp")
        
        last_rain_applied_datetime = None
        if last_rain_applied_str:
            last_rain_applied_datetime = datetime.fromisoformat(last_rain_applied_str)
        else:
            # If no last_rain_applied_timestamp exists, set it to now to start cooldown
            self._state["_last_rain_applied_timestamp"] = current_time_irl.isoformat()
            last_rain_applied_datetime = current_time_irl
            print("Garden Manager Tick: Initializing _last_rain_applied_timestamp.")

        rain_level = self._get_rain()
        time_since_last_rain_applied = current_time_irl - last_rain_applied_datetime
        
        apply_rain_this_tick = False
        if rain_level > 0.0 and time_since_last_rain_applied >= timedelta(minutes=RAIN_COOLDOWN_MINUTES):
            apply_rain_this_tick = True
            self._state["_last_rain_applied_timestamp"] = current_time_irl.isoformat() # Update timestamp
            print(f"Garden Manager Tick: Rain level detected: {rain_level}mm/h. Applying rain effects. Next rain application possible in {RAIN_COOLDOWN_MINUTES} minutes.")
        elif rain_level > 0.0:
            remaining_time = timedelta(minutes=RAIN_COOLDOWN_MINUTES) - time_since_last_rain_applied
            # Ensure remaining_time is not negative if calculation results in slight imprecision
            remaining_minutes = max(0, int(remaining_time.total_seconds() / 60))
            print(f"Garden Manager Tick: Rain detected, but still on cooldown. Next rain application possible in approx. {remaining_minutes} minutes.")
        else:
            print("Garden Manager Tick: No rain detected.")

        room_ids_to_process = [k for k in self._state.keys() if isinstance(self._state[k], dict) and "room_id" in self._state[k]]

        for room_id in room_ids_to_process:
            garden_data = self._state[room_id] # Retrieve garden data by room_id
            
            plots = garden_data.get("plots", [])
            for plot in plots:
                plants_in_plot = plot.get("plants", [])
                
                updated_plants = []
                for plant in plants_in_plot:
                    plant_type = plant.get("plant_type")
                    plant_type_info = self._plant_types.get(plant_type)

                    if not plant_type_info:
                        print(f"Warning: Plant type '{plant_type}' for UID {plant.get('_plant_UID')} not found. Skipping.")
                        updated_plants.append(plant)
                        continue

                    # Retrieve the last logical tick time for this specific plant for precise depletion
                    last_ticked_logical_tick = plant.get("_last_ticked_logical_tick") # Renamed for clarity
                    if last_ticked_logical_tick is None: 
                        # If a plant doesn't have this, it's new or from an old save. Set it to current_logical_tick.
                        plant["_last_ticked_logical_tick"] = current_logical_tick
                        ticks_since_last_plant_tick = 0 # No depletion yet for first tick
                        print(f"  Plant {plant.get('_plant_UID')} Initializing _last_ticked_logical_tick.")
                    else:
                        ticks_since_last_plant_tick = current_logical_tick - last_ticked_logical_tick
                    
                    # If the plant has already been processed for this logical tick (or planted this tick), skip it
                    # This ensures we don't apply growth/depletion multiple times within the same logical minute.
                    if ticks_since_last_plant_tick <= 0:
                        # Update the plant's last ticked logical tick to ensure it's current
                        plant["_last_ticked_logical_tick"] = current_logical_tick
                        updated_plants.append(plant)
                        continue

                    # Update the plant's last ticked logical tick for the next iteration
                    plant["_last_ticked_logical_tick"] = current_logical_tick


                    # Apply rain effect (example: increase water_level)
                    if apply_rain_this_tick:
                        current_water = plant.get("water_level", 0.0)
                        # Scale rain effect by the number of logical ticks processed
                        new_water_from_rain = min(1.0, current_water + (rain_level * RAIN_WATER_APPLY_MULTIPLIER * ticks_since_last_plant_tick)) 
                        plant["water_level"] = new_water_from_rain
                        print(f"  Plant {plant.get('_plant_UID')} water increased by rain to {new_water_from_rain:.2f}")

                    # --- Water Depletion ---
                    # Get the plant-specific depletion rate, falling back to default if not specified
                    plant_depletion_rate = plant_type_info.get("water_depletion_rate_per_tick", 
                                                                DEFAULT_WATER_DEPLETION_RATE_PER_TICK)

                    # Calculate depletion based on logical ticks elapsed since the last time this plant was ticked
                    depletion_amount = plant_depletion_rate * ticks_since_last_plant_tick
                    current_water = plant.get("water_level", 0.0)
                    new_water_level_after_depletion = max(0.0, current_water - depletion_amount)
                    plant["water_level"] = new_water_level_after_depletion
                    print(f"  Plant {plant.get('_plant_UID')} water depleted by {depletion_amount:.3f} to {new_water_level_after_depletion:.2f} (rate: {plant_depletion_rate:.4f}/logical tick)")


                    # --- Growth calculation based on logical ticks ---
                    planted_logical_tick = plant.get("planted_logical_tick") # Renamed for clarity
                    if planted_logical_tick is None:
                        plant["planted_logical_tick"] = current_logical_tick
                        print(f"Warning: Plant {plant.get('_plant_UID')} missing planted_logical_tick, setting to current logical tick.")
                        planted_logical_tick = plant["planted_logical_tick"]

                    elapsed_logical_ticks = current_logical_tick - planted_logical_tick

                    # Store old stage index before updating
                    old_stage_index = plant.get("current_stage_index", 0) # Default to 0 if not present

                    # Determine and update current stage based on elapsed logical ticks
                    plant["current_stage_index"] = self._get_current_stage_index(plant_type_info, elapsed_logical_ticks)
                    plant["current_stage_name"] = plant_type_info["stages"][plant["current_stage_index"]]["name"]

                    # --- Apply water loss on stage change ---
                    if plant["current_stage_index"] > old_stage_index:
                        # A stage transition has occurred!
                        current_water = plant.get("water_level", 0.0)
                        plant["water_level"] = max(0.0, current_water - WATER_LOSS_ON_STAGE_CHANGE)
                        print(f"  Plant {plant.get('_plant_UID')} advanced from stage {old_stage_index} to {plant['current_stage_index']}. Water reduced by {WATER_LOSS_ON_STAGE_CHANGE} to {plant['water_level']:.2f}.")

                    # --- Water History Recording ---
                    # Record water state (0: low, 1: optimal, 2: high)
                    water_state = self._get_water_state(plant, plant_type_info)
                    plant_water_history = plant.get("water_history", []) # Get current history

                    last_water_history_recorded_logical_tick = plant.get("_last_water_history_recorded_logical_tick") # Renamed
                    
                    ticks_since_last_history_record = 0
                    if last_water_history_recorded_logical_tick is not None:
                        ticks_since_last_history_record = current_logical_tick - last_water_history_recorded_logical_tick

                    should_append_new_history_entry = False

                    # Condition to append a new history entry:
                    # 1. If no history recorded yet for this plant (always append the first entry)
                    # 2. If enough logical ticks have passed since the last record
                    if not plant_water_history:
                        should_append_new_history_entry = True
                        print(f"  Plant {plant.get('_plant_UID')} water history: First entry being recorded.")
                    elif ticks_since_last_history_record >= RECORD_WATER_HISTORY_INTERVAL_TICKS:
                        should_append_new_history_entry = True
                        print(f"  Plant {plant.get('_plant_UID')} water history: Interval passed ({ticks_since_last_history_record} logical ticks). Appending new entry.")

                    if should_append_new_history_entry:
                        plant_water_history.append(water_state)
                        plant["_last_water_history_recorded_logical_tick"] = current_logical_tick
                        print(f"  Plant {plant.get('_plant_UID')} water history: Appended new state {water_state} at logical tick {current_logical_tick}")
                    elif plant_water_history and plant_water_history[-1] != water_state:
                        # If not appending a new entry, but the current state is different from the last recorded one, update the last one.
                        plant_water_history[-1] = water_state
                        print(f"  Plant {plant.get('_plant_UID')} water history: Updated last state to {water_state} due to level change.")
                    else:
                        # No change in water state, and not time to record a new entry
                        print(f"  Plant {plant.get('_plant_UID')} water history: No change from last recorded state ({plant_water_history[-1] if plant_water_history else 'N/A'}) and not due for new record.")

                    plant["water_history"] = plant_water_history # Ensure the updated list is saved back

                    print(f"Plant {plant.get('_plant_UID')} ({plant.get('plant_type')}) in plot {plot.get('plot_id')} "
                          f"has been growing for {elapsed_logical_ticks} logical ticks, is in stage '{plant['current_stage_name']}', current water: {plant['water_level']:.2f}")
                        
                    updated_plants.append(plant)
                plot["plants"] = updated_plants
        
        # Save the logical tick counter to persist it
        self._state["_garden_logical_tick_counter"] = self._garden_logical_tick_counter
        self._write_json(self._state) # Save state after all plants are processed
        print(f"Garden state updated after logical tick {current_logical_tick}.")


    def _get_current_stage_index(self, plant_type_info: dict, elapsed_ticks: int) -> int:
        """
        Calculates the current growth stage index based on plant's elapsed time (in logical ticks).
        Args:
            plant_type_info (dict): The dictionary defining the plant type properties.
            elapsed_ticks (int): The total number of logical ticks elapsed since the plant was planted.
        Returns:
            int: The index of the current stage in the plant's stages list.
        """
        
        cumulative_ticks = 0
        for i, stage in enumerate(plant_type_info["stages"]):
            # For harvestable stage with duration 0, it means it's the final state
            # If elapsed ticks are greater than or equal to total growth time, it's harvestable.
            # Otherwise, if elapsed ticks are less than the cumulative ticks for this stage, it's in this stage.
            if i == len(plant_type_info["stages"]) - 1 and stage["duration_ticks"] == 0:
                # If it's the last stage and duration is 0, it's the final harvestable stage
                if elapsed_ticks >= cumulative_ticks: # Check against cumulative ticks up to the previous stage
                    return i
            
            cumulative_ticks += stage["duration_ticks"] # using existing key but interpreting as logical ticks
            
            if elapsed_ticks < cumulative_ticks:
                return i
        
        # If elapsed_ticks exceeds all defined stages (excluding the harvestable with 0 duration),
        # it's in the last (harvestable) stage.
        return len(plant_type_info["stages"]) - 1

    def _get_water_state(self, plant: dict, plant_type_info: dict) -> int:
        """
        Determines the water state of a plant (low, optimal, high) based on its current stage
        and water level.
        Args:
            plant (dict): The plant's state dictionary.
            plant_type_info (dict): The dictionary defining the plant type properties.
        Returns:
            int: 0 for low water, 1 for optimal water, 2 for high (overwatered).
        """
        current_stage_idx = plant.get("current_stage_index", 0)
        water_level = plant.get("water_level", 0.0)

        # Ensure current_stage_idx is within the valid range
        if current_stage_idx >= len(plant_type_info["stages"]):
            current_stage_idx = len(plant_type_info["stages"]) - 1 # Cap to last valid stage index

        stage_def = plant_type_info["stages"][current_stage_idx]
        optimal_min, optimal_max = stage_def["optimal_water_level_range"]

        if water_level < optimal_min:
            return 0 # Low water
        elif water_level > optimal_max:
            return 2 # High water (overwatered)
        else:
            return 1 # Optimal water

    def _generate_plant_uid(self) -> str:
        """
        Generates a unique 6-character plant UID.
        Ensures the generated UID is not already in use across all plants.
        """
        existing_uids = set()
        for garden_data in self._state.values():
            # Skip global-level keys (like _last_rain_applied_timestamp, _garden_logical_tick_counter)
            if not isinstance(garden_data, dict) or "room_id" not in garden_data:
                continue
            for plot in garden_data.get("plots", []):
                for plant in plot.get("plants", []):
                    existing_uids.add(plant.get("_plant_UID"))
        
        while True:
            uid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if uid not in existing_uids:
                return uid


    def plant_seed(self, plot_id: str, item_id: int) -> str:
        """
        Allows an AI agent to plant a seed from their inventory in a specified plot
        in the current garden room.
        Args:
            plot_id (str): The ID of the plot within the room (e.g., "plot1").
            item_id (int): The ID of the seed item in the player's inventory.
        Returns:
            str: A message indicating success or failure.
        """
        current_room_id = str(self.state_manager.get_current_room_id()) # Convert to string
        # Use the logical tick counter from Garden_Mananger itself for planting
        current_logical_tick = self._garden_logical_tick_counter
        
        # Retrieve default initial water level from settings
        DEFAULT_INITIAL_WATER_LEVEL = self.settings["DEFAULT_INITIAL_WATER_LEVEL"]


        if current_room_id not in self._state:
            return f"Error: You are not in a garden room. Cannot plant here."

        # Find the item by its ID
        attempt_item = self.state_manager._find_item_info_by_id(item_id)

        print(f"📌📌📌📌{attempt_item}, {type(attempt_item)}")

        if not attempt_item:
            return f"You don't see an item with ID '{item_id}' here or in your inventory."
        
        # Check if the item is in the current player's inventory
        if attempt_item["location"] != "inventory":
            # Correctly get name from item_data for error message
            item_name = attempt_item.get('item_data', {}).get('name', 'unknown item')
            return f"Item {item_id} ({item_name}) is not in your inventory, can't use it to plant."
        
        item_details = attempt_item.get("item_data", {}) # Get the nested item_data dictionary
        
        item_name = item_details.get('name', 'unknown item') # Access 'name' from item_details
        item_types_list = item_details.get("type", []) # Get the list of types

        if "seed" not in item_types_list:
            return f"Item {item_id} ({item_name}) is not of 'seed' type (found types: {item_types_list}), cannot use it to plant."
        
        plant_type = item_details.get("plant_type") # Access 'plant_type' from item_details
        if not plant_type:
            return f"Error: Seed item {item_id} ({item_name}) does not specify a 'plant_type'."
        

        garden_data = self._state[current_room_id]
        plots = garden_data.get("plots", [])
        
        target_plot = None
        for plot in plots:
            if plot.get("plot_id") == plot_id:
                target_plot = plot
                break
        
        if not target_plot:
            return f"Error: Plot '{plot_id}' not found in garden room '{current_room_id}'."

        if not isinstance(target_plot.get("plants"), list):
            target_plot["plants"] = []

        if len(target_plot["plants"]) > 0:
            return f"Error: Plot '{plot_id}' in garden '{current_room_id}' is already occupied. Harvest first before planting a new seed."

        if plant_type not in self._plant_types:
            return f"Error: Plant type '{plant_type}' specified by seed is not recognized. Available types: {', '.join(self._plant_types.keys())}."

        new_plant_uid = self._generate_plant_uid()
        
        # Initial stage is calculated based on 0 elapsed ticks
        plant_type_info = self._plant_types[plant_type]
        initial_stage_index = self._get_current_stage_index(plant_type_info, 0)
        initial_stage_name = plant_type_info["stages"][initial_stage_index]["name"]

        new_plant = {
            "plant_type": plant_type,
            "planted_logical_tick": current_logical_tick, # Store current logical tick for growth tracking
            "_last_ticked_logical_tick": current_logical_tick, # To track depletion from this logical tick
            "water_level": DEFAULT_INITIAL_WATER_LEVEL, # Initial water level from settings
            "current_stage_index": initial_stage_index, # Set explicitly for immediate display
            "current_stage_name": initial_stage_name,   # Set explicitly for immediate display
            "water_history": [], # To record water states over time (0:low, 1:optimal, 2:high)
            "_last_water_history_recorded_logical_tick": current_logical_tick, # Initialize history recording logical tick
            "_plant_UID": new_plant_uid
        }
        
        target_plot["plants"].append(new_plant)
        # self._write_json(self._state) # Handled by the tick() function at the end.

        # If successfully planted, remove the seed item from inventory
        self.state_manager.remove_item(item_id)

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/seed.png", "popup_type": 2})

        return f"Successfully planted {plant_type} with UID {new_plant_uid} in plot {plot_id} of garden {current_room_id}. It is currently in the '{initial_stage_name}' stage. Seed consumed."

    def check_plant_state(self, plot_id: str) -> str:
        """
        Allows an AI agent to check the state of a plant in a specified plot
        in the current garden room.
        Args:
            plot_id (str): The ID of the plot within the room.
        Returns:
            str: A description of the plant's current state or an error message.
        """
        current_room_id = str(self.state_manager.get_current_room_id()) # Convert to string
        current_logical_tick = self._garden_logical_tick_counter # Use logical tick for display

        if current_room_id not in self._state:
            return f"Error: You are not in a garden room. Cannot check plant state here."

        garden_data = self._state[current_room_id]
        plots = garden_data.get("plots", [])
        
        target_plot = None
        for plot in plots:
            if plot.get("plot_id") == plot_id:
                target_plot = plot
                break
        
        if not target_plot:
            return f"Error: Plot '{plot_id}' not found in garden room '{current_room_id}'."

        plants_in_plot = target_plot.get("plants", [])
        if not plants_in_plot:
            return f"Plot '{plot_id}' in garden '{current_room_id}' is empty."

        plant = plants_in_plot[0] # Assuming one plant per plot
        plant_type = plant.get("plant_type", "unknown plant")
        plant_uid = plant.get("_plant_UID", "N/A")
        water_level = plant.get("water_level", 0.0)
        
        planted_logical_tick = plant.get("planted_logical_tick") # Renamed
        elapsed_ticks = 0
        if planted_logical_tick is not None:
            elapsed_ticks = current_logical_tick - planted_logical_tick

        plant_info = self._plant_types.get(plant_type)
        current_stage_name = plant.get("current_stage_name", "unknown stage") # Use stored name for consistency
        
        if plant_info:
            current_stage_idx = plant.get("current_stage_index", 0)
            # Ensure current_stage_idx is within bounds
            if current_stage_idx >= len(plant_info["stages"]):
                current_stage_idx = len(plant_info["stages"]) - 1
            
            stage_def = plant_info["stages"][current_stage_idx]
            optimal_min, optimal_max = stage_def["optimal_water_level_range"]
            
            water_status_desc = ""
            if water_level < optimal_min:
                water_status_desc = "needs more water."
            elif water_level > optimal_max:
                water_status_desc = "is overwatered."
            else:
                water_status_desc = "has optimal water levels."
            
            return (f"Plant {plant_type} (UID: {plant_uid}) in plot {plot_id} is "
                    f"{current_stage_name} (Elapsed time: {elapsed_ticks} logical ticks). "
                    f"Its current water level is {water_level:.2f}, and it {water_status_desc}")
        else:
            return (f"Plant {plant_type} (UID: {plant_uid}) in plot {plot_id} is "
                    f"{current_stage_name} (Elapsed time: {elapsed_ticks} logical ticks). Water level: {water_level:.2f}. "
                    f"Details for this plant type are not available.")
    def harvest_plant(self, plot_id: str) -> str:
        """
        Allows an AI agent to harvest a plant from a specified plot in the current garden room.
        Harvested items are added to the player's inventory. If inventory is full, items are
        placed in the current room.
        Args:
            plot_id (str): The ID of the plot within the room.
        Returns:
            str: A message indicating the harvest result or an error.
        """

        # Remove these lines, as current_inventory_length will be calculated in the loop
        # current_inventory = self.state_manager._state.get("inventory", [])
        # current_inventory_length = len(current_inventory)
        
        max_inventory = self.state_manager.MAX_INVENTORY_SLOTS 
        current_room_id = str(self.state_manager.get_current_room_id()) # Convert to string
        current_logical_tick = self._garden_logical_tick_counter # Use logical tick

        if current_room_id not in self._state:
            return f"Error: You are not in a garden room. Cannot harvest here."

        garden_data = self._state[current_room_id]
        plots = garden_data.get("plots", [])
        
        target_plot = None
        plot_index = -1
        for i, plot in enumerate(plots):
            if plot.get("plot_id") == plot_id:
                target_plot = plot
                plot_index = i
                break
        
        if not target_plot:
            return f"Error: Plot '{plot_id}' not found in garden room '{current_room_id}'."

        plants_in_plot = target_plot.get("plants", [])
        if not plants_in_plot:
            return f"Plot '{plot_id}' in garden '{current_room_id}' is empty, nothing to harvest."

        plant_to_harvest = plants_in_plot[0] # Assuming one plant per plot
        plant_type = plant_to_harvest.get("plant_type")
        plant_uid = plant_to_harvest.get("_plant_UID")
        current_stage_name = plant_to_harvest.get("current_stage_name")

        plant_info = self._plant_types.get(plant_type)

        if not plant_info:
            return f"Error: Plant type '{plant_type}' is not recognized, cannot determine harvest yield."

        if current_stage_name != "harvestable":
            return f"Plant {plant_type} (UID: {plant_uid}) in plot {plot_id} is not yet harvestable. It is currently in the '{current_stage_name}' stage."

        harvested_data = self._calculate_harvest_yield(plant_to_harvest, plant_info)

        harvested_items_with_quantities = harvested_data.get("harvested_items_with_quantities", [])
        life_cycle_quality = harvested_data["life_cycle_quality"]  # This is a string like "poor", "average", "good", etc.
        penalty = harvested_data["penalty"] # This is a float value representing the penalty applied to the yield
        bonus = harvested_data["bonus"] # This is a float value representing the bonus applied to the yield

        # Use the configurable messages
        quality_feedback = self.settings["LIFE_CYCLE_QUALITY_MESSAGES"]

        # Get the specific message for the quality, defaulting to an empty string if not found
        feedback_message = quality_feedback.get(life_cycle_quality, "")

        life_cycle_quality_message = f"The plant's life cycle quality was '{life_cycle_quality}'. {feedback_message} \nTotal penalty applied: {penalty:.2f}, bonus applied: {bonus:.2f}."


        # --- Inventory Space Handling ---
        # total_slots_needed = sum(item_data.get("quantity", 0) for item_data in harvested_items_with_quantities) # This calculation was simplified to 1 slot per item instance in create_item

        items_placed_in_inventory = []
        items_placed_in_room = []

        if harvested_items_with_quantities:
            for item_data in harvested_items_with_quantities:
                item_def = item_data.get("item")
                quantity = item_data.get("quantity", 0)
                
                if item_def and quantity > 0:
                    # RE-EVALUATE current inventory length inside the loop
                    # This ensures we get the most up-to-date count of occupied slots
                    current_inventory = self.state_manager._state.get("inventory", [])
                    current_inventory_length = len(current_inventory)
                    
                    # Check if there's enough space in inventory for this specific item quantity
                    # This is a simplified check assuming create_item will either consume
                    # 0 new slots (if stacking onto an existing item) or 1 new slot (if creating a new stack).
                    if (current_inventory_length + 1) <= max_inventory: 
                        self.state_manager.create_item("inventory", None, item_def, quantity=quantity)
                        items_placed_in_inventory.append(f"{quantity} {item_def.get('name', 'unknown item')}")
                        # NO MANUAL INCREMENT HERE: current_inventory_length will be recalculated on the next iteration
                    else:
                        # Inventory full, place in room
                        self.state_manager.create_item("room", int(current_room_id), item_def, quantity=quantity) # Create item expects an int for the room
                        items_placed_in_room.append(f"{quantity} {item_def.get('name', 'unknown item')}")

        harvest_message_prefix = (f"Successfully harvested {plant_type} (UID: {plant_uid}) from plot {plot_id} in garden {current_room_id}. {life_cycle_quality_message}")
        
        harvest_yield_message_parts = []
        if items_placed_in_inventory:
            harvest_yield_message_parts.append(f"You received: {', '.join(items_placed_in_inventory)} (added to inventory).")
        if items_placed_in_room:
            harvest_yield_message_parts.append(f"Due to limited inventory space, {', '.join(items_placed_in_room)} were placed in the current room.")
        
        harvest_yield_message = " ".join(harvest_yield_message_parts)
        if not harvest_yield_message: # If no items were harvested at all
            harvest_yield_message = "It yielded no items due to poor conditions."


        # Determine the life cycle of the plant for post-harvest behavior
        life_cycle = plant_info.get("life_cycle", "annual") # Default to annual if not specified

        if life_cycle == "perennial":
            # For perennial plants, revert to 'mature' stage and allow re-growth
            mature_stage_index = -1
            ticks_to_reach_mature = 0
            
            # Find the 'mature' stage and calculate cumulative ticks to reach its start
            for i, stage in enumerate(plant_info["stages"]):
                if stage["name"] == "mature":
                    mature_stage_index = i
                    break # Found the mature stage
                ticks_to_reach_mature += stage["duration_ticks"] # Accumulate duration of stages *before* mature (interpreted as logical ticks)

            if mature_stage_index == -1:
                # Fallback if 'mature' stage not found for some reason, treat as annual and remove
                print(f"Warning: Perennial plant '{plant_type}' does not have a 'mature' stage defined for re-growth. Removing plant.")
                self._state[current_room_id]["plots"][plot_index]["plants"] = []
                self._write_json(self._state)
                return f"{harvest_message_prefix} {harvest_yield_message} The plant was removed due to a configuration error for its life cycle type."

            # Calculate the new planted_logical_tick so that elapsed_ticks will put it exactly at the start of 'mature'
            plant_to_harvest["planted_logical_tick"] = current_logical_tick - ticks_to_reach_mature
            
            # Explicitly set current stage to mature for immediate feedback/state consistency
            plant_to_harvest["current_stage_index"] = mature_stage_index
            plant_to_harvest["current_stage_name"] = plant_info["stages"][mature_stage_index]["name"]

            plant_to_harvest["water_level"] = self.settings["DEFAULT_INITIAL_WATER_LEVEL"] # Reset water to a neutral level after harvest
            plant_to_harvest["water_history"] = [] # Reset water history for the new growth cycle
            plant_to_harvest["_last_water_history_recorded_logical_tick"] = current_logical_tick # Reset history recording logical tick
            plant_to_harvest["_last_ticked_logical_tick"] = current_logical_tick # Reset last ticked logical tick

            # Plant remains in plot, no removal needed from the list
            self._write_json(self._state)
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/harvest.png", "popup_type": 2})

            return (f"{harvest_message_prefix} {harvest_yield_message} "
                    f"The plant is now in the 'mature' stage and will regrow for future harvests.")
        else:
            # For annual or biennial plants, or if life_cycle is not recognized, remove the plant from the plot
            self._state[current_room_id]["plots"][plot_index]["plants"] = []
            self._write_json(self._state)
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/harvest.png", "popup_type": 2})

            return (f"{harvest_message_prefix} {harvest_yield_message} "
                    f"The plant has completed its life cycle. The plot is now empty.")
        

    def _calculate_harvest_yield(self, plant_data: dict, plant_type_info: dict) -> dict:
        water_history = plant_data.get("water_history", [])

        # Count optimal, low, and high water states
        optimal_water_count = water_history.count(1)
        low_water_count = water_history.count(0)
        high_water_count = water_history.count(2)

        total_non_optimal_states = low_water_count + high_water_count

        # --- Logarithmic Penalty Logic ---
        # Retrieve settings from self.settings
        PENALTY_LOG_BASE = self.settings["PENALTY_LOG_BASE"]
        PENALTY_SENSITIVITY_FACTOR = self.settings["PENALTY_SENSITIVITY_FACTOR"]

        penalty = math.floor(
            math.log(1 + total_non_optimal_states / PENALTY_SENSITIVITY_FACTOR, PENALTY_LOG_BASE)
        )
        # --- End Logarithmic Penalty Logic ---

        # --- Logarithmic Additive Bonus Logic ---
        # Retrieve settings from self.settings
        BONUS_LOG_BASE = self.settings["BONUS_LOG_BASE"]
        BONUS_SENSITIVITY_FACTOR = self.settings["BONUS_SENSITIVITY_FACTOR"]
        BONUS_PER_LOG_STEP = self.settings["BONUS_PER_LOG_STEP"]

        bonus = math.floor(
            math.log(1 + optimal_water_count / BONUS_SENSITIVITY_FACTOR, BONUS_LOG_BASE) * BONUS_PER_LOG_STEP
        )
        # --- End Logarithmic Additive Bonus Logic ---

        harvested_items_with_quantities = []
        harvest_items_definitions = plant_type_info.get("harvest_items", [])

        for harvest_def in harvest_items_definitions:
            item_definition = harvest_def.get("item")
            base_item_yield = harvest_def.get("base_harvest_yield", 1)

            if item_definition:
                # Apply both bonus and penalty
                potential_yield = base_item_yield + bonus - penalty

                # Ensure at least 1 item is harvested if base yield was positive,
                # otherwise ensure 0.
                if base_item_yield > 0:
                    final_item_yield = max(1, math.floor(potential_yield))
                else:
                    final_item_yield = 0

                if final_item_yield > 0:
                    harvested_items_with_quantities.append({"item": item_definition, "quantity": final_item_yield})
            else:
                print(f"Warning: Missing 'item' definition in harvest_items for plant type {plant_data.get('plant_type')}.")

        # Map the life cycle quality to a descriptive string for the output
        quality_information={
            "life_cycle_quality": self._describe_life_cycle_quality(penalty, bonus),
            "penalty": penalty,
            "bonus": bonus,
            "harvested_items_with_quantities": harvested_items_with_quantities
        }
        return quality_information
        

    def _describe_life_cycle_quality(self, penalty: int, bonus: int) -> str:
            # These conditions directly determine the quality string
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

    def get_garden_summary(self) -> str:
        """
        Provides a summary of the garden in the current room.
        """
        current_room_id = str(self.state_manager.get_current_room_id()) # Convert to string
        current_logical_tick = self._garden_logical_tick_counter # Use logical tick for summary

        if current_room_id not in self._state:
            return "You are not in a garden room. No garden summary available for this location."

        garden_data = self._state[current_room_id]
        
        # Attempt to get room name from state manager, fallback to ID if not available
        room_name_info = self.state_manager._state.get("rooms", [])
        room_name = next((room.get("name") for room in room_name_info if str(room.get("id")) == current_room_id), current_room_id)

        summary_lines = [f"--- Garden Summary for {room_name} (ID: {current_room_id}) ---"]
        
        plots = garden_data.get("plots", [])
        if not plots:
            summary_lines.append("  No plots defined for this garden.")
            return "\n".join(summary_lines)

        for plot in plots:
            plot_id = plot.get("plot_id", "N/A")
            plants = plot.get("plants", [])
            
            if not plants:
                summary_lines.append(f"  Plot {plot_id}: Empty.")
            else:
                plant = plants[0] # Assuming one plant per plot
                plant_type = plant.get("plant_type", "unknown")
                plant_uid = plant.get("_plant_UID", "N/A")
                current_stage_name = plant.get("current_stage_name", "unknown")
                water_level = plant.get("water_level", 0.0)

                planted_logical_tick = plant.get("planted_logical_tick") # Renamed
                elapsed_ticks_display = "N/A"
                if planted_logical_tick is not None:
                    elapsed_ticks_display = f"{current_logical_tick - planted_logical_tick} logical ticks"


                plant_info = self._plant_types.get(plant_type)
                water_status_desc = "N/A"
                if plant_info:
                    water_state = self._get_water_state(plant, plant_info)
                    if water_state == 0: water_status_desc = "Low Water"
                    elif water_state == 1: water_status_desc = "Optimal Water"
                    elif water_state == 2: water_status_desc = "High Water"

                summary_lines.append(
                    f"  Plot {plot_id}:\n"
                    f"    Plant: {plant_type} Plant (UID: {plant_uid})\n"
                    f"    Stage: {current_stage_name} (Time Grown: {elapsed_ticks_display})\n"
                    f"    Water: {water_level:.2f} ({water_status_desc})"
                )
        
        return "\n".join(summary_lines)
    
    def water_plot(self, plot_id: str, water_level_type: str) -> str:
        """
        Waters a plant in a specified plot in the current garden room.
        Args:
            plot_id (str): The ID of the plot within the room.
            water_level_type (str): The amount of water to apply ("low", "medium", or "high").
        Returns:
            str: A message indicating the result of the watering action.
        """
        current_room_id = str(self.state_manager.get_current_room_id()) # Convert to string

        if current_room_id not in self._state:
            return f"Error: You are not in a garden room. Cannot water plots here."

        garden_data = self._state[current_room_id]
        plots = garden_data.get("plots", [])
        
        target_plot = None
        for plot in plots:
            if plot.get("plot_id") == plot_id:
                target_plot = plot
                break
        
        if not target_plot:
            return f"Error: Plot '{plot_id}' not found in garden room '{current_room_id}'."

        plants_in_plot = target_plot.get("plants", [])
        if not plants_in_plot:
            return f"Plot '{plot_id}' in garden '{current_room_id}' is empty, nothing to water."

        plant = plants_in_plot[0] # Assuming one plant per plot
        plant_type = plant.get("plant_type")
        plant_uid = plant.get("_plant_UID")
        current_water = plant.get("water_level", 0.0)

        # Define how much water each type adds (arbitrary values, can be tuned)
        water_amounts = self.settings["WATERING_AMOUNTS"]

        amount_to_add = water_amounts.get(water_level_type.lower())
        if amount_to_add is None:
            return f"Error: Invalid water level type '{water_level_type}'. Choose from {', '.join(water_amounts.keys())}."

        new_water_level = min(1.0, max(0.0, current_water + amount_to_add)) # Cap water level between 0.0 and 1.0
        plant["water_level"] = new_water_level

        # Get immediate water status description for feedback
        plant_info = self._plant_types.get(plant_type)
        water_state = self._get_water_state(plant, plant_info) if plant_info else -1 # -1 for unknown
        
        water_status_desc = ""
        if water_state == 0: water_status_desc = "and it still needs more water."
        elif water_state == 1: water_status_desc = "and it now has optimal water levels."
        elif water_state == 2: water_status_desc = "and it is now overwatered."
        else: water_status_desc = "but its optimal water levels are unknown." # For unknown plant types

        self._write_json(self._state) # Save the updated state

        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/watering_can.png"})

        return (f"You applied {water_level_type} water to {plant_type} (UID: {plant_uid}) in plot {plot_id}. "
                f"Its water level is now {new_water_level:.2f} {water_status_desc}")
    
    def remove_plant_from_plot(self, plot_id: str) -> str:
        """
        Removes any existing plant from a specified plot in the current garden room.
        This action permanently clears the plot.
        Args:
            plot_id (str): The ID of the plot within the room.
        Returns:
            str: A message indicating the success or failure of the removal.
        """
        current_room_id = str(self.state_manager.get_current_room_id()) # Convert to string

        if current_room_id not in self._state:
            return f"Error: You are not in a garden room. Cannot remove plants here."

        garden_data = self._state[current_room_id]
        plots = garden_data.get("plots", [])
        
        target_plot = None
        plot_index = -1
        for i, plot in enumerate(plots):
            if plot.get("plot_id") == plot_id:
                target_plot = plot
                plot_index = i
                break
        
        if not target_plot:
            return f"Error: Plot '{plot_id}' not found in garden room '{current_room_id}'."

        plants_in_plot = target_plot.get("plants", [])
        if not plants_in_plot:
            return f"Plot '{plot_id}' in garden '{current_room_id}' is already empty, nothing to remove."

        plant_type = plants_in_plot[0].get("plant_type", "unknown plant")
        plant_uid = plants_in_plot[0].get("_plant_UID", "N/A")

        # Remove the plant by emptying the 'plants' list for this plot
        self._state[current_room_id]["plots"][plot_index]["plants"] = []
        self._write_json(self._state)

        return f"Successfully removed {plant_type} (UID: {plant_uid}) from plot {plot_id} in garden {current_room_id}. The plot is now empty."
    

    def display_info(self):
        pass