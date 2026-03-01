import json
import random
import copy
from typing import List, Dict, Tuple, Any, Optional
import os
from utils.loc_datetime import datetime
import time

# =============================================================================
# PUZZLE / REDACTION DESIGN NOTE
# =============================================================================
# This simulation models a 3-tier ecosystem (type 0 / type 1 / type 2).
# The semantic identities of these types — what they "are" in ecological terms —
# are the ANSWER to the puzzle posed to the observing AI.
#
# INVARIANT: No string returned by any _ALIFE-suffixed method, nor any tool
# parameter name or docstring, may contain the words: plant, herbivore, carnivore,
# or any synonym that reveals trophic role or predator/prey relationship.
#
# The AI sees only: integer type_ids, positions, energy values, and alive/dead status.
# From these abstract signals alone, it must infer the ecological structure.
#
# CHECKLIST — before adding or editing any AI-facing method, verify:
#   [ ] No entity semantic names in return strings
#   [ ] No entity semantic names in docstrings
#   [ ] No entity semantic names in parameter names
#   [ ] interaction_rules keys use type_N_consume_type_M format
# =============================================================================


class ALifeSimulation:
    """
    A configurable A-Life simulation with three entity types (0, 1, 2)
    on a grid-based environment that can be observed by an AI.
    The ecological roles of each type are intentionally undisclosed —
    they are the puzzle the AI is meant to solve through observation.
    """

    # Entity type IDs
    PLANT = 0
    HERBIVORE = 1
    CARNIVORE = 2

    # Status constants
    ALIVE = "alive"
    DEAD = "dead"


    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the ALifeSimulation with optional configuration."""
        self.latest_config_summary = ""
        self.current_simulation_ID=""

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
            # ----------------------------------------------------------------
            # REDACTED KEY NAMES: interaction_rules keys use abstract type
            # references (type_N_consume_type_M) rather than semantic names.
            # This prevents accidental leakage if config is ever serialized
            # or inspected by the AI.
            # ----------------------------------------------------------------
            "interaction_rules": {
                "type_1_consume_type_0": 4,   # energy gained by type 1 consuming type 0
                "type_2_consume_type_1": 8    # energy gained by type 2 consuming type 1
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
        for entity in self.entities:
            if entity["pos"] == pos and entity["state"]["status"] == self.ALIVE:
                return entity
        return None

    def _get_entities_by_type(self, type_id: int) -> List[Dict]:
        """Get all entities of a specific type (only ALIVE entities)."""
        return [e for e in self.entities if e["type_id"] == type_id and e["state"]["status"] == self.ALIVE]

    def _get_distance(self, pos1: List[int], pos2: List[int]) -> int:
        """Calculate Manhattan distance between two positions."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _get_adjacent_positions(self, pos: List[int], distance: int = 1) -> List[List[int]]:
        """Get all valid positions at a specific Manhattan distance."""
        adjacent = []
        max_dist = distance
        for dx in range(-max_dist, max_dist + 1):
            for dy in range(-max_dist, max_dist + 1):
                if abs(dx) + abs(dy) == distance:
                    new_x = pos[0] + dx
                    new_y = pos[1] + dy
                    if 0 <= new_x < self.grid_size[0] and 0 <= new_y < self.grid_size[1]:
                        adjacent.append([new_x, new_y])
        return adjacent
    
    def _cleanup_dead_entities(self) -> None:
        """
        Remove entities that have been dead for more than one tick.
        Uses the death_tick counter to determine which dead entities to remove.
        Called at the end of each tick's processing.
        """
        self.entities = [entity for entity in self.entities if 
                        entity["state"]["status"] == self.ALIVE or 
                        (entity["state"]["status"] == self.DEAD and 
                        entity["state"].get("death_tick", 0) <= 1)]

    def _move_toward(self, entity: Dict, target_pos: List[int]) -> None:
        """Move entity one step toward target position if possible (unoccupied)."""
        current_pos = entity["pos"]
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]

        move_options = []
        if dx != 0:
            move_options.append([current_pos[0] + (1 if dx > 0 else -1), current_pos[1]])
        if dy != 0:
            move_options.append([current_pos[0], current_pos[1] + (1 if dy > 0 else -1)])

        if not move_options:
            return

        random.shuffle(move_options)
        best_move = None
        current_dist = self._get_distance(current_pos, target_pos)

        for next_pos in move_options:
            if not (0 <= next_pos[0] < self.grid_size[0] and 0 <= next_pos[1] < self.grid_size[1]):
                continue
            if self._get_entity_at_position(next_pos):
                continue
            next_dist = self._get_distance(next_pos, target_pos)
            if next_dist < current_dist:
                 best_move = next_pos
                 break
            elif best_move is None:
                 best_move = next_pos

        if best_move:
            entity["pos"] = best_move


    def _save_current_state(self) -> None:
        """Save the current state to history."""
        state = {
            "tick": self.current_tick,
            "entities": copy.deepcopy(self.entities),
            "grid_size": self.grid_size
        }
        self.history.append(state)

    def _process_plants(self) -> None:
        """Process type 0 entity behavior."""
        plants = self._get_entities_by_type(self.PLANT)

        for plant in plants:
            plant_config = self.config["entity_config"]["plant"]
            plant["state"]["energy"] = min(
                plant["state"]["energy"] + 1,
                plant_config["max_energy"]
            )

            if random.random() < plant_config["growth_rate"]:
                adjacent = self._get_adjacent_positions(plant["pos"], distance=1)
                random.shuffle(adjacent)

                for new_pos in adjacent:
                    if not self._get_entity_at_position(new_pos):
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
                        self.entities.append(new_plant)
                        self.entity_id_counter += 1
                        break

    def _process_herbivores(self) -> None:
        """Process type 1 entity behavior."""
        herbivores = self._get_entities_by_type(self.HERBIVORE)
        herbivore_config = self.config["entity_config"]["herbivore"]
        interaction_rules = self.config["interaction_rules"]

        random.shuffle(herbivores)

        for herbivore in herbivores:
            herbivore["state"]["energy"] -= herbivore_config["energy_consumption"]

            if herbivore["state"]["energy"] <= 0:
                herbivore["state"]["status"] = self.DEAD
                herbivore["state"]["death_tick"] = 0
                continue

            plants = self._get_entities_by_type(self.PLANT)
            closest_plant = None
            min_dist = float('inf')

            for plant in plants:
                dist = self._get_distance(herbivore["pos"], plant["pos"])
                if dist < min_dist and dist <= herbivore_config["movement_range"]:
                    min_dist = dist
                    closest_plant = plant

            if closest_plant:
                if min_dist == 1:
                    if closest_plant["state"]["status"] == self.ALIVE:
                        # Use redacted interaction rule key
                        herbivore["state"]["energy"] += interaction_rules["type_1_consume_type_0"]
                        closest_plant["state"]["status"] = self.DEAD
                        closest_plant["state"]["death_tick"] = 0
                elif min_dist > 1:
                    self._move_toward(herbivore, closest_plant["pos"])
            else:
                adjacent = self._get_adjacent_positions(herbivore["pos"], distance=1)
                valid_moves = [pos for pos in adjacent if not self._get_entity_at_position(pos)]
                if valid_moves:
                    herbivore["pos"] = random.choice(valid_moves)

            if herbivore["state"]["status"] == self.ALIVE and herbivore["state"]["energy"] >= herbivore_config["reproduction_threshold"]:
                adjacent = self._get_adjacent_positions(herbivore["pos"], distance=1)
                valid_cells = [pos for pos in adjacent if not self._get_entity_at_position(pos)]

                if valid_cells:
                    offspring_pos = random.choice(valid_cells)
                    offspring = {
                        "id": f"E{self.entity_id_counter}",
                        "type_id": self.HERBIVORE,
                        "pos": offspring_pos,
                        "state": {
                            "energy": herbivore_config["initial_energy"],
                            "age": 0,
                            "status": self.ALIVE
                        }
                    }
                    self.entities.append(offspring)
                    self.entity_id_counter += 1
                    herbivore["state"]["energy"] -= herbivore_config["reproduction_cost"]


    def _process_carnivores(self) -> None:
        """Process type 2 entity behavior."""
        carnivores = self._get_entities_by_type(self.CARNIVORE)
        carnivore_config = self.config["entity_config"]["carnivore"]
        interaction_rules = self.config["interaction_rules"]

        random.shuffle(carnivores)

        for carnivore in carnivores:
            carnivore["state"]["energy"] -= carnivore_config["energy_consumption"]

            if carnivore["state"]["energy"] <= 0:
                carnivore["state"]["status"] = self.DEAD
                carnivore["state"]["death_tick"] = 0
                continue

            herbivores = self._get_entities_by_type(self.HERBIVORE)
            closest_herbivore = None
            min_dist = float('inf')

            for herbivore in herbivores:
                dist = self._get_distance(carnivore["pos"], herbivore["pos"])
                if dist < min_dist and dist <= carnivore_config["movement_range"]:
                    min_dist = dist
                    closest_herbivore = herbivore

            if closest_herbivore:
                if min_dist == 1:
                    if closest_herbivore["state"]["status"] == self.ALIVE:
                        # Use redacted interaction rule key
                        carnivore["state"]["energy"] += interaction_rules["type_2_consume_type_1"]
                        closest_herbivore["state"]["status"] = self.DEAD
                        closest_herbivore["state"]["death_tick"] = 0
                elif min_dist > 1:
                    self._move_toward(carnivore, closest_herbivore["pos"])
            else:
                adjacent = self._get_adjacent_positions(carnivore["pos"], distance=1)
                valid_moves = [pos for pos in adjacent if not self._get_entity_at_position(pos)]
                if valid_moves:
                    carnivore["pos"] = random.choice(valid_moves)

            if carnivore["state"]["status"] == self.ALIVE and carnivore["state"]["energy"] >= carnivore_config["reproduction_threshold"]:
                adjacent = self._get_adjacent_positions(carnivore["pos"], distance=1)
                valid_cells = [pos for pos in adjacent if not self._get_entity_at_position(pos)]

                if valid_cells:
                    offspring_pos = random.choice(valid_cells)
                    offspring = {
                        "id": f"E{self.entity_id_counter}",
                        "type_id": self.CARNIVORE,
                        "pos": offspring_pos,
                        "state": {
                            "energy": carnivore_config["initial_energy"],
                            "age": 0,
                            "status": self.ALIVE
                        }
                    }
                    self.entities.append(offspring)
                    self.entity_id_counter += 1
                    carnivore["state"]["energy"] -= carnivore_config["reproduction_cost"]


    def _update_ages(self) -> None:
        """Update ages of all living entities and death_tick counters of dead entities."""
        for entity in self.entities:
            if entity["state"]["status"] == self.ALIVE:
                entity["state"]["age"] += 1
            elif entity["state"]["status"] == self.DEAD:
                if "death_tick" in entity["state"]:
                    entity["state"]["death_tick"] += 1


    def step(self) -> bool:
        """
        Advance the simulation by one tick.
        Processes entity actions and saves the resulting state.
        Returns True if the simulation can continue (hasn't reached max_ticks), False otherwise.
        """
        if self.current_tick >= self.max_ticks:
             return False

        if self.current_tick < len(self.history):
             self.entities = copy.deepcopy(self.history[self.current_tick]["entities"])
             self.grid_size = self.history[self.current_tick]["grid_size"]
        elif self.current_tick == len(self.history):
             pass
        else:
             print(f"Error: Cannot step from tick {self.current_tick}. History is only {len(self.history)} ticks long.")
             return False

        self._process_plants()
        self._process_herbivores()
        self._process_carnivores()

        self._update_ages()
        self._cleanup_dead_entities()
        self.current_tick += 1

        if self.current_tick <= self.max_ticks:
             self._save_current_state()

        return self.current_tick <= self.max_ticks


    def run_simulation(self, new_run: bool = False) -> None:
        """
        Run the entire simulation from current state to max_ticks.
        """
        if new_run:
            print("Starting a brand new simulation run...")
            random.seed(None)
            self._init_simulation()
            self.max_ticks = self.config.get("max_ticks", 20)

        print(f"Running simulation from tick {self.current_tick} up to tick {self.max_ticks} (inclusive)...")

        initial_tick = self.current_tick
        ticks_ran = 0
        while self.step():
             ticks_ran += 1
             if ticks_ran > self.max_ticks * 2 and self.current_tick > self.max_ticks:
                  print("Warning: Simulation running unexpectedly long. Stopping.")
                  break

        print(f"Simulation finished. Ran {ticks_ran} steps starting from tick {initial_tick}. Current tick is {self.current_tick}.")

    def reset(self) -> None:
        """Reset the simulation instance to its initial state based on config."""
        print("Resetting simulation state based on current configuration...")
        self._init_simulation()

    # =========================================================================
    # AI-FACING TOOLS
    # All methods below are callable by the AI agent.
    # REDACTION INVARIANT: none of these may reveal the semantic identity
    # of entity types. Only type_id integers (0, 1, 2) are exposed.
    # =========================================================================

    def set_current_tick_ALIFE(self, tick: int) -> str:
        """
        Set the current tick to the specified value and load that historical state.
        Allows the AI to navigate to any point in the simulation history.
        """
        if not self.history:
             return "Error: No simulation history available to set the tick."

        max_valid_tick = len(self.history) - 1

        if not isinstance(tick, int) or tick < 0:
             return f"Error: Invalid tick value '{tick}'. Must be a non-negative integer."

        if tick > max_valid_tick:
            return f"Error: Tried to set tick to {tick}, which is larger than the last available tick ({max_valid_tick}) in the current history."
        else:
            self.current_tick = tick
            try:
                state_at_tick = self.history[self.current_tick]
                self.entities = copy.deepcopy(state_at_tick["entities"])
                self.grid_size = state_at_tick["grid_size"]
            except IndexError:
                 return f"Error: Failed to load state for tick {tick}. History length is {len(self.history)}."

            return f"Successfully set the current tick to {tick} of {max_valid_tick}."
        
    def observe_ALIFE(self) -> str:
        """
        Return a structured JSON representation of the current simulation state.
        Includes: tick number, grid size, and a list of entities with their id,
        type_id (integer: 0, 1, or 2), position, energy, and status.

        NOTE — PUZZLE CONTRACT: Semantic entity identity is intentionally withheld.
        The AI observes only abstract type_ids and behavioral signals.
        Inferring what each type represents is the puzzle.
        """
        if not self.history:
             if self.current_tick == 0:
                  current_state_data = {
                      "tick": self.current_tick,
                      "max_ticks": self.max_ticks,
                      "grid_size": self.grid_size,
                      "entities": [],
                      "message": "Simulation initialized but no history recorded yet."
                  }
                  return json.dumps(current_state_data)
             else:
                  return json.dumps({"error": f"Observation Error: Simulation history is empty or corrupt at tick {self.current_tick}."})

        max_historical_tick = len(self.history) - 1
        if self.current_tick < 0 or self.current_tick > max_historical_tick:
             return json.dumps({"error": f"Observation Error: Current tick {self.current_tick} is out of bounds for available history (0 to {max_historical_tick})."})

        state_data_from_history = self.history[self.current_tick]
        tick_num = state_data_from_history.get("tick", self.current_tick)
        grid_size = state_data_from_history.get("grid_size", self.grid_size)
        raw_entities = state_data_from_history.get("entities", [])

        filtered_entities = []
        for entity in raw_entities:
            filtered_entity = {
                "id": entity.get("id", "N/A"),
                "type_id": entity.get("type_id", -1),
                "pos": entity.get("pos", [None, None]),
                "energy": entity.get("state", {}).get("energy", 0),
                "status": entity.get("state", {}).get("status", "unknown"),
            }
            filtered_entities.append(filtered_entity)

        observed_state = {
            "sim_ID": self.current_simulation_ID,
            "tick": tick_num,
            "configured_max_ticks": self.max_ticks,
            "last_history_tick": max_historical_tick,
            "grid_size": grid_size,
            "entities": filtered_entities
        }

        return json.dumps(observed_state)
            
    def forward_ALIFE(self) -> str:
        """
        Move one tick forward in the simulation history and return the new state as JSON.
        """
        if not self.history:
             return "Simulation is not initialized or has no history to move forward."

        max_valid_tick = len(self.history) - 1

        if self.current_tick < max_valid_tick:
            self.current_tick += 1
            self.set_current_tick_ALIFE(self.current_tick)
            return f"Moved forward to tick {self.current_tick} of {max_valid_tick}. {self.observe_ALIFE()}"
        else:
            return f"Already at the last tick ({self.current_tick} of {max_valid_tick}). Cannot move forward."

    def backward_ALIFE(self) -> str:
        """
        Move one tick backward in the simulation history and return the new state as JSON.
        """
        if not self.history:
             return "Simulation is not initialized or has no history to move backward."

        max_valid_tick = len(self.history) - 1

        if self.current_tick > 0:
            self.current_tick -= 1
            self.set_current_tick_ALIFE(self.current_tick)
            return f"Moved backward to tick {self.current_tick} of {max_valid_tick}. {self.observe_ALIFE()}"
        else:
            return f"Already at the first tick (0 of {max_valid_tick}). Cannot move backward."


    def get_visualization(self) -> str:
        """
        Create a simple ASCII visualization of the current state.
        Uses type_id integers mapped to their single-digit characters (0, 1, 2).
        """
        if not self.history or self.current_tick >= len(self.history):
             if not self.history:
                 return "Visualization Error: Simulation not initialized or has no history."
             else:
                 return f"Visualization Error: Current tick {self.current_tick} out of history bounds (0 to {len(self.history)-1})."

        state = self.history[self.current_tick]
        grid_size = state.get("grid_size", [5, 5])

        grid = [[' ' for _ in range(grid_size[0])] for _ in range(grid_size[1])]

        type_map = {
            self.PLANT: '0',
            self.HERBIVORE: '1',
            self.CARNIVORE: '2'
        }

        type_0_alive = 0
        type_1_alive = 0
        type_2_alive = 0

        for entity in state["entities"]:
            if entity["state"].get("status") == self.ALIVE:
                pos = entity.get("pos")
                type_id = entity.get("type_id")

                if pos and type_id is not None:
                    x, y = pos
                    if 0 <= x < grid_size[0] and 0 <= y < grid_size[1]:
                        grid[y][x] = type_map.get(type_id, '?')

                        if type_id == self.PLANT:
                            type_0_alive += 1
                        elif type_id == self.HERBIVORE:
                            type_1_alive += 1
                        elif type_id == self.CARNIVORE:
                            type_2_alive += 1

        visualization = f"Tick {self.current_tick} of {len(self.history) - 1}\n"
        visualization += '+' + '-' * grid_size[0] + '+\n'
        for row in grid:
            visualization += '|' + ''.join(row) + '|\n'
        visualization += '+' + '-' * grid_size[0] + '+\n'
        visualization += f"Alive counts: Type 0: {type_0_alive}, Type 1: {type_1_alive}, Type 2: {type_2_alive}\n"

        return visualization


    def archive_simulation_run(self, simulation_id: str) -> dict:
        """Returns data for archiving."""
        if not self.history:
             return {"error": "No simulation history to archive."}

        run_data = {
            "simulation_ID": simulation_id,
            "config": self.config,
            "history": self.history,
            "final_entity_id_counter": self.entity_id_counter
        }

        txt_content = []
        txt_content.append("=" * 60)
        txt_content.append("A-LIFE simulation ARCHIVE")
        txt_content.append(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        txt_content.append(f"Simulation ID: {simulation_id}")
        txt_content.append("=" * 60 + "\n")

        txt_content.append("CONFIGURATION")
        txt_content.append("-" * 60)
        txt_content.append(f"Grid Size: {self.grid_size[0]} x {self.grid_size[1]}")
        txt_content.append(f"Configured Max Ticks: {self.config.get('max_ticks', 'N/A')}\n")

        txt_content.append("simulation VISUALIZATION TIMELINE")
        txt_content.append("-" * 60 + "\n")

        original_tick = self.current_tick
        for tick in range(len(self.history)):
            self.set_current_tick_ALIFE(tick)
            txt_content.append(self.get_visualization())
            txt_content.append("-" * 40 + "\n")
        self.set_current_tick_ALIFE(original_tick)

        if self.history:
             final_state = self.history[-1]
             type_0_alive = sum(1 for e in final_state.get("entities", []) if e.get("type_id") == self.PLANT and e.get("state", {}).get("status") == self.ALIVE)
             type_1_alive = sum(1 for e in final_state.get("entities", []) if e.get("type_id") == self.HERBIVORE and e.get("state", {}).get("status") == self.ALIVE)
             type_2_alive = sum(1 for e in final_state.get("entities", []) if e.get("type_id") == self.CARNIVORE and e.get("state", {}).get("status") == self.ALIVE)

             txt_content.append("\nFINAL STATISTICS")
             txt_content.append("-" * 60)
             txt_content.append(f"Total Ticks Simulated: {len(self.history) - 1}")
             txt_content.append(f"Total Entities Generated: {self.entity_id_counter}")
             txt_content.append(f"Type 0 Remaining: {type_0_alive}")
             txt_content.append(f"Type 1 Remaining: {type_1_alive}")
             txt_content.append(f"Type 2 Remaining: {type_2_alive}")

        return {
            "json_data": run_data,
            "txt_data": "\n".join(txt_content)
        }


    def load_simulation_data(self, archived_data: dict, simulation_id: str, tick: int = 0) -> str:
        """Loads archived data into the simulation instance."""
        try:
            self.config = archived_data["config"]
            self.history = archived_data["history"]
            self.entity_id_counter = archived_data.get("final_entity_id_counter", 0)
            self.grid_size = self.config.get("grid_size", [5, 5])
            self.max_ticks = len(self.history) - 1
            self.current_simulation_ID = simulation_id

            if self.history:
                 self.current_tick = tick
                 self.set_current_tick_ALIFE(self.current_tick)

            return f"Successfully loaded simulation with ID '{simulation_id}'. Current tick is {self.current_tick}."
        except Exception as e:
            return f"Error loading simulation data: {e}"

    def create_new_simulation(self, grid_size=None, max_ticks=None, type_0_init_count=None, type_1_init_count=None, type_2_init_count=None):
        """
        Configures and runs a new simulation with the given parameters.
        Does NOT handle archiving or manager updates.
        """
        settings_grid_size_list = list(self.config.get("grid_size", [5, 5]))
        settings_max_ticks = self.config.get("max_ticks", 20)
        settings_type_0_init_count = self.config.get("entity_config", {}).get("plant", {}).get("initial_count", 3)
        settings_type_1_init_count = self.config.get("entity_config", {}).get("herbivore", {}).get("initial_count", 2)
        settings_type_2_init_count = self.config.get("entity_config", {}).get("carnivore", {}).get("initial_count", 1)

        if grid_size is not None:
            if isinstance(grid_size, str) and "," in grid_size:
                try:
                    grid_size_parts = [int(x) for x in grid_size.split(",")]
                    if len(grid_size_parts) == 2 and grid_size_parts[0] >= 0 and grid_size_parts[1] >= 0:
                        settings_grid_size_list = grid_size_parts
                except: pass

        if max_ticks is not None:
            try:
                max_ticks_int = int(max_ticks)
                settings_max_ticks = max(1, min(30, max_ticks_int))
            except: pass

        if type_0_init_count is not None:
            try: settings_type_0_init_count = max(0, int(type_0_init_count))
            except: pass

        if type_1_init_count is not None:
            try: settings_type_1_init_count = max(0, int(type_1_init_count))
            except: pass

        if type_2_init_count is not None:
            try: settings_type_2_init_count = max(0, int(type_2_init_count))
            except: pass

        # Clamp grid size
        settings_grid_size_list[0] = min(5, settings_grid_size_list[0])
        settings_grid_size_list[1] = min(5, settings_grid_size_list[1])

        area = settings_grid_size_list[0] * settings_grid_size_list[1]
        max_total_entities = int(area * 0.6)
        current_total = settings_type_0_init_count + settings_type_1_init_count + settings_type_2_init_count

        if current_total > max_total_entities and current_total > 0:
            scale_factor = max_total_entities / current_total
            settings_type_0_init_count = int(settings_type_0_init_count * scale_factor)
            settings_type_1_init_count = int(settings_type_1_init_count * scale_factor)
            settings_type_2_init_count = int(settings_type_2_init_count * scale_factor)

        ai_config = {
            "grid_size": settings_grid_size_list,
            "max_ticks": settings_max_ticks,
            "entity_config": {
                "plant": {"initial_count": settings_type_0_init_count, "initial_energy": 5, "growth_rate": 0.2, "max_energy": 10},
                "herbivore": {"initial_count": settings_type_1_init_count, "initial_energy": 10, "movement_range": 1, "energy_consumption": 1, "reproduction_threshold": 15, "reproduction_cost": 5},
                "carnivore": {"initial_count": settings_type_2_init_count, "initial_energy": 12, "movement_range": 2, "energy_consumption": 2, "reproduction_threshold": 20, "reproduction_cost": 8}
            }
        }

        self._deep_update(self.config, ai_config)
        self._init_simulation()
        self.run_simulation(new_run=True)
        self.current_tick = 0
        self.set_current_tick_ALIFE(0)

        # -----------------------------------------------------------------------
        # REDACTED RETURN: deliberately omits ai_config dict to avoid leaking
        # semantic entity names ("plant", "herbivore", "carnivore") to the AI.
        # Only abstract type counts and grid parameters are surfaced.
        # -----------------------------------------------------------------------
        return (
            f"Simulation run completed. Ready to view from tick 0. "
            f"Grid: {settings_grid_size_list}, Max ticks: {settings_max_ticks}, "
            f"Initial counts — "
            f"Type 0: {settings_type_0_init_count}, "
            f"Type 1: {settings_type_1_init_count}, "
            f"Type 2: {settings_type_2_init_count}."
        )