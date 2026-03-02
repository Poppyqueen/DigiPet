
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager # just for typing

import json
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

# Notes:
# Most of this works correctly, what is needed is adjusting the rewards settings
# The rewards are too high.

# Secondly, the LLM is bruteforcing the maze. Maybe add a stats reduction on each move, and higher if it goes into a wall. 
# Maybe some other solutions to prevent this bruteforcing behavior.

# Another update, we could add a "turn on" system for the tool, 
# While a new system could be designed, we could do it this way:

# Create two "item types" for the maze tool "maze-off" "maze-on", add a toggle to change the item type. 
# Each different type allows changing the tools tied to the item, so, while off it could have only the 
# turn on toggle, and while on it could have the maze tools alongside the turn off toggle.

# While a fun idea, we might want to figure out how to implement that concept in the items manager and releveant parts of the codebase so we can toggle that behavior with a key in the item blueprint.
# This would allow us to make any item a toggleable item.


BASE_REWARD = 20.0
MAZE_SIZE_MULTIPLIER = 0.4
STEPS_TAKEN_PENALTY_MULTIPLIER = 0.05 # Renamed for clarity
# --- New Reward Constants ---
PENALTY_THRESHOLD_BUFFER = 2.5  # Penalty starts after steps > (Optimal Steps * 1.2)
EFFICIENCY_BONUS_THRESHOLD = 1.0  # Bonus for steps <= (Optimal Steps * 1.0)
EFFICIENCY_BONUS_MULTIPLIER = 1.4 # The reward is multiplied by 1.5 if optimal/near-optimal
@dataclass
class Observation:
    """What the agent receives from the environment tool"""
    current_position: str
    coordinates: Dict[str, int]
    available_moves: List[Dict[str, str]]
    blocked_directions: List[str]
    is_goal: bool


@dataclass
class MoveResult:
    """Result of attempting a move"""
    success: bool
    message: str
    new_position: Optional[str] = None


class MazeEnvironment:
    """
    A maze environment represented as a graph structure.
    Tools provide ONLY immediate observations and move validation.
    """
    
    def __init__(self, state_manager: InventoryHouseManager, signal):
        self.width = 0
        self.height = 0
        self.nodes = {}
        self.start = ""
        self.goal = ""
        self.agent_position = ""
        self.maze_active = False
        self.state_manager = state_manager
        self._signal_callback = signal
        self.steps_taken = 0
    
    
    def _send_signal(self, signal_data):
        """Helper method to send signals using the registered callback."""
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from MazeEnvironment: {e}")

    def _generate_maze(self, width: int, height: int, seed: Optional[int] = None):
        """Generate maze using recursive backtracking with optional seed"""
        if seed is not None:
            random.seed(seed)
        
        self.width = width
        self.height = height
        self.nodes = {}
        self.start = "0,0"
        self.goal = f"{width-1},{height-1}"
        
        # Initialize all cells as isolated nodes
        for y in range(self.height):
            for x in range(self.width):
                self.nodes[f"{x},{y}"] = {"connections": [], "type": "empty"}
        
        # Carve paths using recursive backtracking
        visited = set()
        stack = []
        current = self.start
        
        visited.add(current)
        stack.append(current)
        
        while stack:
            current = stack[-1]
            neighbors = self._get_unvisited_neighbors(current, visited)
            
            if neighbors:
                next_pos, direction = random.choice(neighbors)
                
                # Create bidirectional connection
                self.nodes[current]["connections"].append({
                    "to": next_pos,
                    "direction": direction
                })
                
                opposite = {"NORTH": "SOUTH", "SOUTH": "NORTH", 
                           "EAST": "WEST", "WEST": "EAST"}
                self.nodes[next_pos]["connections"].append({
                    "to": current,
                    "direction": opposite[direction]
                })
                
                visited.add(next_pos)
                stack.append(next_pos)
            else:
                stack.pop()
        
        # Reset random seed after generation
        self.steps_taken = 0 # RESET STEP COUNTER
        random.seed()
    
    def _get_unvisited_neighbors(self, pos: str, visited: set) -> List[Tuple[str, str]]:
        """Get neighboring positions that haven't been visited"""
        x, y = map(int, pos.split(','))
        neighbors = []
        
        if x > 0:
            neighbors.append((f"{x-1},{y}", "WEST"))
        if x < self.width - 1:
            neighbors.append((f"{x+1},{y}", "EAST"))
        if y > 0:
            neighbors.append((f"{x},{y-1}", "NORTH"))
        if y < self.height - 1:
            neighbors.append((f"{x},{y+1}", "SOUTH"))
        
        return [(n, d) for n, d in neighbors if n not in visited]

    def _calculate_optimal_steps(self) -> int:
        """
        Calculates the minimum number of steps from start to goal using BFS.
        """
        if not self.maze_active or not self.start or not self.goal:
            return 0

        # Queue for BFS: (position, distance)
        queue = [(self.start, 0)]
        visited = {self.start}

        while queue:
            current_pos, distance = queue.pop(0)

            if current_pos == self.goal:
                return distance

            # Check all available connections from the current node
            node = self.nodes.get(current_pos, {})
            for connection in node.get("connections", []):
                next_pos = connection["to"]
                if next_pos not in visited:
                    visited.add(next_pos)
                    queue.append((next_pos, distance + 1))
        
        # Should not be reached in a properly generated maze, but as a safeguard
        return 0

    def calculate_reward(self) -> float:
        # The logic will be based on a base reward, an a multiplier for the size of the maze and a multiplier for the number of steps taken to reach the goal both penalties or rewards.
        
        # 1. Determine Optimal Steps
        optimal_steps = self._calculate_optimal_steps()
        
        # 2. Calculate Base Reward + Size Bonus
        maze_size = self.width * self.height 
        size_bonus = maze_size * MAZE_SIZE_MULTIPLIER
        base_amount = BASE_REWARD + size_bonus
        
        final_reward = base_amount

        # 3. Apply Steps-Based Adjustments (Penalty or Bonus)
        
        # --- Penalty Check ---
        penalty_threshold = optimal_steps * PENALTY_THRESHOLD_BUFFER
        
        if self.steps_taken > penalty_threshold:
            # Only penalize for steps taken *beyond* the allowed buffer
            excess_steps = self.steps_taken - penalty_threshold
            steps_penalty = excess_steps * STEPS_TAKEN_PENALTY_MULTIPLIER
            final_reward -= steps_penalty
            
            # Message for demonstration (optional)
            print(f"DEBUG: Penalized! Excess steps: {excess_steps:.1f}")

        # --- Efficiency Bonus Check ---
        bonus_threshold = optimal_steps * EFFICIENCY_BONUS_THRESHOLD # e.g., steps <= optimal
        
        if self.steps_taken <= bonus_threshold and self.steps_taken > 0:
            # Apply a multiplier for optimal or near-optimal solutions
            final_reward *= EFFICIENCY_BONUS_MULTIPLIER
            
            # Message for demonstration (optional)
            print("DEBUG: Efficiency Bonus Applied!")


        # 4. Final Sanity Check
        # Use max(0.0, ...) to guarantee a non-negative monetary value
        return max(0.0, final_reward)
    
    # ========== AGENT TOOLS ==========
    
    def create_maze(self, width: int = 8, height: int = 8, seed: Optional[int] = None) -> Dict:
        """
        TOOL: create_maze
        Creates a new randomly generated maze and resets agent to start position.
        
        Args:
            width: Width of the maze (default: 8)
            height: Height of the maze (default: 8)
            seed: Optional seed for reproducible mazes (default: None = random)
        
        Returns:
            Confirmation with maze dimensions and starting position
        """
        max_squares = 100
        if width * height > max_squares:
            return {"status": "maze_creation_failed", "message": f"Maze size exceeds maximum total allowed squares ({max_squares})."}
        
        self._generate_maze(width, height, seed)
        self.agent_position = self.start
        self.maze_active = True
        
        return {
            "status": "maze_created",
            "dimensions": {"width": width, "height": height},
            "start_position": self.start,
            "goal_position": self.goal,
            "message": f"New {width}x{height} maze created. Positioned at start!"
        }
    
    def observe_environment(self) -> Observation:
        """
        TOOL: observe_environment
        Returns ONLY what the agent can observe from their current position.
        No memory, no history, no hints.
        
        Returns:
            Current observation including position, available moves, and blocked directions
        """
        if not self.maze_active:
            raise RuntimeError("No active maze. Use create_maze tool first.")
        
        node = self.nodes[self.agent_position]
        x, y = map(int, self.agent_position.split(','))
        
        # Check all four cardinal directions
        all_directions = ["NORTH", "SOUTH", "EAST", "WEST"]
        available_moves = []
        blocked_directions = []
        
        for direction in all_directions:
            connection = next((c for c in node["connections"] 
                             if c["direction"] == direction), None)
            if connection:
                available_moves.append({
                    "direction": direction,
                    "destination": connection["to"]
                })
            else:
                blocked_directions.append(direction)

        
        return Observation(
            current_position=self.agent_position,
            coordinates={"x": x, "y": y},
            available_moves=available_moves,
            blocked_directions=blocked_directions,
            is_goal=(self.agent_position == self.goal)
        )
    
    def move(self, direction: str) -> MoveResult:
        """
        TOOL: move
        Attempts to move the agent in the specified direction.
        Validates the move before executing.
        
        Args:
            direction: One of "NORTH", "SOUTH", "EAST", "WEST"
        
        Returns:
            MoveResult with success status and new position if valid
        """
        if not self.maze_active:
            return MoveResult(
                success=False,
                message="No active maze. Use create_maze tool first."
            )
        
        direction = direction.upper()
        valid_directions = ["NORTH", "SOUTH", "EAST", "WEST"]
        
        if direction not in valid_directions:
            return MoveResult(
                success=False,
                message=f"Invalid direction '{direction}'. Must be one of: {', '.join(valid_directions)}"
            )
        
        # Check if move is valid
        node = self.nodes[self.agent_position]
        connection = next((c for c in node["connections"] 
                          if c["direction"] == direction), None)
        
        if connection is None:
            return MoveResult(
                success=False,
                message=f"Cannot move {direction} - blocked by wall"
            )
        
        # Execute move
        old_position = self.agent_position
        self.agent_position = connection["to"]
        self.steps_taken += 1
        
        reward_message=""
        # When we introduce our state manager, we can add currency if we are in the goal position
        if self.agent_position == self.goal:
            # self._send_signal({
            #     "type": "goal_reached",
            #     "message": "Goal reached!"
            # })
            self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/trumpet.png", "popup_type": 2})
            reward = self.calculate_reward()
            reward_result = self.state_manager.adjust_currency(reward)
            reset_width = random.randint(3, 10)
            reset_height = random.randint(3, 10)
            reward_message = f"Congratulations! You made it to the goal! You earned {reward} currency!... Current total: {reward_result.currency}. Resetting and randomizing maze with values {reset_width}x{reset_height}..."
            self._generate_maze(reset_width, reset_height)
            self.agent_position = self.start

        return MoveResult(
            success=True,
            message=f"Moved {direction} from {old_position} to {self.agent_position}. {reward_message}",
            new_position=self.agent_position
        )
    
    # ========== UTILITY FUNCTIONS ==========
    
    def get_internal_structure(self) -> Dict:
        """Returns the complete maze graph (for debugging/inspection)"""
        if not self.maze_active:
            return {"error": "No active maze"}
        
        return {
            "nodes": self.nodes,
            "start": self.start,
            "goal": self.goal,
            "agent_position": self.agent_position,
            "dimensions": {"width": self.width, "height": self.height}
        }
    
    def visualize_human(self) -> str:
        """Human-readable ASCII visualization"""
        if not self.maze_active:
            return "No active maze. Use create_maze() first."
        
        # Create grid with walls
        grid = [[' ' for _ in range(self.width * 2 + 1)] 
                for _ in range(self.height * 2 + 1)]
        
        # Draw outer walls
        for i in range(self.width * 2 + 1):
            grid[0][i] = '─'
            grid[self.height * 2][i] = '─'
        for i in range(self.height * 2 + 1):
            grid[i][0] = '│'
            grid[i][self.width * 2] = '│'
        
        # Draw corners
        grid[0][0] = '┌'
        grid[0][self.width * 2] = '┐'
        grid[self.height * 2][0] = '└'
        grid[self.height * 2][self.width * 2] = '┘'
        
        # Draw internal walls and markers
        for pos, node in self.nodes.items():
            x, y = map(int, pos.split(','))
            cell_x, cell_y = x * 2 + 1, y * 2 + 1
            
            # Place markers
            if pos == self.agent_position:
                grid[cell_y][cell_x] = 'A'
            elif pos == self.goal:
                grid[cell_y][cell_x] = 'G'
            elif pos == self.start:
                grid[cell_y][cell_x] = 'S'
            else:
                grid[cell_y][cell_x] = '·'
            
            # Draw walls where there are no connections
            has_north = any(c["direction"] == "NORTH" for c in node["connections"])
            has_south = any(c["direction"] == "SOUTH" for c in node["connections"])
            has_east = any(c["direction"] == "EAST" for c in node["connections"])
            has_west = any(c["direction"] == "WEST" for c in node["connections"])
            
            if not has_north and y > 0:
                grid[cell_y - 1][cell_x] = '─'
            if not has_south and y < self.height - 1:
                grid[cell_y + 1][cell_x] = '─'
            if not has_east and x < self.width - 1:
                grid[cell_y][cell_x + 1] = '│'
            if not has_west and x > 0:
                grid[cell_y][cell_x - 1] = '│'
        
        return '\n'.join(''.join(row) for row in grid)

    def display_information(self):
        string_response=f"Maze Size: {self.width}x{self.height}\n"
        string_response+=f"Maze Agent Position: {self.agent_position}\n"
        string_response+=f"Maze Goal Position: {self.goal}\n"
        string_response+=f"Maze Start Position: {self.start}\n"
        string_response+=f"Maze Steps Taken: {self.steps_taken}\n"
        string_response+=f"Maze Active: {self.maze_active}\n"

        maze_visualization=self.visualize_human()
        string_response+=f"Maze Visualization:\n{maze_visualization}\n"
        return string_response

# Demo usage simulating an agent
if __name__ == "__main__":
    maze_env = MazeEnvironment()
    
    print("=" * 60)
    print("SIMULATING AGENT INTERACTION WITH MAZE TOOLS")
    print("=" * 60)
    
    # Tool 1: Create a new maze
    print("\n[Agent calls: create_maze(width=6, height=6)]")
    result = maze_env.create_maze(width=6, height=6)
    print(json.dumps(result, indent=2))
    optimal_steps = maze_env._calculate_optimal_steps()
    print(f"Optimal steps: {optimal_steps}")
    # test different reward scenarios
    scenarios = [
        {"steps": optimal_steps},
        {"steps": optimal_steps + 5},
        {"steps": optimal_steps + 10},
        {"steps": optimal_steps + 20},
        {"steps": optimal_steps + 50},
        {"steps": optimal_steps + 100},
        {"steps": optimal_steps + 200},
        {"steps": optimal_steps + 500},
        {"steps": optimal_steps + 1000},
    ]
    for scenario in scenarios:
        maze_env.steps_taken = scenario["steps"]
        reward = maze_env.calculate_reward()
        print(f"Steps: {scenario['steps']} Reward: {reward}")

    
    # Show human visualization (agent would never see this)
    print("\n" + "-" * 60)
    print("HUMAN VIEW (debugging only - agent never sees this)")
    print("-" * 60)
    print(maze_env.visualize_human())
    print("\nLegend: S=Start, G=Goal, A=Agent, ·=Empty")
    
    # Tool 2: Observe environment
    print("\n" + "-" * 60)
    print("[Agent calls: observe_environment()]")
    print("-" * 60)
    obs = maze_env.observe_environment()
    print(json.dumps(asdict(obs), indent=2))
    
    # Tool 3: Attempt moves
    print("\n" + "-" * 60)
    print("AGENT ATTEMPTING MOVES")
    print("-" * 60)
    
    for i in range(8):
        obs = maze_env.observe_environment()
        
        if obs.is_goal:
            print(f"\n🎉 GOAL REACHED at {obs.current_position}!")
            break
        
        if obs.available_moves:
            # Pick a random valid move
            move_choice = random.choice(obs.available_moves)
            direction = move_choice["direction"]
            
            print(f"\n[Agent calls: move('{direction}')]")
            move_result = maze_env.move(direction)
            print(json.dumps(asdict(move_result), indent=2))
        else:
            print("\nNo available moves - agent is stuck!")
            break
    
    # Test invalid moves
    print("\n" + "-" * 60)
    print("TESTING INVALID MOVES")
    print("-" * 60)
    
    print("\n[Agent calls: move('INVALID_DIRECTION')]")
    result = maze_env.move("INVALID_DIRECTION")
    print(json.dumps(asdict(result), indent=2))
    
    obs = maze_env.observe_environment()
    if obs.blocked_directions:
        blocked = obs.blocked_directions[0]
        print(f"\n[Agent calls: move('{blocked}') - blocked direction]")
        result = maze_env.move(blocked)
        print(json.dumps(asdict(result), indent=2))
    
    # Create a new different maze
    print("\n" + "=" * 60)
    print("CREATING A NEW RANDOM MAZE")
    print("=" * 60)
    print("\n[Agent calls: create_maze(width=8, height=5)]")
    result = maze_env.create_maze(width=8, height=5)
    print(json.dumps(result, indent=2))
    
    print("\n" + "-" * 60)
    print("NEW MAZE (human view)")
    print("-" * 60)
    print(maze_env.visualize_human())