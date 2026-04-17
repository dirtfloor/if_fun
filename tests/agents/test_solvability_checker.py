from if_fun.agents.solvability_checker import SolvabilityReport, check_solvability
from if_fun.ids import Direction, ItemId, RoomId
from if_fun.world.effects import (
    AddItemToInventoryEffect,
    MovePlayerEffect,
    RemoveItemFromRoomEffect,
    SetGlobalFlagEffect,
)
from if_fun.world.guards import HasItemGuard, PlayerInRoomGuard
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState
from if_fun.world.state import WinCondition, WorldState
from if_fun.world.transitions import DirectionTrigger, Transition, VerbObjectTrigger


def _solvable_world() -> WorldState:
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
        name="unlock and move north",
        trigger=DirectionTrigger(direction=Direction.NORTH),
        guards=[HasItemGuard(item_id=ItemId("brass_key"))],
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
        win_condition=WinCondition(
            kind="global_flag_equals", args={"flag": "entered_library", "value": True}
        ),
    )


def _unsolvable_world() -> WorldState:
    go_north = Transition(
        id="go_north",
        name="move north",
        trigger=DirectionTrigger(direction=Direction.NORTH),
        guards=[HasItemGuard(item_id=ItemId("brass_key"))],
        effects=[
            MovePlayerEffect(room_id=RoomId("library")),
            SetGlobalFlagEffect(flag="entered_library", value=True),
        ],
    )
    return WorldState(
        rooms={
            RoomId("entry_hall"): RoomState(
                id=RoomId("entry_hall"),
                description="Locked hall.",
                exits={},
                transitions=(go_north,),
            ),
            RoomId("library"): RoomState(
                id=RoomId("library"),
                description="Unreachable.",
            ),
        },
        player=PlayerState(location=RoomId("entry_hall")),
        win_condition=WinCondition(
            kind="global_flag_equals", args={"flag": "entered_library", "value": True}
        ),
    )


def test_solvable_world_reports_shortest_trace() -> None:
    report = check_solvability(_solvable_world())
    assert isinstance(report, SolvabilityReport)
    assert report.solvable
    assert report.winning_trace == ("take_key", "go_north")
    assert report.states_explored >= 2


def test_unsolvable_world_reports_false_with_trace_none() -> None:
    report = check_solvability(_unsolvable_world())
    assert not report.solvable
    assert report.winning_trace is None


def test_max_states_triggers_timeout_result() -> None:
    report = check_solvability(_solvable_world(), max_states=1)
    assert report.timed_out
    assert not report.solvable
