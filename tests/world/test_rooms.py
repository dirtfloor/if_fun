from if_fun.ids import Direction, ItemId, RoomId
from if_fun.world.effects import AddItemToInventoryEffect, RemoveItemFromRoomEffect
from if_fun.world.guards import PlayerInRoomGuard
from if_fun.world.rooms import RoomState
from if_fun.world.transitions import Transition, VerbObjectTrigger


def test_room_defaults_are_empty() -> None:
    r = RoomState(
        id=RoomId("entry_hall"),
        description="A dim stone hallway.",
    )
    assert r.items_present == frozenset()
    assert r.occupants == frozenset()
    assert r.event_ids == ()
    assert r.flags == {}
    assert r.exits == {}
    assert r.transitions == ()
    assert r.visited is False


def test_room_with_exits_and_transitions() -> None:
    r = RoomState(
        id=RoomId("entry_hall"),
        description="A dim stone hallway.",
        exits={Direction.NORTH: RoomId("library")},
        items_present=frozenset({ItemId("brass_key")}),
        transitions=(
            Transition(
                id="take_key",
                name="take brass key",
                trigger=VerbObjectTrigger(verb="take", direct_object=ItemId("brass_key")),
                guards=[PlayerInRoomGuard(room_id=RoomId("entry_hall"))],
                effects=[
                    RemoveItemFromRoomEffect(
                        room_id=RoomId("entry_hall"), item_id=ItemId("brass_key")
                    ),
                    AddItemToInventoryEffect(item_id=ItemId("brass_key")),
                ],
            ),
        ),
    )
    restored = RoomState.model_validate_json(r.model_dump_json())
    assert restored == r
