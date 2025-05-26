from utils import open_meteo_handle
from utils.generic_json_tool import GenericJsonTool
import random
import string
import os
from datetime import datetime, timedelta

from tools.tools_folder.tools_data.harvesting_data import (plant_types)


class Garden_Mananger(GenericJsonTool):
    """
    Manages the state of plants in various garden plots across different rooms.
    Uses GenericJsonTool to persist garden data.
    """

    # Dictionary of predefined plant types and their growth stages
    # Each stage defines duration in *minutes* and optimal water level range.
    _plant_types = plant_types


    def __init__(self, state_manager):
        """
        Initializes the Garden_Mananger.
        Args:
            state_manager: An instance of the main state manager, used to access
                           room data and the base path for saving garden data,
                           and the current game tick.
        """
        self.json_filename = "garden_data.json"
        self.state_manager = state_manager

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
        
        # After GenericJsonTool initializes self._state (either from file or default),
        # ensure all garden rooms from the main state manager are reflected here.
        self._initialize_garden_plots()

    def _initialize_garden_plots(self):
        """
        Ensures that all rooms marked as 'planting_garden' in the main state manager
        have corresponding entries in this Garden_Mananger's state file.
        It will add new gardens if they don't exist or adjust plot counts if changed.
        Existing plant data in plots will be preserved where possible.
        """
        rooms_list = self.state_manager._state.get("rooms", [])

        # Make a copy to modify safely, then assign back to self._state.
        # This preserves non-garden specific keys like "_last_rain_applied_timestamp".
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
        Advances the state of all plants in the garden based on real-world time elapsed.
        Applies rain effect if currently raining and the rain cooldown based on real-time has passed.
        Also applies natural water depletion.
        """
        # ... (existing rain_cooldown_minutes, current_time, last_rain_applied_datetime, etc.) ...

        RAIN_COOLDOWN_MINUTES = 30 
        current_time = datetime.now()
        last_rain_applied_str = self._state.get("_last_rain_applied_timestamp")
        
        # Convert stored string timestamp back to datetime object
        last_rain_applied_datetime = datetime.fromisoformat(last_rain_applied_str)

        rain_level = self._get_rain()
        time_since_last_rain_applied = current_time - last_rain_applied_datetime
        
        apply_rain_this_tick = False
        if rain_level > 0.0 and time_since_last_rain_applied >= timedelta(minutes=RAIN_COOLDOWN_MINUTES):
            apply_rain_this_tick = True
            self._state["_last_rain_applied_timestamp"] = current_time.isoformat() # Update timestamp
            print(f"Garden Manager Tick: Rain level detected: {rain_level}mm/h. Applying rain effects. Next rain application possible in {RAIN_COOLDOWN_MINUTES} minutes.")
        elif rain_level > 0.0:
            remaining_time = timedelta(minutes=RAIN_COOLDOWN_MINUTES) - time_since_last_rain_applied
            # Ensure remaining_time is not negative if calculation results in slight imprecision
            remaining_minutes = max(0, int(remaining_time.total_seconds() / 60))
            print(f"Garden Manager Tick: Rain detected, but still on cooldown. Next rain application possible in approx. {remaining_minutes} minutes.")
        else:
            print("Garden Manager Tick: No rain detected.")

        # Define how much water to deplete per minute of real-world time
        # This is a critical value to tune for game balance.
        # Example: 0.001 per minute means it takes 1000 minutes (approx 16.6 hours) for water to go from 1.0 to 0.0 without any input.
        WATER_DEPLETION_RATE_PER_MINUTE = 0.001 

        # Iterate through all gardens in the state
        for room_id, garden_data in self._state.items():
            if not isinstance(garden_data, dict) or "room_id" not in garden_data:
                continue

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

                    # Retrieve the last tick time for this specific plant for more precise depletion
                    last_tick_time_str = plant.get("_last_ticked_timestamp")
                    if not last_tick_time_str:
                        # If a plant doesn't have this, it's new or from an old save. Set it to current_time.
                        plant["_last_ticked_timestamp"] = current_time.isoformat()
                        time_since_last_plant_tick = timedelta(0) # No depletion yet for first tick
                    else:
                        last_tick_datetime = datetime.fromisoformat(last_tick_time_str)
                        time_since_last_plant_tick = current_time - last_tick_datetime
                    
                    # Update the plant's last ticked timestamp for the next iteration
                    plant["_last_ticked_timestamp"] = current_time.isoformat()


                    # Apply rain effect (example: increase water_level)
                    if apply_rain_this_tick:
                        current_water = plant.get("water_level", 0.0)
                        # Arbitrary multiplier for rain effect, caps water at 1.0
                        new_water_from_rain = min(1.0, current_water + (rain_level * 0.05)) 
                        plant["water_level"] = new_water_from_rain
                        print(f"  Plant {plant.get('_plant_UID')} water increased by rain to {new_water_from_rain:.2f}")

                    # --- Water Depletion ---
                    # Calculate depletion based on time elapsed since the last time this plant was ticked
                    depletion_amount = WATER_DEPLETION_RATE_PER_MINUTE * (time_since_last_plant_tick.total_seconds() / 60.0)
                    current_water = plant.get("water_level", 0.0)
                    new_water_level_after_depletion = max(0.0, current_water - depletion_amount)
                    plant["water_level"] = new_water_level_after_depletion
                    print(f"  Plant {plant.get('_plant_UID')} water depleted by {depletion_amount:.3f} to {new_water_level_after_depletion:.2f}")


                    # --- Growth calculation based on timestamps ---
                    planted_timestamp_str = plant.get("planted_timestamp")
                    if not planted_timestamp_str:
                        plant["planted_timestamp"] = current_time.isoformat()
                        print(f"Warning: Plant {plant.get('_plant_UID')} missing planted_timestamp, setting to current time.")
                        planted_timestamp_str = plant["planted_timestamp"]

                    planted_datetime = datetime.fromisoformat(planted_timestamp_str)
                    elapsed_time = current_time - planted_datetime
                    elapsed_minutes = elapsed_time.total_seconds() / 60.0

                    # Determine and update current stage based on elapsed time
                    plant["current_stage_index"] = self._get_current_stage_index(plant_type_info, elapsed_minutes)
                    plant["current_stage_name"] = plant_type_info["stages"][plant["current_stage_index"]]["name"]

                    # Record water state (0: low, 1: optimal, 2: high)
                    water_state = self._get_water_state(plant, plant_type_info)
                    plant_water_history = plant.get("water_history", [])
                    plant_water_history.append(water_state)
                    plant["water_history"] = plant_water_history

                    print(f"Plant {plant.get('_plant_UID')} ({plant.get('plant_type')}) in plot {plot.get('plot_id')} "
                          f"has been growing for {elapsed_minutes:.2f} minutes, is in stage '{plant['current_stage_name']}', current water: {plant['water_level']:.2f}")
                        
                    updated_plants.append(plant)
                plot["plants"] = updated_plants
        
        self._write_json(self._state) # Save state after all plants are processed
        print("Garden state updated after tick.")

    def _get_current_stage_index(self, plant_type_info: dict, elapsed_minutes: float) -> int:
        """
        Calculates the current growth stage index based on plant's elapsed time (in minutes).
        Args:
            plant_type_info (dict): The dictionary defining the plant type properties.
            elapsed_minutes (float): The total number of minutes elapsed since the plant was planted.
        Returns:
            int: The index of the current stage in the plant's stages list.
        """
        
        cumulative_minutes = 0
        for i, stage in enumerate(plant_type_info["stages"]):
            # For harvestable stage with duration 0, it means it's the final state
            # If elapsed minutes are greater than or equal to total growth time, it's harvestable.
            # Otherwise, if elapsed minutes are less than the cumulative minutes for this stage, it's in this stage.
            if i == len(plant_type_info["stages"]) - 1 and stage["duration_minutes"] == 0:
                # If it's the last stage and duration is 0, it's the final harvestable stage
                if elapsed_minutes >= cumulative_minutes: # Check against cumulative minutes up to the previous stage
                    return i
            
            cumulative_minutes += stage["duration_minutes"]
            
            if elapsed_minutes < cumulative_minutes:
                return i
        
        # If elapsed_minutes exceeds all defined stages (excluding the harvestable with 0 duration),
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
            # Skip global-level keys (like _last_rain_applied_timestamp)
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
        
        # *** FIX STARTS HERE ***
        item_details = attempt_item.get("item_data", {}) # Get the nested item_data dictionary
        
        item_name = item_details.get('name', 'unknown item') # Access 'name' from item_details
        item_types_list = item_details.get("type", []) # Get the list of types

        if "seed" not in item_types_list:
            return f"Item {item_id} ({item_name}) is not of 'seed' type (found types: {item_types_list}), cannot use it to plant."
        
        plant_type = item_details.get("plant_type") # Access 'plant_type' from item_details
        if not plant_type:
            return f"Error: Seed item {item_id} ({item_name}) does not specify a 'plant_type'."
        # *** FIX ENDS HERE ***

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
        
        # Initial stage is calculated based on 0 elapsed time
        plant_type_info = self._plant_types[plant_type]
        initial_stage_index = self._get_current_stage_index(plant_type_info, 0)
        initial_stage_name = plant_type_info["stages"][initial_stage_index]["name"]

        new_plant = {
            "plant_type": plant_type,
            "planted_timestamp": datetime.now().isoformat(), # Store current time for growth tracking
            "water_level": 0.5, # Initial water level (e.g., freshly watered after planting)
            "current_stage_index": initial_stage_index, # Set explicitly for immediate display
            "current_stage_name": initial_stage_name,   # Set explicitly for immediate display
            "water_history": [], # To record water states over time (0:low, 1:optimal, 2:high)
            "_plant_UID": new_plant_uid
        }
        
        target_plot["plants"].append(new_plant)
        # Assuming _write_json is for persistence
        # self._write_json(self._state) 

        # If successfully planted, remove the seed item from inventory
        self.state_manager.remove_item(item_id)

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
        
        planted_timestamp_str = plant.get("planted_timestamp")
        elapsed_minutes = 0.0
        if planted_timestamp_str:
            try:
                planted_datetime = datetime.fromisoformat(planted_timestamp_str)
                elapsed_minutes = (datetime.now() - planted_datetime).total_seconds() / 60.0
            except ValueError:
                pass # Handle corrupted timestamp if necessary

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
                    f"{current_stage_name} (Elapsed time: {elapsed_minutes:.2f} minutes). "
                    f"Its current water level is {water_level:.2f}, and it {water_status_desc}")
        else:
            return (f"Plant {plant_type} (UID: {plant_uid}) in plot {plot_id} is "
                    f"{current_stage_name} (Elapsed time: {elapsed_minutes:.2f} minutes). Water level: {water_level:.2f}. "
                    f"Details for this plant type are not available.")

    # --- Modified harvest_plant function ---
    def harvest_plant(self, plot_id: str) -> str:
        """
        Allows an AI agent to harvest a plant from a specified plot in the current garden room.
        Harvested items are added to the player's inventory.
        Args:
            plot_id (str): The ID of the plot within the room.
        Returns:
            str: A message indicating the harvest result or an error.
        """

        current_inventory = self.state_manager._state.get("inventory", [])
        current_inventory_length = len(current_inventory)
        
        max_inventory = self.state_manager.MAX_INVENTORY_SLOTS 
        current_room_id = str(self.state_manager.get_current_room_id()) # Convert to string

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

        harvested_items = self._calculate_harvest_yield(plant_to_harvest, plant_info)
        
        # --- NEW: Inventory Space Pre-Check ---
        total_slots_needed = sum(item_data.get("quantity", 0) for item_data in harvested_items)

        # Only perform check if there are items to be harvested and they require slots
        if harvested_items and total_slots_needed > 0:
            if (current_inventory_length + total_slots_needed) > max_inventory:
                space_needed = (current_inventory_length + total_slots_needed) - max_inventory
                return (f"Your inventory does not have enough space to harvest all items. "
                        f"You need {space_needed} more slot(s) for the expected {total_slots_needed} items. "
                        f"Please make space before harvesting.")
        # --- END Inventory Space Pre-Check ---

        # Determine the life cycle of the plant for post-harvest behavior
        life_cycle = plant_info.get("life_cycle", "annual") # Default to annual if not specified

        harvest_summary_strings = []
        if harvested_items:
            for item_data in harvested_items:
                item_def = item_data.get("item")
                quantity = item_data.get("quantity", 0)
                if item_def and quantity > 0:
                    # UPDATED: Call create_item with correct arguments
                    # The return value of create_item (a string message) is ignored here
                    # because the space check was done upfront.
                    _ = self.state_manager.create_item("inventory", None, item_def, quantity=quantity) 
                    harvest_summary_strings.append(f"{quantity} {item_def.get('name', 'unknown item')}")
        
        harvest_message_prefix = (f"Successfully harvested {plant_type} (UID: {plant_uid}) from plot {plot_id} in garden {current_room_id}.")
        harvest_yield_message = ""
        if harvest_summary_strings:
            harvest_yield_message = f"You received: {', '.join(harvest_summary_strings)}."
        else:
            harvest_yield_message = "It yielded no items due to poor conditions."


        if life_cycle == "perennial":
            # For perennial plants, revert to 'mature' stage and allow re-growth
            mature_stage_index = -1
            minutes_to_reach_mature = 0
            
            # Find the 'mature' stage and calculate cumulative minutes to reach its start
            for i, stage in enumerate(plant_info["stages"]):
                if stage["name"] == "mature":
                    mature_stage_index = i
                    break # Found the mature stage
                minutes_to_reach_mature += stage["duration_minutes"] # Accumulate duration of stages *before* mature

            if mature_stage_index == -1:
                # Fallback if 'mature' stage not found for some reason, treat as annual and remove
                print(f"Warning: Perennial plant '{plant_type}' does not have a 'mature' stage defined for re-growth. Removing plant.")
                self._state[current_room_id]["plots"][plot_index]["plants"] = []
                self._write_json(self._state)
                return f"{harvest_message_prefix} {harvest_yield_message} The plant was removed due to a configuration error for its life cycle type."

            # Calculate the new planted_timestamp so that elapsed_minutes will put it exactly at the start of 'mature'
            new_planted_datetime = datetime.datetime.now() - datetime.timedelta(minutes=minutes_to_reach_mature)
            plant_to_harvest["planted_timestamp"] = new_planted_datetime.isoformat()
            
            # Explicitly set current stage to mature for immediate feedback/state consistency
            plant_to_harvest["current_stage_index"] = mature_stage_index
            plant_to_harvest["current_stage_name"] = plant_info["stages"][mature_stage_index]["name"]

            plant_to_harvest["water_level"] = 0.5 # Optional: Reset water to a neutral level after harvest
            plant_to_harvest["water_history"] = [] # Reset water history for the new growth cycle

            # Plant remains in plot, no removal needed from the list
            self._write_json(self._state)
            return (f"{harvest_message_prefix} {harvest_yield_message} "
                    f"The plant is now in the 'mature' stage and will regrow for future harvests.")
        else:
            # For annual or biennial plants, or if life_cycle is not recognized, remove the plant from the plot
            self._state[current_room_id]["plots"][plot_index]["plants"] = []
            self._write_json(self._state)
            return (f"{harvest_message_prefix} {harvest_yield_message} "
                    f"The plant has completed its life cycle. The plot is now empty.")
        

    def _calculate_harvest_yield(self, plant_data: dict, plant_type_info: dict) -> list[dict]:
        """
        Calculates the final harvest yield for each item based on the plant's water history and base yield.
        A simpler model: penalize for non-optimal water states across the plant's life.
        Args:
            plant_data (dict): The dictionary representing the specific plant's state.
            plant_type_info (dict): The dictionary defining the plant type properties.
        Returns:
            list[dict]: A list of dictionaries, each containing an 'item' (item definition)
                        and 'quantity' (calculated yield for that item).
        """
        water_history = plant_data.get("water_history", [])

        # Count optimal, low, and high water states
        optimal_water_count = water_history.count(1)
        low_water_count = water_history.count(0)
        high_water_count = water_history.count(2)

        # Apply a simple penalty: e.g., lose 1 yield point for every 5 non-optimal water states
        total_non_optimal_states = low_water_count + high_water_count
        penalty = total_non_optimal_states // 5 
        
        harvested_items_with_quantities = []
        harvest_items_definitions = plant_type_info.get("harvest_items", [])

        for harvest_def in harvest_items_definitions:
            item_definition = harvest_def.get("item")
            base_item_yield = harvest_def.get("base_harvest_yield", 1)
            
            if item_definition:
                # Apply the calculated penalty to the base yield of *each* item type
                final_item_yield = max(0, base_item_yield - penalty) 
                if final_item_yield > 0:
                    harvested_items_with_quantities.append({"item": item_definition, "quantity": final_item_yield})
            else:
                print(f"Warning: Missing 'item' definition in harvest_items for plant type {plant_data.get('plant_type')}.")

        return harvested_items_with_quantities

    def get_garden_summary(self) -> str:
        """
        Provides a summary of the garden in the current room.
        """
        current_room_id = str(self.state_manager.get_current_room_id()) # Convert to string

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

                planted_timestamp_str = plant.get("planted_timestamp")
                elapsed_minutes_display = "N/A"
                if planted_timestamp_str:
                    try:
                        planted_datetime = datetime.fromisoformat(planted_timestamp_str)
                        elapsed_minutes_display = f"{int((datetime.now() - planted_datetime).total_seconds() / 60.0)} minutes"
                    except ValueError:
                        pass # Keep N/A on error

                plant_info = self._plant_types.get(plant_type)
                water_status_desc = "N/A"
                if plant_info:
                    water_state = self._get_water_state(plant, plant_info)
                    if water_state == 0: water_status_desc = "Low Water"
                    elif water_state == 1: water_status_desc = "Optimal Water"
                    elif water_state == 2: water_status_desc = "High Water"

                summary_lines.append(
                    f"  Plot {plot_id}: {plant_type} (UID: {plant_uid}) "
                    f"Stage: {current_stage_name} (Time Grown: {elapsed_minutes_display}) "
                    f"Water: {water_level:.2f} ({water_status_desc})"
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
        water_amounts = {
            "low": 0.1,    # Adds 10% to water level
            "medium": 0.25,  # Adds 25% to water level
            "high": 0.5    # Adds 50% to water level
        }

        amount_to_add = water_amounts.get(water_level_type.lower())
        if amount_to_add is None:
            return f"Error: Invalid water level type '{water_level_type}'. Choose from 'low', 'medium', or 'high'."

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