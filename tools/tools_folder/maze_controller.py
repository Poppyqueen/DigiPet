from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

import secrets
import random
from typing import Optional, List

from tools.tools_folder.tools_helpers.maze_sim.maze import (
    MazeEnvironment,
    DIFFICULTY_NORMAL,
    DIFFICULTY_HARDCORE,
    DIFFICULTY_INSANE,
)
from tools.tools_folder.tools_helpers.maze_sim.maze_props import available_types
from tools.tools_folder.tools_helpers.maze_sim.types import MazeState


MAZE_ITEM_TYPE = "maze_interface"

# ---------------------------------------------------------------------------
# MazeController — stateful coordinator, exposes string-returning agent tools
# ---------------------------------------------------------------------------

class MazeController:
    """
    Bridges the stateless MazeEnvironment sim with persistent item-based state.

    All public methods return plain strings so they can be surfaced directly
    as agent tool responses.

    Seed sentinel: seed == 0 means "no active maze".
    A non-zero seed always means a maze is live and the agent can move.
    """

    MAX_SQUARES = 50

    def __init__(self, state_manager: InventoryHouseManager, signal):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal = signal
        self.last_interact_id = None

    # ------------------------------------------------------------------
    # Interface validation
    # ------------------------------------------------------------------

    def _validate_interface(self, item_id: int):
        result = self.state_manager.find_item(
            item_id,
            required_type=MAZE_ITEM_TYPE,
            required_location="accessible",
        )
        if result.toggle_state is False:
            return None, f"Interface {self.state_manager.format_item_for_display(item_id, False)}, is 'off' can't use it like that."
        if not result.success:
            return None, result.error
        return result.item_data, None

    # ------------------------------------------------------------------
    # Perception tools
    # ------------------------------------------------------------------

    def percieve_data(self):
        if not self.last_interact_id:
            return ""
        item_result = self.state_manager.find_item(
            self.last_interact_id, MAZE_ITEM_TYPE, "accessible"
        )
        if item_result.error:
            return ""

        observation = self.get_maze_state(self.last_interact_id)
        msg = (
            f"The last maze item you interacted with was: "
            f"{self.state_manager.format_item_for_display(item_result.item_data, False)}\n"
            f"State:\n{observation}"
        )
        return msg

    # ------------------------------------------------------------------
    # Agent tools
    # ------------------------------------------------------------------

    def create_maze(
        self,
        interface_id: int,
        width: int = 8,
        height: int = 8,
        difficulty: str = DIFFICULTY_NORMAL,
        maze_type: Optional[str] = None,
        override: bool = False,
    ) -> str:
        """
        TOOL: create_maze
        Generates a new maze and binds it to the maze item.

        Args:
            interface_id: The item/interface this maze is attached to.
            width:        Maze width  (default 8, max such that width*height <= 75).
            height:       Maze height (default 8).
            difficulty:   "normal" (default), "hardcore", or "insane".
            maze_type:    Thematic type for props — one of the values returned by
                          list_maze_types().  None uses the default catalogue.
            override:     If False and a maze is already active, refuses.

        Returns:
            Human-readable status string.
        """
        valid_difficulties = (DIFFICULTY_NORMAL, DIFFICULTY_HARDCORE, DIFFICULTY_INSANE)
        if difficulty not in valid_difficulties:
            return (
                f"Invalid difficulty '{difficulty}'. "
                f"Choose one of: {', '.join(valid_difficulties)}."
            )

        if width * height > self.MAX_SQUARES:
            return (
                f"Maze too large ({width}x{height} = {width*height} squares). "
                f"Maximum is {self.MAX_SQUARES} squares."
            )

        # Validate maze_type if provided
        known_types = available_types()
        if maze_type is not None and maze_type not in known_types:
            return (
                f"Unknown maze_type '{maze_type}'. "
                f"Available types: {', '.join(known_types)}."
            )

        _, error = self._validate_interface(interface_id)
        if error:
            return error

        # Load current state to check for an active maze and read item-level flags
        state, err = self._load_state(interface_id)
        if err:
            return f"Error loading maze state: {err}"

        if state and state.seed is not None and not override:
            return (
                "A maze is already active (seed exists). "
                "Pass override=True to replace it."
            )

        # type_locked is an item-level property — the runtime never writes it,
        # only reads it.  If the item is locked we silently preserve whatever
        # type is already stored and ignore the caller's maze_type argument.
        item_type_locked = bool(state and state.type_locked)
        if item_type_locked:
            resolved_type = state.maze_type  # immutable — ignore caller's arg
        elif maze_type is not None:
            resolved_type = maze_type
        else:
            resolved_type = random.choice(known_types)

        # Generate strong random seeds (never 0)
        seed = secrets.randbits(32) or 1
        props_seed = secrets.randbits(32) or 2  # independent seed for props

        # Pick a random corner that isn't the start (0,0)
        w, h = width - 1, height - 1
        goal = random.choice([[w, 0], [0, h], [w, h]])

        new_state = MazeState(
            seed=seed,
            size=[width, height],
            difficulty=difficulty,
            pos=[0, 0],
            goal=goal,
            steps_taken=0,
            goal_reached=False,
            maze_type=resolved_type,
            type_locked=item_type_locked,   # carry forward exactly what the item had
            props_seed=props_seed,
        )
        save_err = self._save_state(interface_id, new_state)
        if save_err:
            return f"Maze generated but failed to save state: {save_err}"

        self.last_interact_id = interface_id

        diff_label = {
            DIFFICULTY_NORMAL:   "Normal (DFS)",
            DIFFICULTY_HARDCORE: "Hardcore (Prim's)",
            DIFFICULTY_INSANE:   "Insane (Prim's, hidden goal)",
        }[difficulty]

        goal_hint = (
            "Goal location hidden — find it by exploring!"
            if difficulty == DIFFICULTY_INSANE
            else f"Goal is at {goal}."
        )

        return (
            f"New {width}x{height} maze created. "
            f"Difficulty: {diff_label}. "
            f"Theme: {resolved_type}. "
            f"Seed: {seed}. "
            f"You are at the start (0,0). {goal_hint} "
            #f"Use get_maze_state to observe your surroundings."
        )

    def get_maze_state(self, interface_id: int) -> str:
        """
        TOOL: get_maze_state
        Returns the agent's current observation — position, available moves,
        blocked directions, probe results, props, and whether the goal has been reached.

        Args:
            interface_id: The item/interface this maze is attached to.

        Returns:
            Human-readable observation string.
        """
        _, error = self._validate_interface(interface_id)
        if error:
            return error

        env, state, err = self._reconstruct(interface_id)
        if err:
            return err

        obs = env.observe()

        # ---- immediate exits ----
        moves_str = ", ".join(
            f"{m['direction']} → ({m['destination']})" for m in obs.available_moves
        ) or "none"
        blocked_str = ", ".join(obs.blocked_directions) or "none"

        # ---- goal display — hidden on INSANE until visible ----
        if obs.goal_visible:
            goal_display = env.goal
        else:
            goal_display = "???"

        lines = [
            f"Position: {obs.current_position}  |  Goal: {goal_display}",
            f"Steps taken: {state.steps_taken}",
            f"Available moves: {moves_str}",
            f"Blocked: {blocked_str}",
            f"At goal: {'YES 🎉' if obs.is_goal else 'No'}",
            f"Difficulty: {state.difficulty}",
            f"Theme: {state.maze_type or 'none'}",
        ]

        # ---- current-cell prop (full description) ----
        if obs.current_prop:
            lines.append("")
            lines.append(f"In your current position you notice: [{obs.current_prop['name']}]")
            lines.append(f"  {obs.current_prop['description']}")

        # ---- probe report ----
        probe_lines = self._format_probe(obs)
        if probe_lines:
            lines.append("")
            lines.append("What you can see from here:")
            lines.extend(probe_lines)

        self.last_interact_id = interface_id

        return "\n".join(lines)

    def maze_move(self, interface_id: int, direction: str) -> str:
        """
        TOOL: maze_move
        Moves the agent one step in the given direction.

        Args:
            interface_id: The item/interface this maze is attached to.
            direction:    NORTH, SOUTH, EAST, or WEST.

        Returns:
            Human-readable result string (includes reward info on goal).
        """
        _, error = self._validate_interface(interface_id)
        if error:
            return error

        env, state, err = self._reconstruct(interface_id)
        if err:
            return err

        result = env.move(direction)
        if not result.success:
            return result.message

        # Persist updated position and step count
        new_pos = list(map(int, result.new_position.split(",")))
        state.pos = new_pos
        state.steps_taken = env.steps_taken

        reward_message = ""

        if result.reached_goal:
            if not state.goal_reached:
                reward = int(env.calculate_reward())
                reward_result = self.state_manager.adjust_currency(reward)
                state.goal_reached = True
                self._signal({
                    "type": "show_icon_popup",
                    "icon_path": "style/images/action_icons/trumpet.png",
                    "popup_type": 2,
                })
                reward_message = (
                    f" 🎉 Goal reached! Reward: {reward:.1f} currency. "
                    f"Total: {reward_result.currency}."
                )
            else:
                reward_message = (
                    " You reached the goal again, but the reward was already "
                    "collected for this maze. Create a new maze to earn more."
                )

        save_err = self._save_state(interface_id, state)
        self.last_interact_id = interface_id

        if save_err:
            return (
                f"{result.message}{reward_message} "
                f"(Warning: state save failed: {save_err})"
            )

        return f"{result.message}{reward_message}"

    def list_maze_types(self, interface_id: int) -> str:
        """
        TOOL: list_maze_types
        Returns the available maze thematic types that can be passed to create_maze.
        If this interface is type_locked, returns only the locked type instead.
        If maze_type is None on a locked interface, reports 'random'.

        Args:
            interface_id: The item/interface this maze is attached to.
        """
        _, error = self._validate_interface(interface_id)
        if error:
            return error

        state, err = self._load_state(interface_id)
        if err:
            return f"Error loading maze state: {err}"

        if state and state.type_locked:
            locked_type = state.maze_type if state.maze_type is not None else "random"
            return f"This maze interface is type-locked. Type: {locked_type}."

        types = available_types()
        return f"Available maze types: {', '.join(types)}."

    # ------------------------------------------------------------------
    # Private — probe formatting
    # ------------------------------------------------------------------

    def _format_probe(self, obs) -> List[str]:
        """
        Convert probe_results into terse, readable lines grouped by direction.

        For each ray direction, emit one line per notable cell:
          - cells that have a side exit (junction / corner)
          - cells that hold a prop
          - the goal cell (when visible)
        Cells with none of those features (plain corridor) are summarised as a
        distance marker only when the ray terminates there (dead end).
        """
        from collections import defaultdict
        by_dir = defaultdict(list)
        for entry in obs.probe_results:
            by_dir[entry.direction].append(entry)

        lines = []
        for direction in ("NORTH", "SOUTH", "EAST", "WEST"):
            ray = by_dir.get(direction, [])
            if not ray:
                continue

            dir_lines = []
            for entry in ray:
                parts = []

                if entry.side_exits:
                    exits_str = "/".join(entry.side_exits)
                    parts.append(f"junction ({exits_str})")

                if entry.is_goal:
                    parts.append("GOAL ★")

                if entry.prop_name:
                    parts.append(f"[{entry.prop_name}]")

                if parts:
                    desc = ", ".join(parts)
                    dir_lines.append(
                        f"  {direction} +{entry.distance}: {entry.position} — {desc}"
                    )

            # If the ray has no notable cells at all, report the dead end distance
            if not dir_lines:
                last = ray[-1]
                dir_lines.append(
                    f"  {direction}: clear corridor, dead end at {last.position} "
                    f"(+{last.distance})"
                )

            lines.extend(dir_lines)

        return lines

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_state(self, interface_id: int) -> tuple[Optional[MazeState], Optional[str]]:
        """Read and deserialise MazeState from the item. Returns (state, error)."""
        item_result = self.state_manager.find_item(
            interface_id, MAZE_ITEM_TYPE, "accessible"
        )
        if item_result.error:
            return None, item_result.error

        raw = item_result.item_data.get("maze_state")
        if not raw:
            return None, None  # No state yet — treat as fresh

        try:
            state = MazeState(
                seed=raw["seed"],
                size=raw["size"],
                difficulty=raw.get("difficulty", DIFFICULTY_NORMAL),
                pos=raw.get("pos", [0, 0]),
                goal=raw["goal"],
                steps_taken=raw.get("steps_taken", 0),
                goal_reached=raw.get("goal_reached", False),
                # New fields — gracefully absent in old saves
                maze_type=raw.get("maze_type", None),
                type_locked=raw.get("type_locked", False),
                props_seed=raw.get("props_seed", None),
            )
        except (KeyError, TypeError) as exc:
            return None, f"Corrupt maze state: {exc}"

        return state, None

    def _save_state(self, interface_id: int, state: MazeState) -> Optional[str]:
        """Persist MazeState back to the item. Returns error string or None."""
        result = self.state_manager.set_item_attribute(
            interface_id, key="maze_state", value=state.model_dump()
        )
        return result.error if result.error else None

    def _reconstruct(
        self, interface_id: int
    ) -> tuple[Optional[MazeEnvironment], Optional[MazeState], Optional[str]]:
        """
        Load state, gate on active seed, reconstruct sim, teleport to saved pos.
        Returns (env, state, error). On error, env and state are None.
        """
        state, err = self._load_state(interface_id)
        if err:
            return None, None, f"Error loading maze state: {err}"

        if not state or state.seed is None:
            return None, None, (
                "No active maze found. Use create_maze to start one."
            )

        env = MazeEnvironment()
        env.build(
            seed=state.seed,
            width=state.size[0],
            height=state.size[1],
            goal=state.goal,
            difficulty=state.difficulty,
            steps_taken=state.steps_taken,
            props_seed=state.props_seed,
            maze_type=state.maze_type,
        )
        env.teleport(f"{state.pos[0]},{state.pos[1]}")

        return env, state, None