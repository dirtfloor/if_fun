"""Tests for ItemDef and its registry on WorldState.

ItemDef is a Phase A minimal schema: id, display_name, article,
short_description. The display layer uses it to render item names; examine
uses short_description. Phase B's generator will populate these fields;
Phase A's five_room world registers them by hand.
"""

import pytest
from pydantic import ValidationError

from if_fun.ids import ItemId, RoomId
from if_fun.world.items import ItemDef
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState
from if_fun.world.state import WinCondition, WorldState


def test_item_def_has_required_fields() -> None:
    it = ItemDef(
        id=ItemId("brass_key"),
        display_name="brass key",
        article="a",
        short_description="A tarnished brass key.",
    )
    assert it.id == "brass_key"
    assert it.display_name == "brass key"
    assert it.article == "a"


def test_item_def_is_frozen() -> None:
    it = ItemDef(
        id=ItemId("brass_key"),
        display_name="brass key",
        article="a",
        short_description="x",
    )
    with pytest.raises(ValidationError):
        it.display_name = "silver key"  # type: ignore[misc]


def test_item_def_rejects_mismatched_article() -> None:
    # article must be one of the common English articles; anything else rejected.
    with pytest.raises(ValidationError):
        ItemDef(
            id=ItemId("brass_key"),
            display_name="brass key",
            article="la",  # ty: ignore[invalid-argument-type]
            short_description="x",
        )


def test_world_state_carries_item_registry() -> None:
    room = RoomState(id=RoomId("here"), description="Here.")
    brass = ItemDef(
        id=ItemId("brass_key"),
        display_name="brass key",
        article="a",
        short_description="A tarnished brass key.",
    )
    w = WorldState(
        rooms={RoomId("here"): room},
        player=PlayerState(location=RoomId("here")),
        items={ItemId("brass_key"): brass},
        win_condition=WinCondition(kind="player_in_room", args={"room_id": "here"}),
    )
    assert w.items[ItemId("brass_key")].display_name == "brass key"


def test_world_state_items_defaults_to_empty() -> None:
    room = RoomState(id=RoomId("here"), description="Here.")
    w = WorldState(
        rooms={RoomId("here"): room},
        player=PlayerState(location=RoomId("here")),
        win_condition=WinCondition(kind="player_in_room", args={"room_id": "here"}),
    )
    assert w.items == {}


def test_world_state_items_roundtrip_json() -> None:
    room = RoomState(id=RoomId("here"), description="Here.")
    brass = ItemDef(
        id=ItemId("brass_key"),
        display_name="brass key",
        article="a",
        short_description="A tarnished brass key.",
    )
    w = WorldState(
        rooms={RoomId("here"): room},
        player=PlayerState(location=RoomId("here")),
        items={ItemId("brass_key"): brass},
        win_condition=WinCondition(kind="player_in_room", args={"room_id": "here"}),
    )
    raw = w.model_dump_json()
    w2 = WorldState.model_validate_json(raw)
    assert w2.items[ItemId("brass_key")] == brass
