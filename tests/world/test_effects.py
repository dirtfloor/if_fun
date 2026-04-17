import pytest
from pydantic import TypeAdapter, ValidationError

from if_fun.ids import EventId, ItemId, RoomId
from if_fun.world.effects import (
    AddItemToInventoryEffect,
    Effect,
    EmitEventEffect,
    MovePlayerEffect,
    RemoveItemFromRoomEffect,
    SetGlobalFlagEffect,
    SetRoomFlagEffect,
)
from if_fun.world.events import EventKind

EffectAdapter = TypeAdapter(Effect)


def test_effect_discriminates_on_type_field() -> None:
    data = {"type": "move_player", "room_id": "library"}
    e = EffectAdapter.validate_python(data)
    assert isinstance(e, MovePlayerEffect)
    assert e.room_id == RoomId("library")


def test_effect_unknown_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EffectAdapter.validate_python({"type": "rain_toads"})


def test_all_effect_types_roundtrip() -> None:
    effects: list[Effect] = [
        MovePlayerEffect(room_id=RoomId("library")),
        AddItemToInventoryEffect(item_id=ItemId("scroll")),
        RemoveItemFromRoomEffect(room_id=RoomId("library"), item_id=ItemId("scroll")),
        SetRoomFlagEffect(room_id=RoomId("entry_hall"), flag="door_north", value="unlocked"),
        SetGlobalFlagEffect(flag="alarm_raised", value=True),
        EmitEventEffect(
            event_id=EventId("evt_manual"),
            kind=EventKind.TRANSITION_APPLIED,
            payload={"note": "manual"},
        ),
    ]
    for e in effects:
        restored = EffectAdapter.validate_python(e.model_dump())
        assert restored == e
