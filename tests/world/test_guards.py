import pytest
from pydantic import TypeAdapter, ValidationError

from if_fun.ids import ItemId, RoomId
from if_fun.world.guards import (
    GlobalFlagEqualsGuard,
    Guard,
    HasItemGuard,
    PlayerInRoomGuard,
    RoomFlagEqualsGuard,
)

GuardAdapter = TypeAdapter(Guard)


def test_guard_discriminates_on_type_field() -> None:
    data = {"type": "has_item", "item_id": "brass_key"}
    g = GuardAdapter.validate_python(data)
    assert isinstance(g, HasItemGuard)
    assert g.item_id == ItemId("brass_key")


def test_guard_unknown_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GuardAdapter.validate_python({"type": "hovercraft_full_of_eels"})


def test_all_guard_types_roundtrip() -> None:
    guards: list[Guard] = [
        HasItemGuard(item_id=ItemId("brass_key")),
        PlayerInRoomGuard(room_id=RoomId("entry_hall")),
        RoomFlagEqualsGuard(room_id=RoomId("library"), flag="door_north", value="unlocked"),
        GlobalFlagEqualsGuard(flag="alarm_raised", value=False),
    ]
    for g in guards:
        restored = GuardAdapter.validate_python(g.model_dump())
        assert restored == g
