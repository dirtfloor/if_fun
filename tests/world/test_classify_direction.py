"""Tests for classify_direction: OPEN / LOCKED / WALL classification.

classify_direction is the single source of truth for whether a direction is
traversable from the current room. Both the room renderer (for the Exits: line)
and the turn engine (for blocked-move messaging + open/unlock verbs) rely on it.
"""

from if_fun.ids import Direction, ItemId, RoomId
from if_fun.world.effects import MovePlayerEffect
from if_fun.world.guards import HasItemGuard
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState
from if_fun.world.state import WinCondition, WorldState
from if_fun.world.store import DirectionStatus, classify_direction
from if_fun.world.transitions import DirectionTrigger, Transition


def _world_with(
    current: RoomState, *rest: RoomState, inventory: frozenset[ItemId] = frozenset()
) -> WorldState:
    rooms = {r.id: r for r in (current, *rest)}
    return WorldState(
        rooms=rooms,
        player=PlayerState(location=current.id, inventory=inventory),
        win_condition=WinCondition(kind="player_in_room", args={"room_id": "nowhere"}),
    )


def test_classify_direction_returns_wall_when_no_exit_or_transition() -> None:
    room = RoomState(id=RoomId("cell"), description="A dead end.")
    w = _world_with(room)

    assert classify_direction(w, Direction.NORTH) is DirectionStatus.WALL


def test_classify_direction_returns_open_for_bare_exit() -> None:
    here = RoomState(
        id=RoomId("here"),
        description="Here.",
        exits={Direction.NORTH: RoomId("there")},
    )
    there = RoomState(id=RoomId("there"), description="There.")
    w = _world_with(here, there)

    assert classify_direction(w, Direction.NORTH) is DirectionStatus.OPEN


def test_classify_direction_returns_locked_when_guarded_transition_fails() -> None:
    locked = Transition(
        id="go_north",
        name="move north",
        trigger=DirectionTrigger(direction=Direction.NORTH),
        guards=[HasItemGuard(item_id=ItemId("brass_key"))],
        effects=[MovePlayerEffect(room_id=RoomId("there"))],
    )
    here = RoomState(
        id=RoomId("here"),
        description="Here.",
        exits={Direction.NORTH: RoomId("there")},
        transitions=(locked,),
    )
    there = RoomState(id=RoomId("there"), description="There.")
    w = _world_with(here, there)  # no key

    assert classify_direction(w, Direction.NORTH) is DirectionStatus.LOCKED


def test_classify_direction_returns_open_when_guarded_transition_passes() -> None:
    locked = Transition(
        id="go_north",
        name="move north",
        trigger=DirectionTrigger(direction=Direction.NORTH),
        guards=[HasItemGuard(item_id=ItemId("brass_key"))],
        effects=[MovePlayerEffect(room_id=RoomId("there"))],
    )
    here = RoomState(
        id=RoomId("here"),
        description="Here.",
        exits={Direction.NORTH: RoomId("there")},
        transitions=(locked,),
    )
    there = RoomState(id=RoomId("there"), description="There.")
    w = _world_with(here, there, inventory=frozenset({ItemId("brass_key")}))

    assert classify_direction(w, Direction.NORTH) is DirectionStatus.OPEN


def test_classify_direction_returns_locked_even_without_bare_exit_entry() -> None:
    # A room may declare only the guarded DirectionTrigger (no matching bare exit
    # in the exits dict). The classifier should still see it as a locked door,
    # not a wall, because the intent to connect is encoded in the transition.
    locked = Transition(
        id="go_north",
        name="move north",
        trigger=DirectionTrigger(direction=Direction.NORTH),
        guards=[HasItemGuard(item_id=ItemId("brass_key"))],
        effects=[MovePlayerEffect(room_id=RoomId("there"))],
    )
    here = RoomState(
        id=RoomId("here"),
        description="Here.",
        exits={},  # no bare exit
        transitions=(locked,),
    )
    there = RoomState(id=RoomId("there"), description="There.")
    w = _world_with(here, there)  # no key

    assert classify_direction(w, Direction.NORTH) is DirectionStatus.LOCKED
