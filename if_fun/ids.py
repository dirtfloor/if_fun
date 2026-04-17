from enum import StrEnum
from typing import NewType

RoomId = NewType("RoomId", str)
ItemId = NewType("ItemId", str)
MobId = NewType("MobId", str)
EventId = NewType("EventId", str)


class Direction(StrEnum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    UP = "up"
    DOWN = "down"

    def opposite(self) -> "Direction":
        return _OPPOSITES[self]

    @classmethod
    def from_token(cls, token: str) -> "Direction | None":
        return _TOKEN_TO_DIRECTION.get(token.strip().lower())


_OPPOSITES: dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
}

_TOKEN_TO_DIRECTION: dict[str, Direction] = {
    "n": Direction.NORTH,
    "north": Direction.NORTH,
    "s": Direction.SOUTH,
    "south": Direction.SOUTH,
    "e": Direction.EAST,
    "east": Direction.EAST,
    "w": Direction.WEST,
    "west": Direction.WEST,
    "u": Direction.UP,
    "up": Direction.UP,
    "d": Direction.DOWN,
    "down": Direction.DOWN,
}
