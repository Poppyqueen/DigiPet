
from pydantic import BaseModel, Field

class MazeState(BaseModel):
    seed: int = Field(
        default=None,
        description="Always set to None. The seed for the maze generation algorithm, managed by the maze tool."
    )
    size: list[int] = Field(
        default=None,
        description="Always set to None. The dimensions of the maze [width, height], managed by the maze tool."
    )
    difficulty: str = Field(
        default=None,
        description="Always set to None. The maze difficulty ('normal' or 'hardcore'), managed by the maze tool."
    )
    pos: list[int] = Field(
        default=[0, 0],
        description="Always set to [0, 0], x,y. The current coordinates of the player in the maze, managed by the maze tool."
    )
    goal: list[int] = Field(
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