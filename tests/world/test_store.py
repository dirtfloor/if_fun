"""Tests for the StateStore service."""

import pytest

from if_fun.ids import Direction, ItemId, RoomId
from if_fun.world.effects import (
    AddItemToInventoryEffect,
    MovePlayerEffect,
    RemoveItemFromRoomEffect,
    SetGlobalFlagEffect,
)
from if_fun.world.events import EventKind
from if_fun.world.guards import HasItemGuard, PlayerInRoomGuard
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState
from if_fun.world.state import WinCondition, WorldState
from if_fun.world.store import IllegalAction, apply_action, find_transition, legal_transitions
from if_fun.world.transitions import Action, DirectionTrigger, Transition, VerbObjectTrigger


def _two_room_world() -> WorldState:
    take_key = Transition(
        id="take_key",
        name="take brass key",
        trigger=VerbObjectTrigger(verb="take", direct_object=ItemId("brass_key")),
        guards=[PlayerInRoomGuard(room_id=RoomId("entry_hall"))],
        effects=[
            RemoveItemFromRoomEffect(room_id=RoomId("entry_hall"), item_id=ItemId("brass_key")),
            AddItemToInventoryEffect(item_id=ItemId("brass_key")),
        ],
    )
    go_north = Transition(
        id="go_north",
        name="move north",
        trigger=DirectionTrigger(direction=Direction.NORTH),
        guards=[HasItemGuard(item_id=ItemId("brass_key"))],  # must hold key
        effects=[
            MovePlayerEffect(room_id=RoomId("library")),
            SetGlobalFlagEffect(flag="entered_library", value=True),
        ],
    )

    return WorldState(
        rooms={
            RoomId("entry_hall"): RoomState(
                id=RoomId("entry_hall"),
                description="A dim stone hallway.",
                exits={Direction.NORTH: RoomId("library")},
                items_present=frozenset({ItemId("brass_key")}),
                transitions=(take_key, go_north),
            ),
            RoomId("library"): RoomState(
                id=RoomId("library"),
                description="Dusty shelves.",
                exits={Direction.SOUTH: RoomId("entry_hall")},
            ),
        },
        player=PlayerState(location=RoomId("entry_hall")),
        globals={},
        turn=0,
        win_condition=WinCondition(
            kind="global_flag_equals", args={"flag": "entered_library", "value": True}
        ),
    )


def test_find_transition_for_verb_action() -> None:
    w = _two_room_world()
    a = Action(verb="take", direct_object=ItemId("brass_key"))
    tr = find_transition(w, a)
    assert tr is not None
    assert tr.id == "take_key"


def test_find_transition_for_direction_action() -> None:
    w = _two_room_world()
    from if_fun.world.store import find_direction_transition

    tr = find_direction_transition(w, Direction.NORTH)
    assert tr is not None
    assert tr.id == "go_north"


def test_legal_transitions_respects_guards() -> None:
    w = _two_room_world()
    # Without key, go_north is illegal; take_key is legal.
    legal = legal_transitions(w)
    ids = {tr.id for tr in legal}
    assert "take_key" in ids
    assert "go_north" not in ids


def test_apply_action_take_key_then_move() -> None:
    w = _two_room_world()
    w = apply_action(w, Action(verb="take", direct_object=ItemId("brass_key")))
    assert ItemId("brass_key") in w.player.inventory
    assert ItemId("brass_key") not in w.rooms[RoomId("entry_hall")].items_present

    from if_fun.world.store import apply_direction

    w = apply_direction(w, Direction.NORTH)
    assert w.player.location == RoomId("library")
    assert w.globals["entered_library"] is True
    assert w.is_won()


def test_apply_action_illegal_raises() -> None:
    w = _two_room_world()
    with pytest.raises(IllegalAction):
        from if_fun.world.store import apply_direction

        apply_direction(w, Direction.NORTH)  # no key yet


def test_apply_transition_bumps_turn_and_logs_event() -> None:
    w = _two_room_world()
    w2 = apply_action(w, Action(verb="take", direct_object=ItemId("brass_key")))
    assert w2.turn == w.turn + 1
    kinds = [e.kind for e in w2.event_log]
    assert EventKind.TRANSITION_APPLIED in kinds


def test_apply_action_is_pure() -> None:
    w = _two_room_world()
    before = w.model_dump_json()
    _ = apply_action(w, Action(verb="take", direct_object=ItemId("brass_key")))
    assert w.model_dump_json() == before  # input untouched


def test_find_transition_returns_none_for_unknown_action() -> None:
    w = _two_room_world()
    tr = find_transition(w, Action(verb="open", direct_object=ItemId("door")))
    assert tr is None


def test_find_direction_transition_implicit_fallback_for_bare_exit() -> None:
    # library has exits={Direction.SOUTH: RoomId("entry_hall")} and no transitions.
    from if_fun.world.store import apply_direction, find_direction_transition

    w = _two_room_world().model_copy(update={"player": PlayerState(location=RoomId("library"))})
    tr = find_direction_transition(w, Direction.SOUTH)
    assert tr is not None
    assert tr.id == "_implicit_move_south"
    assert tr.guards == []
    assert tr.effects == [MovePlayerEffect(room_id=RoomId("entry_hall"))]

    # And it is usable via apply_direction.
    w2 = apply_direction(w, Direction.SOUTH)
    assert w2.player.location == RoomId("entry_hall")
