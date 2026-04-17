import pytest
from pydantic import ValidationError

from if_fun.ids import ItemId, RoomId
from if_fun.world.player import PlayerState


def test_player_default_flags_and_inventory_are_empty() -> None:
    p = PlayerState(location=RoomId("entry_hall"))
    assert p.location == "entry_hall"
    assert p.inventory == set()
    assert p.flags == {}


def test_player_holds_items() -> None:
    p = PlayerState(
        location=RoomId("entry_hall"),
        inventory=frozenset({ItemId("brass_key"), ItemId("lantern")}),
    )
    assert ItemId("brass_key") in p.inventory
    assert ItemId("lantern") in p.inventory


def test_player_roundtrips_through_json() -> None:
    p = PlayerState(
        location=RoomId("library"),
        inventory=frozenset({ItemId("scroll")}),
        flags={"torch_lit": True},
    )
    restored = PlayerState.model_validate_json(p.model_dump_json())
    assert restored == p


def test_player_coerces_plain_set_to_frozenset() -> None:
    p = PlayerState(
        location=RoomId("entry_hall"),
        inventory={ItemId("brass_key"), ItemId("lantern")},  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    )
    assert isinstance(p.inventory, frozenset)


def test_player_fields_are_immutable_after_construction() -> None:
    p = PlayerState(location=RoomId("entry_hall"))
    with pytest.raises(ValidationError):
        p.location = RoomId("other_room")  # type: ignore[misc]
