import pytest
from pydantic import ValidationError

from if_fun.ids import EventId
from if_fun.world.events import Event, EventKind


def test_event_roundtrips_through_json() -> None:
    ev = Event(
        id=EventId("evt_0001"),
        turn=3,
        kind=EventKind.TRANSITION_APPLIED,
        payload={"transition_id": "unlock_north_door"},
    )
    restored = Event.model_validate_json(ev.model_dump_json())
    assert restored == ev


def test_event_turn_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        Event(
            id=EventId("evt_0002"),
            turn=-1,
            kind=EventKind.PLAYER_MOVED,
            payload={},
        )


def test_event_kind_enum_values_are_stable() -> None:
    # Treat these string values as a contract — saves depend on them.
    assert EventKind.TRANSITION_APPLIED.value == "transition_applied"
    assert EventKind.PLAYER_MOVED.value == "player_moved"
    assert EventKind.ITEM_TAKEN.value == "item_taken"
    assert EventKind.ITEM_DROPPED.value == "item_dropped"
    assert EventKind.ROOM_FLAG_CHANGED.value == "room_flag_changed"
    assert EventKind.GLOBAL_FLAG_CHANGED.value == "global_flag_changed"
