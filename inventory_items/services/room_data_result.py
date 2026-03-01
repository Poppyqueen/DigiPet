from __future__ import annotations
from pydantic import BaseModel
from utils.time_manager import get_time_tag_from_now

class RoomDataResult(BaseModel):
    id: int
    name: str
    image: str
    music: str
    description: str
    room_types: list[str]

    @classmethod
    def from_room_dict(cls, room: dict) -> RoomDataResult:
        time_tag = get_time_tag_from_now()
        descriptions_by_time = room.get("descriptions", {})
        descriptions = descriptions_by_time.get(time_tag, [])
        if not isinstance(descriptions, list):
            descriptions = []

        return cls(
            id=room["id"],
            name=room.get("name", "Unknown Room"),
            image=room.get("image", ""),
            music=room.get("music", ""),
            description=" ".join(descriptions),
            room_types=room.get("room_types", []),
        )