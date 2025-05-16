import json
import random
import copy
from typing import List, Dict, Tuple, Any, Optional
import os
from datetime import datetime

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
    
    def __init__(self, config: Dict[str, Any] = None, archive=None):
        self.archive_path=archive
                # Create the archive directory if it doesn't exist
        os.makedirs(self.archive_path, exist_ok=True)
        
        # Create the archive file paths
        self.json_path = os.path.join(self.archive_path, f"current_simulation.json")
        self.txt_path = os.path.join(self.archive_path, f"current_simulation.txt")
        """Initialize the ALifeSimulation with optional configuration."""
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
            
        # Initialize simulation state
        self.current_tick = 0
        self.max_ticks = self.config["max_ticks"]
        self.grid_size = self.config["grid_size"]
        self.entities = []
        self.entity_id_counter = 0
        
        # History for time-scrubbing
        self.history = []
        
        # Initialize the simulation
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
        """Initialize the simulation with entities based on configuration."""
        # Clear existing state
        self.entities = []
        self.entity_id_counter = 0
        self.current_tick = 0
        self.history = []
        
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
        for _ in range(count):
            # Find an unoccupied position
            while True:
                pos = [random.randint(0, self.grid_size[0]-1), 
                       random.randint(0, self.grid_size[1]-1)]
                
                # Check if position is empty
                if not self._get_entity_at_position(pos):
                    break
            
            # Create the entity
            entity = {
                "id": f"E{self.entity_id_counter}",
                "type_id": type_id,
                "pos": pos,
                "state": copy.deepcopy(state)
            }
            
            self.entities.append(entity)
            self.entity_id_counter += 1
    
    def _get_entity_at_position(self, pos: List[int]) -> Optional[Dict]:
        """Get entity at a specific position if any."""
        for entity in self.entities:
            if entity["pos"] == pos and entity["state"]["status"] == self.ALIVE:
                return entity
        return None
    
    def _get_entities_by_type(self, type_id: int) -> List[Dict]:
        """Get all entities of a specific type."""
        return [e for e in self.entities if e["type_id"] == type_id and e["state"]["status"] == self.ALIVE]
    
    def _get_distance(self, pos1: List[int], pos2: List[int]) -> int:
        """Calculate Manhattan distance between two positions."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    def _get_adjacent_positions(self, pos: List[int], distance: int = 1) -> List[List[int]]:
        """Get all valid positions within a certain distance."""
        adjacent = []
        for dx in range(-distance, distance+1):
            for dy in range(-distance, distance+1):
                # Skip the current position
                if dx == 0 and dy == 0:
                    continue
                
                new_x = pos[0] + dx
                new_y = pos[1] + dy
                
                # Check bounds
                if 0 <= new_x < self.grid_size[0] and 0 <= new_y < self.grid_size[1]:
                    adjacent.append([new_x, new_y])
        
        return adjacent
    
    def _move_toward(self, entity: Dict, target_pos: List[int]) -> None:
        """Move entity one step toward target position."""
        current_pos = entity["pos"]
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]
        
        # Determine movement direction (selfplified)
        if abs(dx) > abs(dy):
            # Move horizontally
            new_x = current_pos[0] + (1 if dx > 0 else -1)
            new_pos = [new_x, current_pos[1]]
        else:
            # Move vertically
            new_y = current_pos[1] + (1 if dy > 0 else -1)
            new_pos = [current_pos[0], new_y]
        
        # Check bounds and occupancy
        if (0 <= new_pos[0] < self.grid_size[0] and 
            0 <= new_pos[1] < self.grid_size[1] and
            not self._get_entity_at_position(new_pos)):
            entity["pos"] = new_pos
    
    def _save_current_state(self) -> None:
        """Save the current state to history."""
        state = {
            "tick": self.current_tick,
            "entities": copy.deepcopy(self.entities),
            "grid_size": self.grid_size
        }
        self.history.append(state)
    
    def _process_plants(self) -> None:
        """Process plant behavior."""
        plants = self._get_entities_by_type(self.PLANT)
        
        # Plants try to grow to adjacent cells
        for plant in plants:
            # Increase energy
            plant_config = self.config["entity_config"]["plant"]
            plant["state"]["energy"] = min(
                plant["state"]["energy"] + 1, 
                plant_config["max_energy"]
            )
            
            # Try to spread to adjacent cells
            if random.random() < plant_config["growth_rate"]:
                adjacent = self._get_adjacent_positions(plant["pos"])
                random.shuffle(adjacent)
                
                for new_pos in adjacent:
                    if not self._get_entity_at_position(new_pos):
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
                        
                        self.entities.append(new_plant)
                        self.entity_id_counter += 1
                        break  # Only create one plant per tick
    
    def _process_herbivores(self) -> None:
        """Process herbivore behavior."""
        herbivores = self._get_entities_by_type(self.HERBIVORE)
        herbivore_config = self.config["entity_config"]["herbivore"]
        
        for herbivore in herbivores:
            # Decrease energy
            herbivore["state"]["energy"] -= herbivore_config["energy_consumption"]
            
            # Check if herbivore dies
            if herbivore["state"]["energy"] <= 0:
                herbivore["state"]["status"] = self.DEAD
                continue
            
            # Find and eat plants
            plants = self._get_entities_by_type(self.PLANT)
            plants_sorted = sorted(
                plants,
                key=lambda p: self._get_distance(herbivore["pos"], p["pos"])
            )
            
            if plants_sorted:
                closest_plant = plants_sorted[0]
                distance = self._get_distance(herbivore["pos"], closest_plant["pos"])
                
                if distance <= herbivore_config["movement_range"]:
                    # If adjacent, eat plant
                    if distance == 1:
                        herbivore["state"]["energy"] += self.config["interaction_rules"]["herbivore_eat_plant"]
                        closest_plant["state"]["status"] = self.DEAD
                    # Otherwise move toward plant
                    else:
                        self._move_toward(herbivore, closest_plant["pos"])
                else:
                    # Move randomly if no plant is in range
                    adjacent = self._get_adjacent_positions(herbivore["pos"])
                    valid_moves = [pos for pos in adjacent if not self._get_entity_at_position(pos)]
                    if valid_moves:
                        herbivore["pos"] = random.choice(valid_moves)
            
            # Reproduction
            if herbivore["state"]["energy"] >= herbivore_config["reproduction_threshold"]:
                adjacent = self._get_adjacent_positions(herbivore["pos"])
                valid_cells = [pos for pos in adjacent if not self._get_entity_at_position(pos)]
                
                if valid_cells:
                    # Create offspring
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
                    
                    # Deduct reproduction cost
                    herbivore["state"]["energy"] -= herbivore_config["reproduction_cost"]
    
    def _process_carnivores(self) -> None:
        """Process carnivore behavior."""
        carnivores = self._get_entities_by_type(self.CARNIVORE)
        carnivore_config = self.config["entity_config"]["carnivore"]
        
        for carnivore in carnivores:
            # Decrease energy
            carnivore["state"]["energy"] -= carnivore_config["energy_consumption"]
            
            # Check if carnivore dies
            if carnivore["state"]["energy"] <= 0:
                carnivore["state"]["status"] = self.DEAD
                continue
            
            # Find and hunt herbivores
            herbivores = self._get_entities_by_type(self.HERBIVORE)
            herbivores_sorted = sorted(
                herbivores,
                key=lambda h: self._get_distance(carnivore["pos"], h["pos"])
            )
            
            if herbivores_sorted:
                closest_herbivore = herbivores_sorted[0]
                distance = self._get_distance(carnivore["pos"], closest_herbivore["pos"])
                
                if distance <= carnivore_config["movement_range"]:
                    # If adjacent, eat herbivore
                    if distance == 1:
                        carnivore["state"]["energy"] += self.config["interaction_rules"]["carnivore_eat_herbivore"]
                        closest_herbivore["state"]["status"] = self.DEAD
                    # Otherwise move toward herbivore
                    else:
                        self._move_toward(carnivore, closest_herbivore["pos"])
                else:
                    # Move randomly if no herbivore is in range
                    adjacent = self._get_adjacent_positions(carnivore["pos"])
                    valid_moves = [pos for pos in adjacent if not self._get_entity_at_position(pos)]
                    if valid_moves:
                        carnivore["pos"] = random.choice(valid_moves)
            
            # Reproduction
            if carnivore["state"]["energy"] >= carnivore_config["reproduction_threshold"]:
                adjacent = self._get_adjacent_positions(carnivore["pos"])
                valid_cells = [pos for pos in adjacent if not self._get_entity_at_position(pos)]
                
                if valid_cells:
                    # Create offspring
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
                    
                    # Deduct reproduction cost
                    carnivore["state"]["energy"] -= carnivore_config["reproduction_cost"]
    
    def _update_ages(self) -> None:
        """Update ages of all living entities."""
        for entity in self.entities:
            if entity["state"]["status"] == self.ALIVE:
                entity["state"]["age"] += 1
    
    def step(self) -> bool:
        """
        Advance the simulation by one tick.
        Returns True if the simulation can continue, False if it has ended.
        """
        if self.current_tick >= self.max_ticks:
            return False
        
        # Process entities in order: plants, herbivores, carnivores
        self._process_plants()
        self._process_herbivores()
        self._process_carnivores()
        
        # Update ages
        self._update_ages()
        
        # Increment tick
        self.current_tick += 1
        
        # Save state
        self._save_current_state()
        
        return self.current_tick < self.max_ticks
    
    def run_simulation(self) -> None:
        """Run the entire simulation from current state to max_ticks."""
        while self.step():
            pass
    
    def reset(self) -> None:
        """Reset the simulation to initial state."""
        self._init_simulation()
    
    # AI  TOOLS

    def set_current_tick(self, tick:int) -> str:
        """
        Set the current tick of the simulation to the given argument, (int)
        """
        if tick >= len(self.history):
            return "Tried to set a tick larger than the total life-span of the simulation"
        else:
            self.current_tick= tick
            return f"Correctly set the new current tick to {tick} {self.observe()}"

    def observe(self) -> str:
        """
        Return a string representation of the current state of the simulation.
        This is one of the three tools available to the AI.
        """
        state = self.history[self.current_tick]
        
        # Add a progress indicator
        state_with_progress = copy.deepcopy(state)
        state_with_progress["progress"] = f"Tick {self.current_tick} of {self.max_ticks}"
        
        return json.dumps(state_with_progress, indent=2)
    
    def forward(self) -> str:
        """
        Move one tick forward in the simulation.
        This is one of the three tools available to the AI.
        """
        if self.current_tick < len(self.history) - 1:
            self.current_tick += 1

            return f"Moved forward to tick {self.current_tick } of {self.max_ticks}. {self.observe()}"
        else:
            return f"Already at the last tick ({self.current_tick } of {self.max_ticks})."
    
    def backward(self) -> str:
        """
        Move one tick backward in the simulation.
        This is one of the three tools available to the AI.
        """
        if self.current_tick > 0:
            self.current_tick -= 1
            return f"Moved backward to tick {self.current_tick} of {self.max_ticks}. {self.observe()}"
        else:
            return f"Already at the first tick (1 of {self.max_ticks})."
        

    
    def get_visualization(self) -> str:
        """
        Create a selfple ASCII visualization of the current state.
        This is a bonus tool to help visualize the simulation for debugging.
        """
        # Create an empty grid
        grid = [[' ' for _ in range(self.grid_size[0])] for _ in range(self.grid_size[1])]
        
        # Fill in entities
        state = self.history[self.current_tick]
        for entity in state["entities"]:
            if entity["state"]["status"] == self.ALIVE:
                x, y = entity["pos"]
                if entity["type_id"] == self.PLANT:
                    grid[y][x] = 'P'
                elif entity["type_id"] == self.HERBIVORE:
                    grid[y][x] = 'H'
                elif entity["type_id"] == self.CARNIVORE:
                    grid[y][x] = 'C'
        
        # Convert grid to string
        visualization = f"Tick {self.current_tick + 1} of {self.max_ticks}\n"
        visualization += '+' + '-' * self.grid_size[0] + '+\n'
        for row in grid:
            visualization += '|' + ''.join(row) + '|\n'
        visualization += '+' + '-' * self.grid_size[0] + '+\n'
        
        # Add entity counts
        plants = sum(1 for e in state["entities"] if e["type_id"] == self.PLANT and e["state"]["status"] == self.ALIVE)
        herbivores = sum(1 for e in state["entities"] if e["type_id"] == self.HERBIVORE and e["state"]["status"] == self.ALIVE)
        carnivores = sum(1 for e in state["entities"] if e["type_id"] == self.CARNIVORE and e["state"]["status"] == self.ALIVE)
        
        visualization += f"Plants (P): {plants}, Herbivores (H): {herbivores}, Carnivores (C): {carnivores}\n"
        
        return visualization


    def archive_simulation_run(self):
        """
        Archive a completed simulation run by saving:
        1. A JSON file with the complete simulation history
        2. A text file with the visualization of each tick and simulation metadata
        
        Args:
            self: ALifesimulation instance that has completed a run
            archive_dir: Directory to save the archives (created if it doesn't exist)
        
        Returns:
            dict: Information about the archived files
        """
        
        # Save the JSON history
        with open(self.json_path, 'w') as f:
            json.dump({
                "config": self.config,
                "history": self.history,
                "entity_id_counter": self.entity_id_counter
            }, f, indent=2)
        
        # Save the visualizations and metadata
        with open(self.txt_path, 'w') as f:
            # Write simulation metadata
            f.write("=" * 60 + "\n")
            f.write("A-LIFE simulation ARCHIVE\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            # Write configuration information
            f.write("CONFIGURATION\n")
            f.write("-" * 60 + "\n")
            f.write(f"Grid Size: {self.grid_size[0]} x {self.grid_size[1]}\n")
            f.write(f"Max Ticks: {self.max_ticks}\n\n")
            
            # Write entity type information
            f.write("ENTITY TYPES\n")
            f.write("-" * 60 + "\n")
            f.write(f"PLANT (Type ID: {self.PLANT}): Plants grow and spread to adjacent cells\n")
            f.write(f"  - Initial Count: {self.config['entity_config']['plant']['initial_count']}\n")
            f.write(f"  - Initial Energy: {self.config['entity_config']['plant']['initial_energy']}\n")
            f.write(f"  - Growth Rate: {self.config['entity_config']['plant']['growth_rate']}\n")
            f.write(f"  - Max Energy: {self.config['entity_config']['plant']['max_energy']}\n\n")
            
            f.write(f"HERBIVORE (Type ID: {self.HERBIVORE}): Herbivores move to and eat plants\n")
            f.write(f"  - Initial Count: {self.config['entity_config']['herbivore']['initial_count']}\n")
            f.write(f"  - Initial Energy: {self.config['entity_config']['herbivore']['initial_energy']}\n")
            f.write(f"  - Movement Range: {self.config['entity_config']['herbivore']['movement_range']}\n")
            f.write(f"  - Energy Consumption: {self.config['entity_config']['herbivore']['energy_consumption']}\n")
            f.write(f"  - Reproduction Threshold: {self.config['entity_config']['herbivore']['reproduction_threshold']}\n")
            f.write(f"  - Reproduction Cost: {self.config['entity_config']['herbivore']['reproduction_cost']}\n")
            f.write(f"  - Energy Gained from eating plants: {self.config['interaction_rules']['herbivore_eat_plant']}\n\n")
            
            f.write(f"CARNIVORE (Type ID: {self.CARNIVORE}): Carnivores move to and eat herbivores\n")
            f.write(f"  - Initial Count: {self.config['entity_config']['carnivore']['initial_count']}\n")
            f.write(f"  - Initial Energy: {self.config['entity_config']['carnivore']['initial_energy']}\n")
            f.write(f"  - Movement Range: {self.config['entity_config']['carnivore']['movement_range']}\n")
            f.write(f"  - Energy Consumption: {self.config['entity_config']['carnivore']['energy_consumption']}\n")
            f.write(f"  - Reproduction Threshold: {self.config['entity_config']['carnivore']['reproduction_threshold']}\n")
            f.write(f"  - Reproduction Cost: {self.config['entity_config']['carnivore']['reproduction_cost']}\n")
            f.write(f"  - Energy Gained from eating herbivores: {self.config['interaction_rules']['carnivore_eat_herbivore']}\n\n")
            
            f.write("simulation BEHAVIORS\n")
            f.write("-" * 60 + "\n")
            f.write("1. Plants passively grow and spread to adjacent empty cells based on growth rate\n")
            f.write("2. Herbivores move toward and consume plants, gaining energy\n")
            f.write("3. Carnivores move toward and consume herbivores, gaining energy\n")
            f.write("4. All entities consume energy each tick\n")
            f.write("5. Animals reproduce when energy threshold is reached\n")
            f.write("6. Entities die when energy reaches zero\n\n")
            
            # Write visualizations for each tick
            f.write("simulation VISUALIZATION\n")
            f.write("-" * 60 + "\n\n")
            
            # Store the current tick so we can restore it
            original_tick = self.current_tick
            
            # Loop through all ticks and write visualization
            for tick in range(len(self.history)):
                self.set_current_tick(tick)
                visualization = self.get_visualization()
                f.write(visualization)
                f.write("\n" + "-" * 40 + "\n\n")
            
            # Restore the original tick
            self.set_current_tick(original_tick)
            
            # Write summary statistics
            final_state = self.history[-1]
            plants_alive = sum(1 for e in final_state["entities"] if e["type_id"] == self.PLANT and e["state"]["status"] == self.ALIVE)
            herbivores_alive = sum(1 for e in final_state["entities"] if e["type_id"] == self.HERBIVORE and e["state"]["status"] == self.ALIVE)
            carnivores_alive = sum(1 for e in final_state["entities"] if e["type_id"] == self.CARNIVORE and e["state"]["status"] == self.ALIVE)
            
            f.write("\nFINAL STATISTICS\n")
            f.write("-" * 60 + "\n")
            f.write(f"Total Ticks: {len(self.history)}\n")
            f.write(f"Total Entities Generated: {self.entity_id_counter}\n")
            f.write(f"Plants Remaining: {plants_alive}\n")
            f.write(f"Herbivores Remaining: {herbivores_alive}\n")
            f.write(f"Carnivores Remaining: {carnivores_alive}\n")
        
        return {
            "json_file": self.json_path,
            "text_file": self.txt_path
        }


    def create_new_simulation(self):
        """
        create a new simulation on the current run-time
        probably we want to introduce a way to track and save previous runs?
        """


        with open(self.json_path, 'r') as f:
            data = json.load(f)
        
        # Create a new simulation with the archived config
        self = ALifeSimulation(data["config"], self.archive_path)
        
        self.run_simulation()
        
        # Set current tick to beginning
        self.current_tick = 0
        
        # Set max_ticks based on history length
        self.max_ticks = len(self.history) - 1

        self.archive_simulation_run()
        
        return "New simulation created."



# Example usage
if __name__ == "__main__":
    # Create a simulation with default settings
    self = ALifeSimulation()
    
    # Run the full simulation
    self.run_simulation()
    self.archive_simulation_run()
    
    # Reset to the beginning
    self.current_tick = 0
    print("Initial observation")
    print(self.observe())

  
    

    
    # # Print the visualization of the first tick
    # print(self.get_visualization())
    
    # # Move forward and observe
    # print(self.forward())
    # print(self.get_visualization())

    for i in range(3):
        print(self.forward())
        #print(self.observe())
        print(self.get_visualization())
    
    self.create_new_simulation()
    print("new observation")
    print(self.observe())


# Example of a custom configuration
example_custom_config = {
    "grid_size": [6, 6],
    "max_ticks": 25,
    "entity_config": {
        "plant": {
            "initial_count": 5,
            "growth_rate": 0.3
        },
        "herbivore": {
            "initial_count": 3,
            "movement_range": 2
        },
        "carnivore": {
            "initial_count": 2
        }
    },
    "interaction_rules": {
        "herbivore_eat_plant": 5
    }
}
