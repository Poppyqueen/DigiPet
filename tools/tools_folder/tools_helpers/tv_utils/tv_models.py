
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any, Literal, Annotated
## TV Models

class TVProgram(BaseModel):
    """A single program airing on a channel, broken into 3–6 sections."""
    name: str = Field(description="The name/title of the program")
    sections: list[str] = Field(
        description="Between 3 and 6 sections (segments, acts, or scenes). "
                    "Each section is 2-4 sentences describing what a viewer would see.",
        min_length=3,
        max_length=6,
    )
    section_index: int = Field(default=0, description="Index of the currently airing section")


class TVChannel(BaseModel):
    """A single channel on a TV, with its currently airing program."""
    name: str = Field(description="The channel name and number, e.g. 'Channel 1 - News'")
    description: str = Field(description="A short description of what this channel airs")
    current_program: TVProgram = Field(description="The program currently airing on this channel")


class TVState(BaseModel):
    """Snapshot of what is currently on screen — used by TVController to format output."""
    channel: str
    program: TVProgram
    section: int