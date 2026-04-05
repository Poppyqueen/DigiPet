from __future__ import annotations

import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Reward constants (consumed by MazeController, defined here for locality)
# ---------------------------------------------------------------------------
BASE_REWARD = 20.0
MAZE_SIZE_MULTIPLIER = 0.4
STEPS_TAKEN_PENALTY_MULTIPLIER = 0.05
PENALTY_THRESHOLD_BUFFER = 2.5    # penalty starts after steps > optimal * this
EFFICIENCY_BONUS_THRESHOLD = 1.0  # bonus when steps <= optimal * this
EFFICIENCY_BONUS_MULTIPLIER = 1.4

DIFFICULTY_NORMAL   = "normal"    # Recursive backtracking (DFS) — long corridors
DIFFICULTY_HARDCORE = "hardcore"  # Prim's algorithm — dense branching, much harder
DIFFICULTY_INSANE   = "insane"    # Prim's algorithm + goal hidden until line-of-sight

HARDCORE_REWARD_MULTIPLIER = 1.75  # Prim's mazes are harder — reward reflects that
INSANE_REWARD_MULTIPLIER   = 2.50  # Hidden goal on top of Prim's density

# Difficulties that use Prim's carving
_PRIMS_DIFFICULTIES = {DIFFICULTY_HARDCORE, DIFFICULTY_INSANE}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProbeEntry:
    """
    A single point of interest discovered by the directional probe.

    The probe travels straight from the agent in one of the four cardinal
    directions, annotating every cell it passes through.  It stops only when
    it hits a wall (no connection in the travel direction).
    """
    position: str                    # "x,y"
    distance: int                    # steps from agent
    direction: str                   # which ray this came from  (NORTH/SOUTH/EAST/WEST)

    # What the probe noticed at this cell
    side_exits: List[str] = field(default_factory=list)
    # Directions perpendicular to travel that are open (the "peripheral" junctions)

    is_goal: bool = False            # True only if goal is visible at this cell
    prop_name: Optional[str] = None  # Name of prop on this cell (no description via probe)


@dataclass
class Observation:
    """What the agent can observe from their current position."""
    current_position: str
    coordinates: Dict[str, int]
    available_moves: List[Dict[str, str]]
    blocked_directions: List[str]
    is_goal: bool

    # Richer perception data (populated by MazeEnvironment.observe())
    probe_results: List[ProbeEntry] = field(default_factory=list)
    # Props whose description the agent can read (standing on the same cell)
    current_prop: Optional[dict] = None   # {"name": ..., "description": ...}
    # Whether the goal's position is known (False on INSANE until seen)
    goal_visible: bool = True


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
    Deterministic maze simulation reconstructed from
    (seed, width, height, difficulty, props_seed, maze_type).

    Owns no state-manager, no signals, no rewards — those live in MazeController.

    Usage pattern:
        env = MazeEnvironment()
        env.build(seed, width, height, goal, difficulty,
                  props_seed=..., maze_type=...)
        env.teleport(pos)
        obs  = env.observe()
        result = env.move("NORTH")
    """

    OPPOSITE = {"NORTH": "SOUTH", "SOUTH": "NORTH", "EAST": "WEST", "WEST": "EAST"}

    # The two axes perpendicular to each direction of travel
    _PERP = {
        "NORTH": ("EAST", "WEST"),
        "SOUTH": ("EAST", "WEST"),
        "EAST":  ("NORTH", "SOUTH"),
        "WEST":  ("NORTH", "SOUTH"),
    }

    def __init__(self):
        self.width: int = 0
        self.height: int = 0
        self.nodes: Dict[str, dict] = {}   # pos → {"connections": [...], "type": str}
        self.props: Dict[str, dict] = {}   # pos → {"name": str, "description": str, "ascii_char": str}
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
        props_seed: Optional[int] = None,
        maze_type: Optional[str] = None,
    ) -> None:
        """
        Fully reconstruct the maze from its nuclear parameters.
        After this call the agent is at start; call teleport() to restore position.

        Args:
            goal:       [x, y] corner chosen at creation time.
            props_seed: Dedicated seed for prop placement.  If None, props are
                        skipped (backwards-compatible with old saves).
            maze_type:  Key into PROP_REGISTRY.  Determines which props can spawn.
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

        if difficulty in _PRIMS_DIFFICULTIES:
            self._carve_prims()
        else:
            self._carve_dfs()

        random.seed()  # detach from the maze-shape seed

        # Props — only placed when props_seed is provided
        self.props = {}
        if props_seed is not None:
            self._place_props(props_seed, maze_type)

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
        """
        Return what the agent can see from their current cell.

        Includes:
          - immediate available moves / blocked directions (unchanged)
          - directional probe results (junctions, props, goal if visible)
          - current-cell prop description (if standing on one)
          - goal_visible flag (False on INSANE until goal is in line-of-sight)
        """
        self._require_active()

        node = self.nodes[self.agent_position]
        x, y = map(int, self.agent_position.split(","))

        available_moves: List[Dict[str, str]] = []
        blocked_directions: List[str] = []

        for direction in ("NORTH", "SOUTH", "EAST", "WEST"):
            conn = next(
                (c for c in node["connections"] if c["direction"] == direction), None
            )
            if conn:
                available_moves.append(
                    {"direction": direction, "destination": conn["to"]}
                )
            else:
                blocked_directions.append(direction)

        # Determine if goal is visible (always visible except INSANE)
        goal_visible = self._goal_in_los()

        # Run probes in every open direction
        probe_results = self._run_probes(goal_visible)

        # Check for a prop underfoot
        current_prop = self.props.get(self.agent_position)

        print(self.visualize())

        return Observation(
            current_position=self.agent_position,
            coordinates={"x": x, "y": y},
            available_moves=available_moves,
            blocked_directions=blocked_directions,
            is_goal=(self.agent_position == self.goal),
            probe_results=probe_results,
            current_prop=current_prop,
            goal_visible=goal_visible,
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
        conn = next(
            (c for c in node["connections"] if c["direction"] == direction), None
        )

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
        elif self.difficulty == DIFFICULTY_INSANE:
            reward *= INSANE_REWARD_MULTIPLIER

        return max(0.0, reward)

    # ------------------------------------------------------------------
    # Utility / debug
    # ------------------------------------------------------------------

    def visualize(self, hide_goal: bool = False) -> str:
        """
        ASCII art of the maze.

        Legend: S=Start  G=Goal (or ? if hidden)  A=Agent  ·=Empty
                Props shown by their ascii_char when not obscured by agent/start/goal.

        Args:
            hide_goal: If True, the goal cell is rendered as '?' instead of 'G'.
                       MazeController passes this for INSANE difficulty when the
                       goal has not yet entered line-of-sight.
        """
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

            # Cell character — priority: agent > goal > start > prop > empty
            if pos == self.agent_position:
                cell_char = "A"
            elif pos == self.goal:
                cell_char = "?" if hide_goal else "G"
            elif pos == self.start:
                cell_char = "S"
            elif pos in self.props:
                cell_char = self.props[pos].get("ascii_char", "P")
            else:
                cell_char = "·"

            grid[cy][cx] = cell_char

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
    # Private — line-of-sight and probe
    # ------------------------------------------------------------------

    def _goal_in_los(self) -> bool:
        """
        Return True if the goal is in line-of-sight from the agent's position,
        or if the difficulty is not INSANE (goal is always visible otherwise).

        Line-of-sight: travel in each of the 4 directions along open corridors.
        The goal is visible if it appears in any of those straight lines before
        the first wall terminates that ray.

        Special case: agent is adjacent to the goal (distance == 1) always counts.
        """
        if self.difficulty != DIFFICULTY_INSANE:
            return True

        # Standing on the goal — trivially visible
        if self.agent_position == self.goal:
            return True

        for direction in ("NORTH", "SOUTH", "EAST", "WEST"):
            pos = self.agent_position
            while True:
                node = self.nodes[pos]
                conn = next(
                    (c for c in node["connections"] if c["direction"] == direction),
                    None,
                )
                if conn is None:
                    break  # wall — ray terminates
                pos = conn["to"]
                if pos == self.goal:
                    return True

        return False

    def _run_probes(self, goal_visible: bool) -> List[ProbeEntry]:
        """
        Cast a ray from the agent in each open direction.

        The probe travels cell-by-cell until it hits a wall.  At each cell it
        records:
          • side_exits  — perpendicular open passages ("peripheral vision")
          • is_goal     — whether the goal sits here AND is currently visible
          • prop_name   — name of any prop at this cell (description withheld)

        The agent's own cell is not included in probe_results.
        """
        results: List[ProbeEntry] = []
        node = self.nodes[self.agent_position]

        for direction in ("NORTH", "SOUTH", "EAST", "WEST"):
            conn = next(
                (c for c in node["connections"] if c["direction"] == direction), None
            )
            if conn is None:
                continue  # wall immediately — no probe in this direction

            pos = conn["to"]
            distance = 1

            while True:
                current_node = self.nodes[pos]

                # Peripheral exits: perpendicular open passages
                perp_dirs = self._PERP[direction]
                side_exits = [
                    d for d in perp_dirs
                    if any(c["direction"] == d for c in current_node["connections"])
                ]

                # Goal visibility at this cell
                is_goal_here = (pos == self.goal) and goal_visible

                # Prop at this cell (name only — description requires standing on it)
                prop_here = self.props.get(pos)
                prop_name = prop_here["name"] if prop_here else None

                entry = ProbeEntry(
                    position=pos,
                    distance=distance,
                    direction=direction,
                    side_exits=side_exits,
                    is_goal=is_goal_here,
                    prop_name=prop_name,
                )
                results.append(entry)

                # Advance probe along the same direction
                fwd_conn = next(
                    (c for c in current_node["connections"] if c["direction"] == direction),
                    None,
                )
                if fwd_conn is None:
                    break  # wall — ray terminates

                pos = fwd_conn["to"]
                distance += 1

        return results

    # ------------------------------------------------------------------
    # Private — prop placement
    # ------------------------------------------------------------------

    def _place_props(self, props_seed: int, maze_type: Optional[str]) -> None:
        """
        Deterministically place props from the type's catalogue onto walkable
        cells, using props_seed for all randomness.

        The algorithm:
          1. Build the pool of candidate cells (all cells except start and goal).
          2. Use the catalogue's density_range to decide how many cells get props.
          3. Randomly select that many cells (without replacement).
          4. For each selected cell, weighted-randomly pick a prop from the catalogue.

        Everything uses the props_seed so the result is perfectly reproducible
        without storing the prop map in persistent state.
        """
        # Import here to avoid circular imports at module load time
        from .maze_props import get_catalogue

        catalogue = get_catalogue(maze_type)
        rng = random.Random(props_seed)

        # Candidate cells: walkable, not start, not goal
        candidates = [
            pos for pos in self.nodes
            if pos != self.start and pos != self.goal
        ]

        if not candidates:
            return

        min_density, max_density = catalogue.density_range
        density = rng.uniform(min_density, max_density)
        n_props = max(1, round(len(candidates) * density))
        n_props = min(n_props, len(candidates))

        chosen_cells = rng.sample(candidates, n_props)

        # Weighted selection of which prop appears at each cell
        props_list = catalogue.props
        weights = [p.weight for p in props_list]

        for cell in chosen_cells:
            prop = rng.choices(props_list, weights=weights, k=1)[0]
            self.props[cell] = {
                "name": prop.name,
                "description": prop.description,
                "ascii_char": prop.ascii_char,
            }

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
        self.nodes[b]["connections"].append(
            {"to": a, "direction": self.OPPOSITE[direction]}
        )

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