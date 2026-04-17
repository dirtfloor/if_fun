"""Effects produced by transitions. Pure; return a new WorldState.

All Effect variants are frozen pydantic models. Effects with dict-typed
``value`` or ``payload`` fields are never hashable; do not store them in
sets. Non-JSON-native Python types will coerce on JSON round-trip.
"""

from typing import TYPE_CHECKING, Annotated, Any, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import EventId, ItemId, RoomId
from if_fun.world.events import Event, EventKind

if TYPE_CHECKING:
    from if_fun.world.state import WorldState  # ty: ignore[unresolved-import]


class _EffectBase(BaseModel):
    model_config = ConfigDict(frozen=True)


class MovePlayerEffect(_EffectBase):
    type: Literal["move_player"] = "move_player"
    room_id: RoomId


class AddItemToInventoryEffect(_EffectBase):
    type: Literal["add_item_to_inventory"] = "add_item_to_inventory"
    item_id: ItemId


class RemoveItemFromRoomEffect(_EffectBase):
    type: Literal["remove_item_from_room"] = "remove_item_from_room"
    room_id: RoomId
    item_id: ItemId


class SetRoomFlagEffect(_EffectBase):
    type: Literal["set_room_flag"] = "set_room_flag"
    room_id: RoomId
    flag: str
    value: Any


class SetGlobalFlagEffect(_EffectBase):
    type: Literal["set_global_flag"] = "set_global_flag"
    flag: str
    value: Any


class EmitEventEffect(_EffectBase):
    type: Literal["emit_event"] = "emit_event"
    event_id: EventId
    kind: EventKind
    payload: dict[str, Any] = Field(default_factory=dict)


Effect = Annotated[
    MovePlayerEffect
    | AddItemToInventoryEffect
    | RemoveItemFromRoomEffect
    | SetRoomFlagEffect
    | SetGlobalFlagEffect
    | EmitEventEffect,
    Field(discriminator="type"),
]


def apply(effect: Effect, world: "WorldState") -> "WorldState":
    """Return a new WorldState with ``effect`` applied. The input is not mutated."""

    match effect:
        case MovePlayerEffect(room_id=room_id):
            new_player = world.player.model_copy(update={"location": room_id})
            return world.model_copy(update={"player": new_player})

        case AddItemToInventoryEffect(item_id=item_id):
            new_inv = world.player.inventory | {item_id}
            new_player = world.player.model_copy(update={"inventory": new_inv})
            return world.model_copy(update={"player": new_player})

        case RemoveItemFromRoomEffect(room_id=room_id, item_id=item_id):
            room = world.rooms[room_id]
            new_items = room.items_present - {item_id}
            new_room = room.model_copy(update={"items_present": new_items})
            new_rooms = {**world.rooms, room_id: new_room}
            return world.model_copy(update={"rooms": new_rooms})

        case SetRoomFlagEffect(room_id=room_id, flag=flag, value=value):
            room = world.rooms[room_id]
            new_flags = {**room.flags, flag: value}
            new_room = room.model_copy(update={"flags": new_flags})
            new_rooms = {**world.rooms, room_id: new_room}
            return world.model_copy(update={"rooms": new_rooms})

        case SetGlobalFlagEffect(flag=flag, value=value):
            new_globals = {**world.globals, flag: value}
            return world.model_copy(update={"globals": new_globals})

        case EmitEventEffect(event_id=event_id, kind=kind, payload=payload):
            ev = Event(id=event_id, turn=world.turn, kind=kind, payload=payload)
            new_log = [*world.event_log, ev]
            return world.model_copy(update={"event_log": new_log})

        case _ as unreachable:
            assert_never(unreachable)
