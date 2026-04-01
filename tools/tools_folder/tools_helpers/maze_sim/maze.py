from __future__ import annotations

import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

# ---------------------------------------------------------------------------
# Reward constants (consumed by MazeController, defined here for locality)
# ---------------------------------------------------------------------------
BASE_REWARD = 20.0
MAZE_SIZE_MULTIPLIER = 0.4
STEPS_TAKEN_PENALTY_MULTIPLIER = 0.05
PENALTY_THRESHOLD_BUFFER = 2.5   # penalty starts after steps > optimal * this
EFFICIENCY_BONUS_THRESHOLD = 1.0  # bonus when steps <= optimal * this
EFFICIENCY_BONUS_MULTIPLIER = 1.4

DIFFICULTY_NORMAL   = "normal"    # Recursive backtracking (DFS) — long corridors
DIFFICULTY_HARDCORE = "hardcore"  # Prim's algorithm — dense branching, much harder

HARDCORE_REWARD_MULTIPLIER = 1.75  # Prim's mazes are harder — reward reflects that


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    """What the agent can observe from their current position."""
    current_position: str
    coordinates: Dict[str, int]
    available_moves: List[Dict[str, str]]
    blocked_directions: List[str]
    is_goal: bool


@dataclass
class MoveResult:
    """Result of a single move attempt."""
    success: bool
    message: str
    new_position: Optional[str] = None
    reached_goal: bool = False


# ---------------------------------------------------------------------------
# MazeEnvironment — pure simulation, no I/O, no persistence
# ---------------------------------------------------------------------------

class MazeEnvironment:
    """
    Deterministic maze simulation reconstructed from (seed, width, height, difficulty).
    Owns no state-manager, no signals, no rewards — those live in MazeController.

    Usage pattern:
        env = MazeEnvironment()
        env.build(seed, width, height, difficulty)
        env.teleport(pos)          # restore agent to saved position
        obs  = env.observe()
        result = env.move("NORTH")
    """

    OPPOSITE = {"NORTH": "SOUTH", "SOUTH": "NORTH", "EAST": "WEST", "WEST": "EAST"}

    def __init__(self):
        self.width: int = 0
        self.height: int = 0
        self.nodes: Dict[str, dict] = {}
        self.start: str = ""
        self.goal: str = ""
        self.agent_position: str = ""
        self.steps_taken: int = 0
        self.difficulty: str = DIFFICULTY_NORMAL
        self._active: bool = False

    # ------------------------------------------------------------------
    # Public build interface
    # ------------------------------------------------------------------

    def build(
        self,
        seed: int,
        width: int,
        height: int,
        goal: List[int],
        difficulty: str = DIFFICULTY_NORMAL,
        steps_taken: int = 0,
    ) -> None:
        """
        Fully reconstruct the maze from its nuclear parameters.
        After this call the agent is at start; call teleport() to restore position.

        Args:
            goal: [x, y] corner chosen at creation time, stored in MazeState.
        """
        random.seed(seed)

        self.width = width
        self.height = height
        self.start = "0,0"
        self.goal = f"{goal[0]},{goal[1]}"
        self.nodes = {
            f"{x},{y}": {"connections": [], "type": "empty"}
            for y in range(height)
            for x in range(width)
        }

        if difficulty == DIFFICULTY_HARDCORE:
            self._carve_prims()
        else:
            self._carve_dfs()

        random.seed()  # detach from the fixed seed

        self.agent_position = self.start
        self.steps_taken = steps_taken
        self.difficulty = difficulty
        self._active = True

    def teleport(self, pos: str) -> None:
        """Restore agent to a previously saved position (no step cost)."""
        if pos in self.nodes:
            self.agent_position = pos

    # ------------------------------------------------------------------
    # Agent-facing tools (called by MazeController)
    # ------------------------------------------------------------------

    def observe(self) -> Observation:
        """Return what the agent can see from their current cell."""
        self._require_active()

        node = self.nodes[self.agent_position]
        x, y = map(int, self.agent_position.split(","))

        available_moves: List[Dict[str, str]] = []
        blocked_directions: List[str] = []

        for direction in ("NORTH", "SOUTH", "EAST", "WEST"):
            conn = next((c for c in node["connections"] if c["direction"] == direction), None)
            if conn:
                available_moves.append({"direction": direction, "destination": conn["to"]})
            else:
                blocked_directions.append(direction)

        print(self.visualize())


        return Observation(
            current_position=self.agent_position,
            coordinates={"x": x, "y": y},
            available_moves=available_moves,
            blocked_directions=blocked_directions,
            is_goal=(self.agent_position == self.goal),
        )

    def move(self, direction: str) -> MoveResult:
        """Attempt to move one cell. Returns result; caller handles rewards/state."""
        self._require_active()

        direction = direction.upper()
        if direction not in ("NORTH", "SOUTH", "EAST", "WEST"):
            return MoveResult(
                success=False,
                message=f"Invalid direction '{direction}'. Use NORTH, SOUTH, EAST, or WEST.",
            )

        node = self.nodes[self.agent_position]
        conn = next((c for c in node["connections"] if c["direction"] == direction), None)

        if conn is None:
            return MoveResult(
                success=False,
                message=f"Cannot move {direction} — wall.",
            )

        old_pos = self.agent_position
        self.agent_position = conn["to"]
        self.steps_taken += 1
        reached_goal = self.agent_position == self.goal

        print(self.visualize())

        return MoveResult(
            success=True,
            message=f"Moved {direction} from {old_pos} to {self.agent_position}.",
            new_position=self.agent_position,
            reached_goal=reached_goal,
        )

    # ------------------------------------------------------------------
    # Reward calculation (pure, uses only sim state)
    # ------------------------------------------------------------------

    def calculate_reward(self) -> float:
        optimal = self._bfs_optimal_steps()
        maze_size = self.width * self.height
        base = BASE_REWARD + maze_size * MAZE_SIZE_MULTIPLIER
        reward = base

        penalty_threshold = optimal * PENALTY_THRESHOLD_BUFFER
        if self.steps_taken > penalty_threshold:
            excess = self.steps_taken - penalty_threshold
            reward -= excess * STEPS_TAKEN_PENALTY_MULTIPLIER

        if 0 < self.steps_taken <= optimal * EFFICIENCY_BONUS_THRESHOLD:
            reward *= EFFICIENCY_BONUS_MULTIPLIER

        if self.difficulty == DIFFICULTY_HARDCORE:
            reward *= HARDCORE_REWARD_MULTIPLIER

        return max(0.0, reward)

    # ------------------------------------------------------------------
    # Utility / debug
    # ------------------------------------------------------------------

    def visualize(self) -> str:
        """ASCII art of the maze. Legend: S=Start  G=Goal  A=Agent  ·=Empty"""
        if not self._active:
            return "No active maze."

        grid = [[" "] * (self.width * 2 + 1) for _ in range(self.height * 2 + 1)]

        for i in range(self.width * 2 + 1):
            grid[0][i] = "─"
            grid[self.height * 2][i] = "─"
        for i in range(self.height * 2 + 1):
            grid[i][0] = "│"
            grid[i][self.width * 2] = "│"

        grid[0][0] = "┌"
        grid[0][self.width * 2] = "┐"
        grid[self.height * 2][0] = "└"
        grid[self.height * 2][self.width * 2] = "┘"

        for pos, node in self.nodes.items():
            x, y = map(int, pos.split(","))
            cx, cy = x * 2 + 1, y * 2 + 1

            if pos == self.agent_position:
                grid[cy][cx] = "A"
            elif pos == self.goal:
                grid[cy][cx] = "G"
            elif pos == self.start:
                grid[cy][cx] = "S"
            else:
                grid[cy][cx] = "·"

            dirs = {c["direction"] for c in node["connections"]}
            if "NORTH" not in dirs and y > 0:
                grid[cy - 1][cx] = "─"
            if "SOUTH" not in dirs and y < self.height - 1:
                grid[cy + 1][cx] = "─"
            if "EAST" not in dirs and x < self.width - 1:
                grid[cy][cx + 1] = "│"
            if "WEST" not in dirs and x > 0:
                grid[cy][cx - 1] = "│"

        return "\n".join("".join(row) for row in grid)

    # ------------------------------------------------------------------
    # Private — maze generation algorithms
    # ------------------------------------------------------------------

    def _carve_dfs(self) -> None:
        """Recursive backtracking (DFS). Produces long corridors — easier to navigate."""
        visited = {self.start}
        stack = [self.start]

        while stack:
            current = stack[-1]
            neighbors = self._unvisited_neighbors(current, visited)
            if neighbors:
                nxt, direction = random.choice(neighbors)
                self._connect(current, nxt, direction)
                visited.add(nxt)
                stack.append(nxt)
            else:
                stack.pop()

    def _carve_prims(self) -> None:
        """Randomised Prim's. Produces dense branching — significantly harder."""
        visited = {self.start}

        # frontier entries: (from_pos, to_pos, direction)
        frontier: List[Tuple[str, str, str]] = self._frontier_edges(self.start, visited)

        while frontier:
            idx = random.randrange(len(frontier))
            from_pos, to_pos, direction = frontier.pop(idx)

            if to_pos in visited:
                continue

            self._connect(from_pos, to_pos, direction)
            visited.add(to_pos)
            frontier.extend(self._frontier_edges(to_pos, visited))

    def _frontier_edges(
        self, pos: str, visited: set
    ) -> List[Tuple[str, str, str]]:
        x, y = map(int, pos.split(","))
        candidates = []
        if x > 0:
            candidates.append((pos, f"{x-1},{y}", "WEST"))
        if x < self.width - 1:
            candidates.append((pos, f"{x+1},{y}", "EAST"))
        if y > 0:
            candidates.append((pos, f"{x},{y-1}", "NORTH"))
        if y < self.height - 1:
            candidates.append((pos, f"{x},{y+1}", "SOUTH"))
        return [(f, t, d) for f, t, d in candidates if t not in visited]

    def _unvisited_neighbors(
        self, pos: str, visited: set
    ) -> List[Tuple[str, str]]:
        x, y = map(int, pos.split(","))
        candidates = []
        if x > 0:
            candidates.append((f"{x-1},{y}", "WEST"))
        if x < self.width - 1:
            candidates.append((f"{x+1},{y}", "EAST"))
        if y > 0:
            candidates.append((f"{x},{y-1}", "NORTH"))
        if y < self.height - 1:
            candidates.append((f"{x},{y+1}", "SOUTH"))
        return [(n, d) for n, d in candidates if n not in visited]

    def _connect(self, a: str, b: str, direction: str) -> None:
        self.nodes[a]["connections"].append({"to": b, "direction": direction})
        self.nodes[b]["connections"].append({"to": a, "direction": self.OPPOSITE[direction]})

    def _bfs_optimal_steps(self) -> int:
        queue = [(self.start, 0)]
        visited = {self.start}
        while queue:
            pos, dist = queue.pop(0)
            if pos == self.goal:
                return dist
            for conn in self.nodes.get(pos, {}).get("connections", []):
                nxt = conn["to"]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, dist + 1))
        return 0  # unreachable in a valid maze

    def _require_active(self) -> None:
        if not self._active:
            raise RuntimeError("No active maze. Call build() first.")