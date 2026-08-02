from typing import Optional, List
from pydantic import BaseModel, Field
from typing import Literal

from .maze_props import PROP_REGISTRY

# 1. Extract the keys into a constant tuple
_maze_type_keys = tuple(PROP_REGISTRY.keys()) # Add more props and types for mazes here!

# 2. Create the Literal type 
# Note: type: ignore is used because Literal technically expects 
# hardcoded strings, but this is the standard way to keep it DRY.
MazeType = Literal[_maze_type_keys]  # type: ignore[valid-type] 

# 3. Create a helper string for error messages/logging
maze_type_names = ", ".join(_maze_type_keys)

class MazeState(BaseModel):
    # Use Optional[type] or type | None so that default=None is VALID
    seed: Optional[int] = Field(
        default=None,
        description="Always set to None. The seed for the maze generation algorithm, managed by the maze tool."
    )
    size: Optional[List[int]] = Field(
        default=None,
        description="Always set to None. The dimensions of the maze [width, height], managed by the maze tool."
    )
    difficulty: Optional[str] = Field(
        default=None,
        description="Always set to None. The maze difficulty ('normal', 'hardcore', or 'insane'), managed by the maze tool."
    )
    pos: List[int] = Field(
        default=[0, 0],
        description="Always set to [0, 0], x,y. The current coordinates of the player in the maze, managed by the maze tool."
    )
    goal: Optional[List[int]] = Field(
        default=None,
        description="Always set to None. The coordinates of the goal in the maze, managed by the maze tool."
    )
    steps_taken: int = Field(
        default=0,
        description="Always set to 0. The number of steps taken by the player in the maze."
    )
    goal_reached: bool = Field(
        default=False,
        description="Always set to False. Indicates whether the player has reached the goal in the maze."
    )

    # --- Props & environment flavour ---

    maze_type: Optional[MazeType] = Field( # Or MazeType if you have that Enum defined
        default=None,
        description=(
            "The thematic type of the maze from possible types. "
            "Determines which prop catalogue is used for decorative objects. "
            "None means no type has been assigned; props will use a random catalogue."
        )
    )
    type_locked: bool = Field(
        default=False,
        description=(
            "When True the maze_type cannot be changed for this maze instance. "
            "Set to True for static items that should not change type, like a physical maze box."
        )
    )
    props_seed: Optional[int] = Field(
        default=None,
        description=(
            "Independent random seed used exclusively for deterministic prop placement. "
            "None means no props have been seeded for this maze."
        )
    )