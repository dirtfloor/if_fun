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
