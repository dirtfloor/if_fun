"""Guard predicates for transitions. Pure; no I/O.

All Guard variants are frozen pydantic models. Guards are never hashable
while they carry dict-typed ``value`` fields, so do not store them in sets.
"""

from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import ItemId, RoomId

if TYPE_CHECKING:
    from if_fun.world.state import WorldState  # ty: ignore[unresolved-import]


class _GuardBase(BaseModel):
    model_config = ConfigDict(frozen=True)


class HasItemGuard(_GuardBase):
    type: Literal["has_item"] = "has_item"
    item_id: ItemId


class PlayerInRoomGuard(_GuardBase):
    type: Literal["player_in_room"] = "player_in_room"
    room_id: RoomId


class RoomFlagEqualsGuard(_GuardBase):
    type: Literal["room_flag_equals"] = "room_flag_equals"
    room_id: RoomId
    flag: str
    value: Any


class GlobalFlagEqualsGuard(_GuardBase):
    type: Literal["global_flag_equals"] = "global_flag_equals"
    flag: str
    value: Any


Guard = Annotated[
    HasItemGuard | PlayerInRoomGuard | RoomFlagEqualsGuard | GlobalFlagEqualsGuard,
    Field(discriminator="type"),
]


def evaluate(guard: Guard, world: "WorldState") -> bool:
    match guard:
        case HasItemGuard(item_id=item_id):
            return item_id in world.player.inventory
        case PlayerInRoomGuard(room_id=room_id):
            return world.player.location == room_id
        case RoomFlagEqualsGuard(room_id=room_id, flag=flag, value=value):
            room = world.rooms.get(room_id)
            return room is not None and room.flags.get(flag) == value
        case GlobalFlagEqualsGuard(flag=flag, value=value):
            return world.globals.get(flag) == value
