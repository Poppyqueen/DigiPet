from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager

import secrets
import random
from typing import Optional

from tools.tools_folder.tools_helpers.maze_sim.maze import MazeEnvironment, DIFFICULTY_NORMAL, DIFFICULTY_HARDCORE
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
 
    MAX_SQUARES = 75
 
    def __init__(self, state_manager: InventoryHouseManager, signal):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal = signal

        self.last_interact_id = None

    # Perception tools
    def percieve_data(self):
        if not self.last_interact_id:
            return ""
        item_result = self.state_manager.find_item(self.last_interact_id, MAZE_ITEM_TYPE, "accessible")
        if item_result.error:
            return ""
        
        observation = self.get_maze_state(self.last_interact_id)
        msg = f"""The last maze item you interacted with was: {self.state_manager.format_item_for_display(item_result.item_data, False)}
        State:
        {observation}
        """
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
        override: bool = False,
    ) -> str:
        """
        TOOL: create_maze
        Generates a new maze and binds it to the maze item.
 
        Args:
            interface_id: The item/interface this maze is attached to.
            width:        Maze width  (default 8, max such that width*height <= 100).
            height:       Maze height (default 8).
            difficulty:   "normal" (default) or "hardcore".
            override:     If False and a maze is already active, refuses.
 
        Returns:
            Human-readable status string.
        """
        if difficulty not in (DIFFICULTY_NORMAL, DIFFICULTY_HARDCORE):
            return (
                f"Invalid difficulty '{difficulty}'. "
                f"Choose '{DIFFICULTY_NORMAL}' or '{DIFFICULTY_HARDCORE}'."
            )
 
        if width * height > self.MAX_SQUARES:
            return (
                f"Maze too large ({width}x{height} = {width*height} squares). "
                f"Maximum is {self.MAX_SQUARES} squares."
            )
 
        # Load current state to check for an active maze
        state, err = self._load_state(interface_id)
        if err:
            return f"Error loading maze state: {err}"
 
        if state and state.seed is not None and not override:
            return (
                "A maze is already active (seed exists). "
                "Pass override=True to replace it."
            )
 
        # Generate a strong random seed (never 0)
        seed = secrets.randbits(32) or 1  # paranoia: ensure non-zero
 
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
        )
        save_err = self._save_state(interface_id, new_state)
        if save_err:
            return f"Maze generated but failed to save state: {save_err}"
        
    
        self.last_interact_id = interface_id
        
 
        diff_label = "Hardcore (Prim's)" if difficulty == DIFFICULTY_HARDCORE else "Normal (DFS)"
        return (
            f"New {width}x{height} maze created. "
            f"Difficulty: {diff_label}. "
            f"Seed: {seed}. "
            f"You are at the start (0,0). Goal is at {goal}. " # TODO: Introduce extra-insane hardcore difficulty that hides the goal from perception
            f"Use get_maze_state to observe your surroundings."
        )
 
    def get_maze_state(self, interface_id: int) -> str:
        """
        TOOL: get_maze_state
        Returns the agent's current observation — position, available moves,
        blocked directions, and whether the goal has been reached.
 
        Args:
            interface_id: The item/interface this maze is attached to.
 
        Returns:
            Human-readable observation string.
        """
        env, state, err = self._reconstruct(interface_id)
        if err:
            return err
 
        obs = env.observe()
 
        moves_str = ", ".join(
            f"{m['direction']} → ({m['destination']})" for m in obs.available_moves
        ) or "none"
        blocked_str = ", ".join(obs.blocked_directions) or "none"
 
        lines = [
            f"Position: {obs.current_position}  |  Goal: {env.goal}", # TODO: Introduce extra-insane hardcore difficulty that hides the goal from perception
            f"Steps taken: {state.steps_taken}",
            f"Available moves: {moves_str}",
            f"Blocked: {blocked_str}",
            f"At goal: {'YES 🎉' if obs.is_goal else 'No'}",
            f"Difficulty: {state.difficulty}",
        ]

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
                # First time completing this seed — award and lock reward
                reward = env.calculate_reward()
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
            return f"{result.message}{reward_message} (Warning: state save failed: {save_err})"
 
        return f"{result.message}{reward_message}"
 
    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
 
    def _load_state(self, interface_id: int) -> tuple[Optional[MazeState], Optional[str]]:
        """Read and deserialise MazeState from the item. Returns (state, error)."""
        item_result = self.state_manager.find_item(interface_id, MAZE_ITEM_TYPE, "accessible")
        if item_result.error:
            return None, item_result.error
 
        raw = item_result.item_data.get("maze_state")
        if not raw:
            # No state yet — treat as fresh
            return None, None
 
        try:
            state = MazeState(
                seed=raw["seed"],
                size=raw["size"],
                difficulty=raw.get("difficulty", DIFFICULTY_NORMAL),
                pos=raw.get("pos", [0, 0]),
                goal=raw["goal"],
                steps_taken=raw.get("steps_taken", 0),
                goal_reached=raw.get("goal_reached", False),
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
        )
        env.teleport(f"{state.pos[0]},{state.pos[1]}")
 
        return env, state, None