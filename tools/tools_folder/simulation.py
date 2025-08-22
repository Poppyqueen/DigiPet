
#simulation.py

import json
import random
import copy
from typing import List, Dict, Tuple, Any, Optional
import os
from datetime import datetime
import time

from tools.tools_folder.tools_helpers.alife_manager import ALifeManager


class ALifeSimulation:
    """
    A configurable A-Life simulation with plants, herbivores, and carnivores
    on a grid-based environment that can be observed by an AI.
    """

    # Entity type IDs
    PLANT = 0
    HERBIVORE = 1
    CARNIVORE = 2

    # Status constants
    ALIVE = "alive"
    DEAD = "dead"




    def __init__(self, config: Dict[str, Any] = None, archive_path=None, state_manager=None, signal=None):
        """Initialize the ALifeSimulation with optional configuration."""
        self.latest_config_summary = ""
        self.state_manager = state_manager
        self.current_simulation_ID=""
        self._signal_callback=signal

        self.archive_path = archive_path
        if self.archive_path:
            # Create the archive directory if it doesn't exist
            os.makedirs(self.archive_path, exist_ok=True)
            self.simulations_manager = ALifeManager(archive_path) # Initialize manager with archive_path
        else:
            self.simulations_manager = None
            print("Warning: archive_path not provided. Archiving features will be disabled.")

        # Default configuration
        default_config = {
            "grid_size": [5, 5],
            "max_ticks": 20,
            "entity_config": {
                "plant": {
                    "initial_count": 3,
                    "initial_energy": 5,
                    "growth_rate": 0.2,  # Chance to spread each tick
                    "max_energy": 10
                },
                "herbivore": {
                    "initial_count": 2,
                    "initial_energy": 10,
                    "movement_range": 1,
                    "energy_consumption": 1,
                    "reproduction_threshold": 15,
                    "reproduction_cost": 5
                },
                "carnivore": {
                    "initial_count": 1,
                    "initial_energy": 12,
                    "movement_range": 2,
                    "energy_consumption": 2,
                    "reproduction_threshold": 20,
                    "reproduction_cost": 8
                }
            },
            "interaction_rules": {
                "herbivore_eat_plant": 4,  # Energy gained
                "carnivore_eat_herbivore": 8  # Energy gained
            }
        }

        # Use provided config or default
        self.config = default_config
        if config:
            self._deep_update(self.config, config)

        # Initialize simulation state - This happens when the object is created
        self.current_tick = 0
        self.max_ticks = self.config["max_ticks"]
        self.grid_size = self.config["grid_size"]
        self.entities = []
        self.entity_id_counter = 0

        # History for time-scrubbing
        self.history = []

        # Initialize the simulation state (placing initial entities etc.)
        self._init_simulation()


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


    def _deep_update(self, d: Dict, u: Dict) -> Dict:
        """Recursively update a dictionary."""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
        return d

    def _init_simulation(self):
        """
        Initialize the simulation with entities based on configuration.
        Resets internal state variables.
        """
        # Clear existing state
        self.entities = []
        self.entity_id_counter = 0
        self.current_tick = 0
        self.history = [] # Clear history for a new run

        # Ensure grid_size and max_ticks are set from config
        self.grid_size = self.config.get("grid_size", [5, 5])
        self.max_ticks = self.config.get("max_ticks", 20)


        # Create plants
        self._create_initial_entities(
            self.PLANT,
            self.config["entity_config"]["plant"]["initial_count"],
            {
                "energy": self.config["entity_config"]["plant"]["initial_energy"],
                "age": 0,
                "status": self.ALIVE
            }
        )

        # Create herbivores
        self._create_initial_entities(
            self.HERBIVORE,
            self.config["entity_config"]["herbivore"]["initial_count"],
            {
                "energy": self.config["entity_config"]["herbivore"]["initial_energy"],
                "age": 0,
                "status": self.ALIVE
            }
        )

        # Create carnivores
        self._create_initial_entities(
            self.CARNIVORE,
            self.config["entity_config"]["carnivore"]["initial_count"],
            {
                "energy": self.config["entity_config"]["carnivore"]["initial_energy"],
                "age": 0,
                "status": self.ALIVE
            }
        )

        # Store initial state in history
        self._save_current_state()


    def _create_initial_entities(self, type_id: int, count: int, state: Dict):
        """Create initial entities of a specific type."""
        entities_created = 0
        max_attempts = self.grid_size[0] * self.grid_size[1] * 5 # Prevent infinite loops on full grid
        attempts = 0

        while entities_created < count and attempts < max_attempts:
            attempts += 1
            # Find an unoccupied position
            pos = [random.randint(0, self.grid_size[0]-1),
                   random.randint(0, self.grid_size[1]-1)]

            # Check if position is empty
            if not self._get_entity_at_position(pos):
                # Create the entity
                entity = {
                    "id": f"E{self.entity_id_counter}",
                    "type_id": type_id,
                    "pos": pos,
                    "state": copy.deepcopy(state)
                }

                self.entities.append(entity)
                self.entity_id_counter += 1
                entities_created += 1

        if entities_created < count:
            print(f"Warning: Could only place {entities_created}/{count} entities of type {type_id} due to grid full or placement issues.")

    def _get_entity_at_position(self, pos: List[int]) -> Optional[Dict]:
        """Get entity at a specific position if any (only checks ALIVE entities)."""
        # Iterate in reverse to potentially find recently added entities faster? Or just standard order.
        for entity in self.entities:
            if entity["pos"] == pos and entity["state"]["status"] == self.ALIVE:
                return entity
        return None

    def _get_entities_by_type(self, type_id: int) -> List[Dict]:
        """Get all entities of a specific type (only ALIVE entities)."""
        # Return a list copy ([...]) to avoid modifying the list while iterating in processing loops
        return [e for e in self.entities if e["type_id"] == type_id and e["state"]["status"] == self.ALIVE]

    def _get_distance(self, pos1: List[int], pos2: List[int]) -> int:
        """Calculate Manhattan distance between two positions."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _get_adjacent_positions(self, pos: List[int], distance: int = 1) -> List[List[int]]:
        """Get all valid positions at a specific Manhattan distance."""
        adjacent = []
        # Iterate through all possible relative positions up to the max distance
        max_dist = distance
        for dx in range(-max_dist, max_dist + 1):
            for dy in range(-max_dist, max_dist + 1):
                # Check if this relative position is exactly the desired Manhattan distance
                if abs(dx) + abs(dy) == distance:
                    new_x = pos[0] + dx
                    new_y = pos[1] + dy

                    # Check bounds
                    if 0 <= new_x < self.grid_size[0] and 0 <= new_y < self.grid_size[1]:
                        adjacent.append([new_x, new_y])

        return adjacent
    
    def _cleanup_dead_entities(self) -> None:
        """
        Remove entities that have been dead for more than one tick.
        Uses the death_tick counter to determine which dead entities to remove.
        Called at the end of each tick's processing.
        """
        # Keep entities that are either: (1) alive OR (2) recently dead (death_tick <= 1)
        self.entities = [entity for entity in self.entities if 
                        entity["state"]["status"] == self.ALIVE or 
                        (entity["state"]["status"] == self.DEAD and 
                        entity["state"].get("death_tick", 0) <= 1)]

    def _move_toward(self, entity: Dict, target_pos: List[int]) -> None:
        """Move entity one step toward target position if possible (unoccupied)."""
        current_pos = entity["pos"]
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]

        # Determine movement direction (prioritize axis with larger difference, tie-break randomly?)
        # Simple approach: Choose one axis based on which difference is larger.
        # If equal, pick one (e.g., horizontal first).
        move_options = []
        if dx != 0:
            move_options.append([current_pos[0] + (1 if dx > 0 else -1), current_pos[1]])
        if dy != 0:
            move_options.append([current_pos[0], current_pos[1] + (1 if dy > 0 else -1)])

        if not move_options: # Already at target or no movement possible
            return

        # Prioritize moves that get closer or maintain distance if blocked, prefer open cells
        random.shuffle(move_options) # Shuffle to add some randomness in tie-breaking
        best_move = None
        current_dist = self._get_distance(current_pos, target_pos)

        for next_pos in move_options:
            # Check bounds (should be covered by _get_adjacent_positions but double check)
            if not (0 <= next_pos[0] < self.grid_size[0] and 0 <= next_pos[1] < self.grid_size[1]):
                continue

            # Check if cell is occupied (only by ALIVE entities)
            if self._get_entity_at_position(next_pos):
                continue # Cannot move to occupied cell

            # If we found a valid move, pick the first one (due to shuffling, it's somewhat random)
            # or pick one that reduces distance if possible
            next_dist = self._get_distance(next_pos, target_pos)
            if next_dist < current_dist:
                 best_move = next_pos # Found a move that gets strictly closer
                 break # Prioritize getting closer
            elif best_move is None: # If no closer move found yet, keep this as a possibility
                 best_move = next_pos # Keep the first valid move found (might be diagonal or same distance if blocked)


        if best_move:
            entity["pos"] = best_move


    def _save_current_state(self) -> None:
        """Save the current state to history."""
        state = {
            "tick": self.current_tick,
            "entities": copy.deepcopy(self.entities), # Deep copy ensures entities state at this tick is preserved
            "grid_size": self.grid_size
        }
        self.history.append(state)

    def _process_plants(self) -> None:
        """Process plant behavior."""
        plants = self._get_entities_by_type(self.PLANT) # Gets list of ALIVE plants

        # Plants try to grow to adjacent cells (distance 1)
        for plant in plants:
            # Increase energy
            plant_config = self.config["entity_config"]["plant"]
            plant["state"]["energy"] = min(
                plant["state"]["energy"] + 1,
                plant_config["max_energy"]
            )

            # Try to spread to adjacent cells
            if random.random() < plant_config["growth_rate"]:
                adjacent = self._get_adjacent_positions(plant["pos"], distance=1)
                random.shuffle(adjacent) # Randomize order of checking adjacent cells

                for new_pos in adjacent:
                    if not self._get_entity_at_position(new_pos): # Check if target cell is empty
                        # Create a new plant
                        new_plant = {
                            "id": f"E{self.entity_id_counter}",
                            "type_id": self.PLANT,
                            "pos": new_pos,
                            "state": {
                                "energy": plant_config["initial_energy"],
                                "age": 0,
                                "status": self.ALIVE
                            }
                        }

                        self.entities.append(new_plant) # Add to the active list
                        self.entity_id_counter += 1
                        break  # Only create one plant per successful spreading attempt

    def _process_herbivores(self) -> None:
        """Process herbivore behavior."""
        herbivores = self._get_entities_by_type(self.HERBIVORE) # Gets list of ALIVE herbivores
        herbivore_config = self.config["entity_config"]["herbivore"]
        interaction_rules = self.config["interaction_rules"]

        # Process herbivores in a random order to avoid bias based on list index
        random.shuffle(herbivores)

        for herbivore in herbivores:
             # Note: Status check already done by _get_entities_by_type

            # Decrease energy
             herbivore["state"]["energy"] -= herbivore_config["energy_consumption"]

            # Check if herbivore dies
             if herbivore["state"]["energy"] <= 0:
                 herbivore["state"]["status"] = self.DEAD
                 herbivore["state"]["death_tick"] = 0

                 continue # Stop processing this herbivore for this tick

            # Find and eat plants
             plants = self._get_entities_by_type(self.PLANT) # Gets list of ALIVE plants
             # Find closest plant within movement range
             closest_plant = None
             min_dist = float('inf')

             # Find the closest plant among all ALIVE plants
             for plant in plants:
                 dist = self._get_distance(herbivore["pos"], plant["pos"])
                 if dist < min_dist and dist <= herbivore_config["movement_range"]: # Check distance <= movement_range
                     min_dist = dist
                     closest_plant = plant

             if closest_plant:
                 # If adjacent (distance 1), eat plant
                 if min_dist == 1:
                     # Ensure the plant is still alive before eating (might have been eaten by another herbivore this tick)
                     # Check again from the full entities list as _get_entities_by_type is a snapshot at start of method
                     # Or, simpler, just check the status of the specific plant found
                     if closest_plant["state"]["status"] == self.ALIVE:
                         herbivore["state"]["energy"] += interaction_rules["herbivore_eat_plant"]
                         closest_plant["state"]["status"] = self.DEAD # Mark plant as dead
                         closest_plant["state"]["death_tick"] = 0


                 # Otherwise move toward plant (if distance > 1 and <= movement_range)
                 elif min_dist > 1:
                    self._move_toward(herbivore, closest_plant["pos"])

             else:
                 # Move randomly if no plant is in range or none are alive
                 adjacent = self._get_adjacent_positions(herbivore["pos"], distance=1) # Get adjacent cells (dist 1)
                 valid_moves = [pos for pos in adjacent if not self._get_entity_at_position(pos)] # Filter for empty cells
                 if valid_moves:
                     herbivore["pos"] = random.choice(valid_moves) # Move to a random empty adjacent cell

            # Reproduction - check energy *after* movement/eating
             if herbivore["state"]["status"] == self.ALIVE and herbivore["state"]["energy"] >= herbivore_config["reproduction_threshold"]:
                 adjacent = self._get_adjacent_positions(herbivore["pos"], distance=1) # Offspring appears in adjacent cell
                 valid_cells = [pos for pos in adjacent if not self._get_entity_at_position(pos)] # Find empty adjacent cells

                 if valid_cells:
                     # Create offspring
                     offspring_pos = random.choice(valid_cells)
                     offspring = {
                         "id": f"E{self.entity_id_counter}",
                         "type_id": self.HERBIVORE,
                         "pos": offspring_pos,
                         "state": {
                             "energy": herbivore_config["initial_energy"], # Offspring starts with initial energy
                             "age": 0,
                             "status": self.ALIVE
                         }
                     }

                     self.entities.append(offspring) # Add to the active list
                     self.entity_id_counter += 1

                     # Deduct reproduction cost from parent
                     herbivore["state"]["energy"] -= herbivore_config["reproduction_cost"]


    def _process_carnivores(self) -> None:
        """Process carnivore behavior."""
        carnivores = self._get_entities_by_type(self.CARNIVORE) # Gets list of ALIVE carnivores
        carnivore_config = self.config["entity_config"]["carnivore"]
        interaction_rules = self.config["interaction_rules"]

        # Process carnivores in a random order
        random.shuffle(carnivores)

        for carnivore in carnivores:
             # Note: Status check already done by _get_entities_by_type

            # Decrease energy
             carnivore["state"]["energy"] -= carnivore_config["energy_consumption"]

            # Check if carnivore dies
             if carnivore["state"]["energy"] <= 0:
                 carnivore["state"]["status"] = self.DEAD
                 carnivore["state"]["death_tick"] = 0
                 
                 continue # Stop processing this carnivore for this tick

            # Find and hunt herbivores
             herbivores = self._get_entities_by_type(self.HERBIVORE) # Gets list of ALIVE herbivores
             # Find closest herbivore within movement range
             closest_herbivore = None
             min_dist = float('inf')

             # Find the closest herbivore among all ALIVE herbivores
             for herbivore in herbivores:
                  dist = self._get_distance(carnivore["pos"], herbivore["pos"])
                  if dist < min_dist and dist <= carnivore_config["movement_range"]: # Check distance <= movement_range
                     min_dist = dist
                     closest_herbivore = herbivore

             if closest_herbivore:
                # If adjacent (distance 1), eat herbivore
                if min_dist == 1:
                    # Ensure the herbivore is still alive before eating
                    if closest_herbivore["state"]["status"] == self.ALIVE:
                        carnivore["state"]["energy"] += interaction_rules["carnivore_eat_herbivore"]
                        closest_herbivore["state"]["status"] = self.DEAD # Mark herbivore as dead
                        closest_herbivore["state"]["death_tick"] = 0
                # Otherwise move toward herbivore (if distance > 1 and <= movement_range)
                elif min_dist > 1:
                    self._move_toward(carnivore, closest_herbivore["pos"])

             else:
                 # Move randomly if no herbivore is in range or none are alive
                 adjacent = self._get_adjacent_positions(carnivore["pos"], distance=1) # Get adjacent cells (dist 1)
                 valid_moves = [pos for pos in adjacent if not self._get_entity_at_position(pos)] # Filter for empty cells
                 if valid_moves:
                     carnivore["pos"] = random.choice(valid_moves) # Move to a random empty adjacent cell

            # Reproduction - check energy *after* movement/eating
             if carnivore["state"]["status"] == self.ALIVE and carnivore["state"]["energy"] >= carnivore_config["reproduction_threshold"]:
                 adjacent = self._get_adjacent_positions(carnivore["pos"], distance=1) # Offspring appears in adjacent cell
                 valid_cells = [pos for pos in adjacent if not self._get_entity_at_position(pos)] # Find empty adjacent cells

                 if valid_cells:
                     # Create offspring
                     offspring_pos = random.choice(valid_cells)
                     offspring = {
                         "id": f"E{self.entity_id_counter}",
                         "type_id": self.CARNIVORE,
                         "pos": offspring_pos,
                         "state": {
                             "energy": carnivore_config["initial_energy"], # Offspring starts with initial energy
                             "age": 0,
                             "status": self.ALIVE
                         }
                     }

                     self.entities.append(offspring) # Add to the active list
                     self.entity_id_counter += 1

                     # Deduct reproduction cost from parent
                     carnivore["state"]["energy"] -= carnivore_config["reproduction_cost"]


    def _update_ages(self) -> None:
        """Update ages of all living entities and death_tick counters of dead entities."""
        for entity in self.entities:
            if entity["state"]["status"] == self.ALIVE:
                # Update age for living entities
                entity["state"]["age"] += 1
            elif entity["state"]["status"] == self.DEAD:
                # Update death_tick for dead entities
                if "death_tick" in entity["state"]:
                    entity["state"]["death_tick"] += 1


    def step(self) -> bool:
        """
        Advance the simulation by one tick.
        Processes entity actions and saves the resulting state.
        Returns True if the simulation can continue (hasn't reached max_ticks), False otherwise.
        """
        # Check if max_ticks is already reached
        if self.current_tick >= self.max_ticks:
             # Cannot step beyond max_ticks
             return False

        # Ensure the state for the current tick is loaded before processing
        # This is important if set_current_tick_ALIFE was used.
        if self.current_tick < len(self.history):
             # Load the state corresponding to self.current_tick from history
             # This prepares self.entities for processing *into* the next tick (current_tick + 1)
             self.entities = copy.deepcopy(self.history[self.current_tick]["entities"])
             self.grid_size = self.history[self.current_tick]["grid_size"]
             # Note: self.max_ticks and self.entity_id_counter are instance-level, not per-tick

        elif self.current_tick == len(self.history):
             # This is the expected case when stepping forward normally
             # The entities state is already what resulted from the previous tick's processing
             # (which was saved as history[current_tick-1]).
             # Nothing specific to load here, self.entities is ready.
             pass # self.entities holds the state from the end of the previous tick's process

        else:
             # Current tick is beyond available history AND not just the next tick index
             print(f"Error: Cannot step from tick {self.current_tick}. History is only {len(self.history)} ticks long.")
             return False


        # Process entity behaviors for the *transition* from current_tick to current_tick + 1
        # Note: Processing order can affect outcomes! (Plants -> Herbivores -> Carnivores)
        self._process_plants()
        self._process_herbivores()
        self._process_carnivores()

        # Update ages of all living entities *after* behaviors
        self._update_ages()
        self._cleanup_dead_entities()
        # Increment tick counter (we are now at the *end* of the actions for the old current_tick)
        self.current_tick += 1

        # Save the state *resulting from* this tick's actions.
        # This state corresponds to self.current_tick - 1 in the history *before* the increment,
        # but we save it as the state *at* the new self.current_tick.
        # The history list should store states for ticks 0, 1, 2... up to max_ticks.
        # If current_tick becomes max_ticks + 1, we should NOT save another state.
        if self.current_tick <= self.max_ticks:
             self._save_current_state()
             # After saving, self.entities contains the state for the new self.current_tick

        # Determine if simulation should continue
        return self.current_tick <= self.max_ticks # Continue if the *next* tick (current_tick now) is <= max_ticks


    def run_simulation(self, new_run: bool = False) -> None:
        """
        Run the entire simulation from current state to max_ticks.

        Args:
            new_run (bool): If True, re-initializes the simulation and re-seeds
                            the random generator before running.
        """
        if new_run:
            print("Starting a brand new simulation run...")
            random.seed(None) # Re-seed the random number generator using system time
            self._init_simulation() # Reset state (clears history too, sets current_tick to 0)
            self.max_ticks = self.config.get("max_ticks", 20) # Reset max_ticks based on config
            # _init_simulation already saved the state for tick 0.
            # The loop below will run from tick 1 up to max_ticks.

        print(f"Running simulation from tick {self.current_tick} up to tick {self.max_ticks} (inclusive)...")

        # If we are already at or past max_ticks, the loop won't run
        # The loop continues as long as step() successfully advances *and* indicates more ticks are possible
        initial_tick = self.current_tick
        ticks_ran = 0
        while self.step():
             ticks_ran += 1
             # Optional: Add a small delay or progress print if running long simulations
             # print(f"Completed tick {self.current_tick - 1}") # Print the tick that just finished processing

             # Prevent infinite loops if simulation state becomes stuck
             if ticks_ran > self.max_ticks * 2 and self.current_tick > self.max_ticks:
                  print("Warning: Simulation running unexpectedly long. Stopping.")
                  break

        print(f"Simulation finished. Ran {ticks_ran} steps starting from tick {initial_tick}. Current tick is {self.current_tick}.")
        # After the loop, self.current_tick is typically max_ticks + 1 if it completed fully.
        # Or it might be less if `step()` returned False early for another reason (e.g. no entities left).
        # The history will contain states from 0 up to the last successfully processed tick.

    def reset(self) -> None:
        """Reset the simulation instance to its initial state based on config."""
        print("Resetting simulation state based on current configuration...")
        self._init_simulation()
        # Note: This does NOT re-seed random. Use run_simulation(new_run=True) for that if needed.

    # AI  TOOLS

    def set_current_tick_ALIFE(self, tick:int) -> str:
        """
        Set the current tick of the simulation to the given argument (int).
        Allows viewing specific moments in the simulation history.
        Loads the state corresponding to the specified tick from history.
        """
        if not self.history:
             return "Error: No simulation history available to set the tick."

        max_valid_tick = len(self.history) - 1

        if not isinstance(tick, int) or tick < 0:
             return f"Error: Invalid tick value '{tick}'. Must be a non-negative integer."

        if tick > max_valid_tick:
            return f"Error: Tried to set tick to {tick}, which is larger than the last available tick ({max_valid_tick}) in the current history."
        else:
            self.current_tick= tick
            # Load the state from history so observe() reflects it
            try:
                state_at_tick = self.history[self.current_tick]
                self.entities = copy.deepcopy(state_at_tick["entities"])
                self.grid_size = state_at_tick["grid_size"]
                # Note: self.max_ticks and self.entity_id_counter are instance-level attributes
                # reflecting the overall run, not per-tick state, and are not loaded here.
            except IndexError:
                 # This should ideally not happen due to the tick > max_valid_tick check
                 return f"Error: Failed to load state for tick {tick}. History length is {len(self.history)}."

            self.state_manager.set_sim_state(sim_current_step=self.current_tick)
            return f"Successfully set the current tick to {tick} of {max_valid_tick}."
        
    def observe_ALIFE(self) -> str:
        """
        Return a structured representation of the current state of the simulation as a JSON string.
        Includes basic information for the current tick: tick number, grid size,
        and a list of entities with their ID, type ID (0, 1, or 2), position, and status.
        This is one of the three tools available to the AI.
        """
        # Ensure history exists and current_tick is valid
        if not self.history:
             # Provide a minimal observation if simulation is just initialized but not run
             if self.current_tick == 0:
                  # Construct a minimal state dictionary from current instance attributes
                  current_state_data = {
                      "tick": self.current_tick,
                      "max_ticks": self.max_ticks,
                      "grid_size": self.grid_size,
                      "entities": [], # No entities in history yet, show current if any exist? No, stick to history concept. Empty list for initial state.
                      "message": "Simulation initialized but no history recorded yet (run step() or run_simulation())."
                  }
                  return json.dumps(current_state_data)
             else:
                  # Should not happen if navigation tools are used correctly, but handle defensively
                  return json.dumps({"error": f"Observation Error: Simulation history is empty or corrupt at tick {self.current_tick}."})


        max_historical_tick = len(self.history) - 1
        if self.current_tick < 0 or self.current_tick > max_historical_tick:
             return json.dumps({"error": f"Observation Error: Current tick {self.current_tick} is out of bounds for available history (0 to {max_historical_tick})."})

        # Get the state data from history for the current tick
        # history[k] contains the state AT THE START of tick k (after tick k-1 finished)
        state_data_from_history = self.history[self.current_tick]

        # Extract relevant data fields from the historical state
        tick_num = state_data_from_history.get("tick", self.current_tick) # Prefer tick from history, fallback to instance
        grid_size = state_data_from_history.get("grid_size", self.grid_size) # Prefer grid_size from history state
        raw_entities = state_data_from_history.get("entities", []) # List of entities at this state

        # Filter and structure the entity data to be included
        filtered_entities = []
        for entity in raw_entities:
            # Extract only the requested basic fields, ensuring they exist or providing defaults
            filtered_entity = {
                "id": entity.get("id", "N/A"),
                "type_id": entity.get("type_id", -1), # Use -1 for unknown type
                "pos": entity.get("pos", [None, None]),
                # Include status as it's critical for knowing if an entity is active
                "energy": entity.get("state", {}).get("energy", 0),
                "status": entity.get("state", {}).get("status", "unknown"),

            }
            filtered_entities.append(filtered_entity)


        # Construct the final, simplified state dictionary
        observed_state = {
            "sim_ID": self.current_simulation_ID,
            "tick": tick_num,
            # Note: max_ticks is the *configured* maximum, not the last tick in history.
            # Let's include both for clarity.
            "configured_max_ticks": self.max_ticks,
            "last_history_tick": max_historical_tick,
            "grid_size": grid_size,
            "entities": filtered_entities
        }
        self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/alife_examine.png"})

        # Return the JSON string representation
        return json.dumps(observed_state, indent=2)
            
    def forward_ALIFE(self) -> str:
        """
        Move one tick forward in the simulation history.
        Loads the state from history at the new tick.
        Returns a message indicating the new tick number.
        This is one of the three tools available to the AI.
        """
        if not self.history:
             return "Simulation is not initialized or has no history to move forward."

        max_valid_tick = len(self.history) - 1

        if self.current_tick < max_valid_tick:
            self.current_tick += 1
            # Load the state for the new current_tick using set_current_tick_ALIFE for consistency
            self.set_current_tick_ALIFE(self.current_tick) # This also validates and loads state
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/alife_scroll.png"})

            return f"Moved forward to tick {self.current_tick} of {max_valid_tick}. {self.observe_ALIFE()}"
        else:
            return f"Already at the last tick ({self.current_tick} of {max_valid_tick}). Cannot move forward."

    def backward_ALIFE(self) -> str:
        """
        Move one tick backward in the simulation history.
        Loads the state from history at the new tick.
        Returns a message indicating the new tick number.
        This is one of the three tools available to the AI.
        """
        if not self.history:
             return "Simulation is not initialized or has no history to move backward."

        max_valid_tick = len(self.history) - 1

        if self.current_tick > 0:
            self.current_tick -= 1
            # Load the state for the new current_tick using set_current_tick_ALIFE for consistency
            self.set_current_tick_ALIFE(self.current_tick) # This also validates and loads state
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/alife_scroll.png"})

            return f"Moved backward to tick {self.current_tick} of {max_valid_tick}. {self.observe_ALIFE()}"
        else:
            return f"Already at the first tick (0 of {max_valid_tick}). Cannot move backward."


    def get_visualization(self) -> str:
        """
        Create a simple ASCII visualization of the current state (`self.current_tick`).
        Uses entity type IDs (0, 1, 2) mapping them to P, H, C for the grid display.
        This visualization provides positional information and basic counts.
        """
        if not self.history or self.current_tick >= len(self.history):
             if not self.history:
                 return "Visualization Error: Simulation not initialized or has no history."
             else:
                 return f"Visualization Error: Current tick {self.current_tick} out of history bounds (0 to {len(self.history)-1})."

        # Get the state for the current tick from history
        state = self.history[self.current_tick]
        grid_size = state.get("grid_size", [5, 5]) # Use get with default for safety

        # Create an empty grid representation (using state's grid_size)
        grid = [[' ' for _ in range(grid_size[0])] for _ in range(grid_size[1])]

        # Map entity type IDs to characters for the visualization
        type_map = {
            self.PLANT: '0',
            self.HERBIVORE: '1',
            self.CARNIVORE: '2'
        }

        # Fill in entities (only alive ones for visualization) and count them
        plants_alive = 0
        herbivores_alive = 0
        carnivores_alive = 0

        for entity in state["entities"]:
            if entity["state"].get("status") == self.ALIVE:
                pos = entity.get("pos")
                type_id = entity.get("type_id")

                if pos and type_id is not None: # Basic check for required keys
                    x, y = pos
                    # Check bounds again just to be safe
                    if 0 <= x < grid_size[0] and 0 <= y < grid_size[1]:
                        grid[y][x] = type_map.get(type_id, '?') # Use '?' for unknown types

                        # Count entities
                        if type_id == self.PLANT:
                            plants_alive += 1
                        elif type_id == self.HERBIVORE:
                            herbivores_alive += 1
                        elif type_id == self.CARNIVORE:
                            carnivores_alive += 1


        # Convert grid to string
        visualization = f"Tick {self.current_tick} of {len(self.history) - 1}\n" # Show total ticks
        visualization += '+' + '-' * grid_size[0] + '+\n'
        for row in grid:
            visualization += '|' + ''.join(row) + '|\n'
        visualization += '+' + '-' * grid_size[0] + '+\n'

        # Add entity counts based on the *current* state in history
        visualization += f"Alive counts: Type 0: {plants_alive}, Type 1: {herbivores_alive}, Type 2: {carnivores_alive}\n"

        return visualization


    def archive_simulation_run(self):
        """
        Archive the completed simulation run by saving:
        1. A JSON file with the complete simulation history
        2. A text file with the visualization of each tick and simulation metadata

        Args:
            self: ALifesimulation instance that has completed a run (history is populated)

        Returns:
            str: A message indicating success or failure, including the simulation ID.
        """
        if not self.archive_path or not self.simulations_manager:
             return "Archiving is disabled because archive_path was not provided during initialization."

        if not self.history:
             return "Error: No simulation history to archive."

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        timestamp_time = int(time.time())
        run_filename_base = f"SIM_{timestamp_str}_{timestamp_time}"

        json_file_name = f"{run_filename_base}.json"
        txt_file_name = f"{run_filename_base}.txt"

        json_file_path = os.path.join(self.archive_path, json_file_name)
        txt_file_path = os.path.join(self.archive_path, txt_file_name)

        try:
            # Save the JSON history
            # Include the final entity_id_counter for potential future resuming/analysis
            manager_result = self.simulations_manager.create_entry(json_file_path)

            run_data = {
                "simulation_ID": manager_result.get("simulation_ID", None),
                "config": self.config,
                "history": self.history,
                "final_entity_id_counter": self.entity_id_counter # Store final value
                
            }
            with open(json_file_path, 'w') as f:
                json.dump(run_data, f, indent=2)

        # Delegate registering the archived file to the manager
            # Save the visualizations and metadata
            with open(txt_file_path, 'w') as f:
                # Write simulation metadata
                f.write("=" * 60 + "\n")
                f.write("A-LIFE simulation ARCHIVE\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Simulation ID:{manager_result.get("simulation_ID", None)}\n\n")
                f.write("=" * 60 + "\n\n")

                # Write configuration information
                f.write("CONFIGURATION\n")
                f.write("-" * 60 + "\n")
                f.write(f"Grid Size: {self.grid_size[0]} x {self.grid_size[1]}\n")
                f.write(f"Configured Max Ticks: {self.config.get('max_ticks', 'N/A')}\n\n")

                # Write entity type information (still useful for understanding the text file)
                f.write("ENTITY TYPES\n")
                f.write("-" * 60 + "\n")
                f.write(f"Type ID {self.PLANT}: Plant (P on grid)\n")
                for k, v in self.config.get('entity_config', {}).get('plant', {}).items():
                    f.write(f"  - {k}: {v}\n")
                f.write("\n")

                f.write(f"Type ID {self.HERBIVORE}: Herbivore (H on grid)\n")
                for k, v in self.config.get('entity_config', {}).get('herbivore', {}).items():
                    f.write(f"  - {k}: {v}\n")
                f.write(f"  - Energy Gained from eating plants: {self.config.get('interaction_rules', {}).get('herbivore_eat_plant', 'N/A')}\n")
                f.write("\n")

                f.write(f"Type ID {self.CARNIVORE}: Carnivore (C on grid)\n")
                for k, v in self.config.get('entity_config', {}).get('carnivore', {}).items():
                    f.write(f"  - {k}: {v}\n")
                f.write(f"  - Energy Gained from eating herbivores: {self.config.get('interaction_rules', {}).get('carnivore_eat_herbivore', 'N/A')}\n")
                f.write("\n")


                f.write("simulation BEHAVIORS (Based on configuration):\n")
                f.write("-" * 60 + "\n")
                f.write("1. Plants grow energy and attempt to spread (P).\n")
                f.write("2. Herbivores consume energy, move toward and eat plants (H).\n")
                f.write("3. Carnivores consume energy, move toward and eat herbivores (C).\n")
                f.write("4. Animals reproduce when energy is high enough.\n")
                f.write("5. Entities die when energy is zero or less.\n")
                f.write("6. Entity types are inferred by their behaviors and appearance (P, H, C) on the grid.\n\n") # Hint for AI


                # Write visualizations for each tick
                f.write("simulation VISUALIZATION TIMELINE\n")
                f.write("-" * 60 + "\n\n")

                # Store the current tick so we can restore it
                original_tick = self.current_tick

                # Loop through all ticks in the history
                for tick in range(len(self.history)):
                    # Temporarily set the tick to generate visualization
                    # set_current_tick_ALIFE handles loading state and bounds check safely
                    self.set_current_tick_ALIFE(tick)
                    visualization = self.get_visualization()
                    f.write(visualization)
                    f.write("\n" + "-" * 40 + "\n\n")

                # Restore the original tick index and state
                self.set_current_tick_ALIFE(original_tick)


                # Write summary statistics
                if self.history:
                     final_state = self.history[-1]
                     plants_alive = sum(1 for e in final_state.get("entities", []) if e.get("type_id") == self.PLANT and e.get("state", {}).get("status") == self.ALIVE)
                     herbivores_alive = sum(1 for e in final_state.get("entities", []) if e.get("type_id") == self.HERBIVORE and e.get("state", {}).get("status") == self.ALIVE)
                     carnivores_alive = sum(1 for e in final_state.get("entities", []) if e.get("type_id") == self.CARNIVORE and e.get("state", {}).get("status") == self.ALIVE)

                     f.write("\nFINAL STATISTICS\n")
                     f.write("-" * 60 + "\n")
                     f.write(f"Total Ticks Simulated: {len(self.history) -1} (from tick 0 to {len(self.history)-1})\n")
                     f.write(f"Total Entities Generated (ever in this run): {self.entity_id_counter}\n")
                     f.write(f"Plants Remaining: {plants_alive}\n")
                     f.write(f"Herbivores Remaining: {herbivores_alive}\n")
                     f.write(f"Carnivores Remaining: {carnivores_alive}\n")
                else:
                     f.write("\nNo history available for final statistics.\n")


        except Exception as e:
             print(f"An error occurred during archiving: {e}")
             # Clean up potentially half-written files
             if os.path.exists(json_file_path): os.remove(json_file_path)
             if os.path.exists(txt_file_path): os.remove(txt_file_path)
             return f"Error archiving simulation: {e}"


        if "Error" in manager_result:
             print(f"Warning: Archived files created ({json_file_path}, {txt_file_path}), but failed to register with ALifeManager: {manager_result}")
             return f"Archived files created, but failed to register with manager: {manager_result}"
        else:
            # The manager's create_entry returns a message including the new ID
            # We can try to parse the ID from the message or adjust create_entry to return it.
            # For now, let's just return the manager's message.
            return manager_result


    def load_previous_simulation(self, simulation_id: str, tick:int=0)  -> str:
        """
        Given a simulation ID from the archive, loads its history into the current
        simulation instance. Sets the current tick to 0 for viewing.

        Args:
            simulation_id (str): The ID of the simulation to load from the archive.

        Returns:
            str: A string indicating success or failure.
        """
        if not self.simulations_manager:
            return "Error: Archiving is disabled. Cannot load previous simulations."

        if simulation_id not in self.simulations_manager._state:
            return f"Error: Could not find simulation with ID '{simulation_id}' in the archive."

        try:
            simulation_data_meta = self.simulations_manager._state[simulation_id]
            archive_file_path = simulation_data_meta.get("simulation_file_path")

            if not archive_file_path or not os.path.exists(archive_file_path):
                 return f"Error: Archive file path missing or file not found for simulation ID '{simulation_id}' at expected location '{archive_file_path}'."

            with open(archive_file_path, 'r') as f:
                archived_data = json.load(f)

            # Validate archived_data structure
            if not isinstance(archived_data, dict) or "config" not in archived_data or "history" not in archived_data:
                 return f"Error: Archived data for simulation ID '{simulation_id}' is in an unexpected format."

            # --- Load the archived state into the current instance ---
            self.config = archived_data["config"] # Load the configuration
            self.history = archived_data["history"] # Load the full history
            # Use get with default for safety, entity_id_counter might be missing in older archives
            self.entity_id_counter = archived_data.get("final_entity_id_counter", 0) # Load the entity counter state

            # Update instance attributes based on loaded data/config
            # Use .get() with defaults in case config is missing keys (robustness)
            self.grid_size = self.config.get("grid_size", [5, 5])
            # max_ticks for *viewing* or *resuming* should be the last tick index in history
            self.max_ticks = len(self.history) - 1 # Last tick index

            # Set current state to the beginning of the loaded history for viewing
            if self.history:
                 self.current_tick = tick # Set to the requested tick (0 for start)
                 # Load the entity state corresponding to the new current_tick (which is 0)
                 # Use set_current_tick_ALIFE to ensure state is loaded correctly
                 load_state_status = self.set_current_tick_ALIFE(self.current_tick) # This updates self.entities and self.grid_size
                 if "Error" in load_state_status:
                      # This indicates an issue even loading tick 0, which shouldn't happen if history is valid
                      return f"Error loading simulation ID '{simulation_id}': Could not load initial state from history. {load_state_status}"

            else:
                 # Handle case where history is empty (shouldn't happen with proper archiving)
                 self.current_tick = 0
                 self.entities = []
                 self.grid_size = self.config.get("grid_size", [5,5]) # Reset grid size from config

            self.current_simulation_ID=simulation_id

            return f"Successfully loaded simulation with ID '{simulation_id}'. Current tick is set to {self.current_tick} (start of loaded history). Total ticks in history: {len(self.history)-1}."

        except FileNotFoundError:
            # This case should ideally be caught by the os.path.exists check, but good to have
            return f"Error: Archive file not found at '{archive_file_path}' for simulation ID '{simulation_id}'."
        except json.JSONDecodeError:
             return f"Error: Could not decode JSON from archive file '{archive_file_path}' for simulation ID '{simulation_id}'."
        except Exception as e:
            # Catch any other unexpected errors during loading
            print(f"An unexpected error occurred while loading simulation ID '{simulation_id}': {e}")
            return f"Error loading simulation ID '{simulation_id}': An internal error occurred."

    def create_new_simulation(self, grid_size=None, max_ticks=None, type_0_init_count=None, type_1_init_count=None, type_2_init_count=None, new_name=None, internal=False):
        """
        Creates, runs, and archives a completely new simulation.
        Optionally takes arguments to configure the new run.
        """
        print("Attempting to create, run, and archive a new simulation...")

        # Get current default/base settings from the simulation instance config
        # Assuming self.config is initialized with defaults elsewhere upon object creation
        # Initialize working variables with current config values (defaults if this is the first run)
        # Use list copy for grid_size to avoid modifying original config reference too early
        settings_grid_size_list = list(self.config.get("grid_size", [5, 5]))
        settings_max_ticks = self.config.get("max_ticks", 20)
        settings_type_0_init_count = self.config.get("entity_config", {}).get("plant", {}).get("initial_count", 3)
        settings_type_1_init_count = self.config.get("entity_config", {}).get("herbivore", {}).get("initial_count", 2)
        settings_type_2_init_count = self.config.get("entity_config", {}).get("carnivore", {}).get("initial_count", 1)

        config_notes = [] # List to collect notes about config application, validation, clamping


        # --- Process and Validate Input Arguments ---
        # Check if arguments were explicitly provided (are not None) and apply them

        # Process grid_size
        if grid_size is not None: # Check if grid_size was provided (not None)
            # Assume input string format "X,Y"
            if isinstance(grid_size, str) and "," in grid_size:
                try:
                    grid_size_parts = [int(x) for x in grid_size.split(",")]
                    # Allow non-negative values here; clamping happens later
                    if len(grid_size_parts) != 2 or grid_size_parts[0] < 0 or grid_size_parts[1] < 0:
                        raise ValueError("Grid size must contain exactly two non-negative integers.")
                    # Update working variable with validated value
                    settings_grid_size_list = grid_size_parts
                    config_notes.append(f"Grid Size requested: {grid_size_parts[0]},{grid_size_parts[1]}.")
                except (ValueError, TypeError):
                    config_notes.append(f"Invalid grid size format or value '{grid_size}'. Using current setting {settings_grid_size_list[0]},{settings_grid_size_list[1]}.")
            else:
                config_notes.append(f"Invalid grid size type '{type(grid_size).__name__}'. Expected string 'X,Y'. Using current setting {settings_grid_size_list[0]},{settings_grid_size_list[1]}.")


        # Process max_ticks
        if max_ticks is not None: # Check if max_ticks was provided (not None, handles 0)
            try:
                max_ticks_int = int(max_ticks)
                # Apply clamping limits immediately after successful conversion
                clamp_max_ticks = 30
                if max_ticks_int >= clamp_max_ticks:
                    settings_max_ticks = clamp_max_ticks
                    config_notes.append(f"Max ticks clamped to {clamp_max_ticks} (requested {max_ticks}).")
                elif max_ticks_int <= 0:
                    settings_max_ticks = 1
                    config_notes.append(f"Max ticks clamped to 1 (requested {max_ticks}).")
                else:
                    settings_max_ticks = max_ticks_int
                    config_notes.append(f"Max ticks requested: {max_ticks_int}. Final: {settings_max_ticks}.") # Note final if not clamped by range
            except (ValueError, TypeError):
                config_notes.append(f"Invalid max_ticks value '{max_ticks}'. Using current setting {settings_max_ticks}.")


        # Process type_0_init_count
        if type_0_init_count is not None: # Check if argument was provided (not None, handles 0)
            try:
                count_int = int(type_0_init_count)
                # Clamp to 0 if negative
                if count_int < 0:
                    settings_type_0_init_count = 0
                    config_notes.append(f"Type 0 initial count clamped to 0 (requested {type_0_init_count}).")
                else:
                    settings_type_0_init_count = count_int
                    config_notes.append(f"Type 0 initial count requested: {settings_type_0_init_count}.")
            except (ValueError, TypeError):
                config_notes.append(f"Invalid type_0_init_count value '{type_0_init_count}'. Using current setting {settings_type_0_init_count}.")


        # Process type_1_init_count
        if type_1_init_count is not None: # Check if argument was provided (not None, handles 0)
            try:
                count_int = int(type_1_init_count)
                 # Clamp to 0 if negative
                if count_int < 0:
                    settings_type_1_init_count = 0
                    config_notes.append(f"Type 1 initial count clamped to 0 (requested {type_1_init_count}).")
                else:
                    settings_type_1_init_count = count_int
                    config_notes.append(f"Type 1 initial count requested: {settings_type_1_init_count}.")
            except (ValueError, TypeError):
                config_notes.append(f"Invalid type_1_init_count value '{type_1_init_count}'. Using current setting {settings_type_1_init_count}.")

        # Process type_2_init_count
        if type_2_init_count is not None: # Check if argument was provided (not None, handles 0)
            try:
                count_int = int(type_2_init_count)
                 # Clamp to 0 if negative
                if count_int < 0:
                    settings_type_2_init_count = 0
                    config_notes.append(f"Type 2 initial count clamped to 0 (requested {type_2_init_count}).")
                else:
                    settings_type_2_init_count = count_int
                    config_notes.append(f"Type 2 initial count requested: {settings_type_2_init_count}.")
            except (ValueError, TypeError):
                config_notes.append(f"Invalid type_2_init_count value '{type_2_init_count}'. Using current setting {settings_type_2_init_count}.")


        # --- Apply Global Clamping and Constraints after processing individual inputs ---

        # Apply Grid Size Clamping (Max 10x10) - Ensure settings_grid_size_list is used
        original_dims = list(settings_grid_size_list) # Store before potential clamp
        clamped_grid_size = False
        max_grid_size = 5 # Define maximum grid size
        if settings_grid_size_list[0] > max_grid_size:
             settings_grid_size_list[0] = max_grid_size
             clamped_grid_size = True
        if settings_grid_size_list[1] > max_grid_size:
             settings_grid_size_list[1] = max_grid_size
             clamped_grid_size = True
        if clamped_grid_size:
             config_notes.append(f"Grid size final value clamped to {settings_grid_size_list[0]},{settings_grid_size_list[1]}.")

        area = settings_grid_size_list[0] * settings_grid_size_list[1]

        if area <= 0: # Handle 0 or negative area explicitly after clamping
             config_notes.append("Grid area is 0 or less after clamping. Setting all initial counts to 0.")
             settings_type_0_init_count = 0
             settings_type_1_init_count = 0
             settings_type_2_init_count = 0
        else:
            # --- Apply Population Clamping Strategy (Total Population) ---
            # This happens *after* individual counts are determined from input/defaults

            current_total = settings_type_0_init_count + settings_type_1_init_count + settings_type_2_init_count

            # Apply a total population maximum (e.g., 60% of area)
            max_total_entities = int(area * 0.6)

            # If the current total exceeds the total maximum and current_total is positive
            if current_total > max_total_entities and current_total > 0:
                # Scale down proportionally to fit within the total maximum
                scale_factor = max_total_entities / current_total

                settings_type_0_init_count = int(settings_type_0_init_count * scale_factor)
                settings_type_1_init_count = int(settings_type_1_init_count * scale_factor)
                settings_type_2_init_count = int(settings_type_2_init_count * scale_factor)
                config_notes.append(f"Total initial entity count scaled down to {settings_type_0_init_count + settings_type_1_init_count + settings_type_2_init_count} (max allowed {max_total_entities}) due to grid size constraints.")


        # --- Construct the final configuration dictionary ---
        # Use the settings_... variables which now hold the final determined values
        ai_config = {
            "grid_size": settings_grid_size_list, # Use the validated/clamped list
            "max_ticks": settings_max_ticks,
            "entity_config": {
                "plant": { # Type 0
                    "initial_count": settings_type_0_init_count,
                    "initial_energy": 5, "growth_rate": 0.2, "max_energy": 10
                },
                "herbivore": { # Type 1
                    "initial_count": settings_type_1_init_count,
                    "initial_energy": 10, "movement_range": 1, "energy_consumption": 1,
                    "reproduction_threshold": 15, "reproduction_cost": 5
                },
                "carnivore": { # Type 2
                    "initial_count": settings_type_2_init_count,
                    "initial_energy": 12, "movement_range": 2, "energy_consumption": 2,
                    "reproduction_threshold": 20, "reproduction_cost": 8
                }
            },
            "interaction_rules": {
                "herbivore_eat_plant": 4,
                "carnivore_eat_herbivore": 8
            }
        }

        # Update the instance's config with the determined settings
        # Assuming _deep_update merges recursively
        self._deep_update(self.config, ai_config)

        # Initialize the simulation with the determined config
        # This applies the settings in self.config to set up the initial simulation state
        self._init_simulation()
        print("Initialized new simulation with determined configuration.")


        # Build the final configuration summary message
        final_config_summary_parts = []
        final_config_summary_parts.append(f"Grid Size: {self.config['grid_size'][0]},{self.config['grid_size'][1]}")
        final_config_summary_parts.append(f"Max Ticks: {self.config['max_ticks']}")
        final_config_summary_parts.append(f"Type 0 Initial Count: {self.config['entity_config']['plant']['initial_count']}")
        final_config_summary_parts.append(f"Type 1 Initial Count: {self.config['entity_config']['herbivore']['initial_count']}")
        final_config_summary_parts.append(f"Type 2 Initial Count: {self.config['entity_config']['carnivore']['initial_count']}")

        final_config_summary = "Final Settings: " + ", ".join(final_config_summary_parts)
        if config_notes:
            final_config_summary += ". Notes: " + " ".join(config_notes)
        # Add a note if no custom args resulted in notes, implying defaults were largely used
        # Check if any *input* args were provided. If not, note defaults were used.
        elif grid_size is None and max_ticks is None and type_0_init_count is None and type_1_init_count is None and type_2_init_count is None:
             final_config_summary += ". Notes: Default settings used as no custom values were provided."

        self.latest_config_summary=final_config_summary
        # The run_simulation() call handles running the simulation steps
        # new_run=True re-seeds the random generator for a fresh run starting from tick 0
        self.run_simulation(new_run=True)

        # After run_simulation finishes, self.history is populated with states.
        # current_tick is set to the final tick by run_simulation.
        # We usually want to view from the beginning after creation.
        if self.history:
             self.current_tick = 0
             # Assuming set_current_tick_ALIFE loads the state for the given tick number
             self.set_current_tick_ALIFE(self.current_tick)
        else:
             # This case should not happen if run_simulation completes successfully
             self.current_tick = 0
             config_notes.append("Warning: Simulation history is empty after run.") # Add a note


        # Archive the newly completed run
        # This method should use the state from self.config, self.history, self.entity_id_counter etc.
        archive_data = self.archive_simulation_run()
        simulation_id = "Unknown ID" # Default in case archiving fails
        if archive_data:
            simulation_id = archive_data.get("simulation_ID", "Unknown ID")
            self.current_simulation_ID = simulation_id # Store ID on instance

            if new_name:
                # Assuming update_simulation_name takes simulation ID and new name string
                # You might want error handling here if update_simulation_name can fail
                try:
                    self.simulations_manager.update_simulation_name(simulation_id, new_name)
                except Exception as e: # Catch potential errors from manager
                     config_notes.append(f"Warning: Failed to set simulation name '{new_name}': {e}")
                     print(f"Error setting simulation name: {e}")
        else:
            config_notes.append("Warning: Archiving simulation failed.") # Note if archiving failed


        if archive_data:
            self.state_manager.set_sim_state(simulation_id, self.current_tick) # Update state manager with the last tick's state

        # Return a combined system confirmation message
        # Include all gathered notes in the final message
        if internal:
            if archive_data:
                return archive_data.archive_data.get("simulation_ID", "Unknown ID")
            return "Error archiving simulation data."
        return f"System confirmation, New simulation run completed and archived with simulation ID: {simulation_id}, Name:{new_name or 'Unnamed Simulation'}, Configuration: {final_config_summary}. Ready to view from tick {self.current_tick}."


    def display_information(self):
        """
        Gathers and presents comprehensive information about the current simulation state,
        including metadata, configuration, and an ASCII visualization, in a human-readable format.
        """
        # --- 1. Get and Parse Simulation Metadata Details ---
        # The details_of_simulation method returns a string that *contains* JSON
        sim_details_raw_string = self.simulations_manager.details_of_simulation(self.current_simulation_ID)
        sim_details_dict = None # Initialize as None, will be parsed if possible
        metadata_status_message = ""

        if "Error: Simulation with ID" in sim_details_raw_string:
            # Handle the case where the simulation ID is not found in the manager
            metadata_status_message = f"Note: Simulation with ID '{self.current_simulation_ID}' not found in archive. Metadata details are unavailable."
        else:
            # Attempt to parse the JSON content from the raw string
            try:
                # Look for the JSON block: '```json\n{...}\n```'
                json_start = sim_details_raw_string.find('```json\n')
                json_end = sim_details_raw_string.find('\n```', json_start + 8)
                if json_start != -1 and json_end != -1:
                    json_content = sim_details_raw_string[json_start + 8 : json_end]
                    sim_details_dict = json.loads(json_content)
                else:
                    metadata_status_message = "Warning: Could not parse simulation metadata. Unexpected format from manager."
            except json.JSONDecodeError:
                metadata_status_message = "Warning: Could not decode JSON from simulation metadata. Data might be corrupted."
            except Exception as e:
                metadata_status_message = f"Warning: An unexpected error occurred parsing metadata: {e}"

        # --- 2. Format the Metadata for Human Readability ---
        metadata_parts = []
        metadata_parts.append("--- Simulation Metadata ---")
        if metadata_status_message:
            metadata_parts.append(metadata_status_message)
        
        if sim_details_dict:
            metadata_parts.append(f"  Simulation ID: {sim_details_dict.get('simulation_ID', 'N/A')}")
            metadata_parts.append(f"  Name: {sim_details_dict.get('simulation_name', 'Unnamed Simulation')}")
            details_list = sim_details_dict.get('simulation_details', [])
            if details_list:
                metadata_parts.append("  Details:")
                for i, detail in enumerate(details_list):
                    metadata_parts.append(f"    {i+1}. {detail}")
            else:
                metadata_parts.append("  Details: No specific details recorded for this simulation run.")
        elif not metadata_status_message: # If no specific error, but no dict was parsed, indicate general unavailability
             metadata_parts.append(f"  No detailed metadata available for simulation ID '{self.current_simulation_ID}'.")
             metadata_parts.append("  This simulation might be new and not yet archived, or its ID is not set.")

        # --- 3. Format the Current Configuration for Human Readability ---
        config_parts = []
        config_parts.append("\n--- Current Simulation Configuration ---")
        config_parts.append(f"  Grid Size: {self.config.get('grid_size', ['N/A', 'N/A'])[0]}x{self.config.get('grid_size', ['N/A', 'N/A'])[1]}")
        config_parts.append(f"  Configured Max Ticks: {self.config.get('max_ticks', 'N/A')}")

        # Map internal type names to their constant IDs for display
        type_id_map = {
            "plant": self.PLANT,
            "herbivore": self.HERBIVORE,
            "carnivore": self.CARNIVORE
        }

        entity_config = self.config.get('entity_config', {})
        for entity_type_name, config_data in entity_config.items():
            type_id = type_id_map.get(entity_type_name, 'N/A')
            config_parts.append(f"\n (Type ID {type_id}) Settings:")
            for key, value in config_data.items():
                # Format key for better readability (e.g., "initial_count" -> "Initial Count")
                readable_key = key.replace('_', ' ').title()
                config_parts.append(f"    - {readable_key}: {value}")


        # --- 4. Get the ASCII Visualization (already human-readable) ---
        # The get_visualization() method already includes its own header and tick information.
        visuals = self.get_visualization()

        # --- 5. Combine all formatted parts into a final message ---
        message = "\n".join(metadata_parts) + "\n" + \
                  "\n".join(config_parts) + "\n" + \
                  f"\n--- ASCII Visualization (Current Tick: {self.current_tick}) ---\n" + \
                  visuals # get_visualization() string starts with "Tick X of Y\n"

        return message