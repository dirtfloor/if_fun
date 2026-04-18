"""StateStore service: matches actions to transitions, applies them purely."""

from enum import Enum

from if_fun.ids import Direction, EventId
from if_fun.world.effects import MovePlayerEffect
from if_fun.world.effects import apply as apply_effect
from if_fun.world.events import Event, EventKind
from if_fun.world.guards import evaluate as evaluate_guard
from if_fun.world.state import WorldState
from if_fun.world.transitions import Action, DirectionTrigger, Transition, VerbObjectTrigger


class IllegalAction(Exception):
    """Raised when an action does not match a legal transition in the current state."""


class DirectionStatus(Enum):
    OPEN = "open"
    LOCKED = "locked"
    WALL = "wall"


def classify_direction(world: WorldState, direction: Direction) -> DirectionStatus:
    """Return whether ``direction`` is traversable from the player's current room.

    OPEN   — a bare exit with no guarded transition, or a guarded transition
             whose guards all currently pass.
    LOCKED — a DirectionTrigger transition exists but at least one of its
             guards fails in the current world state.
    WALL   — neither a bare exit nor any DirectionTrigger transition exists
             for this direction.
    """
    room = world.rooms[world.player.location]
    for tr in room.transitions:
        if isinstance(tr.trigger, DirectionTrigger) and tr.trigger.direction is direction:
            if all(evaluate_guard(g, world) for g in tr.guards):
                return DirectionStatus.OPEN
            return DirectionStatus.LOCKED
    if direction in room.exits:
        return DirectionStatus.OPEN
    return DirectionStatus.WALL


def find_transition(world: WorldState, action: Action) -> Transition | None:
    """Match a verb-object action to a transition in the player's current room."""
    room = world.rooms[world.player.location]
    for tr in room.transitions:
        if (
            isinstance(tr.trigger, VerbObjectTrigger)
            and tr.trigger.verb == action.verb
            and tr.trigger.direct_object == action.direct_object
        ):
            return tr
    return None


def find_direction_transition(world: WorldState, direction: Direction) -> Transition | None:
    """Match a direction to a transition in the player's current room.

    An explicit DirectionTrigger transition takes precedence over a bare exit:
    if a room defines both, the explicit (possibly guarded) transition is
    returned and the bare-exit fallback is never reached.
    """
    room = world.rooms[world.player.location]
    for tr in room.transitions:
        if isinstance(tr.trigger, DirectionTrigger) and tr.trigger.direction is direction:
            return tr
    # Fallback: a bare exit with no guarded transition becomes a free MovePlayerEffect.
    if direction in room.exits:
        return Transition(
            id=f"_implicit_move_{direction.value}",
            name=f"move {direction.value}",
            trigger=DirectionTrigger(direction=direction),
            guards=[],
            effects=[MovePlayerEffect(room_id=room.exits[direction])],
        )
    return None


def legal_transitions(world: WorldState) -> list[Transition]:
    """All transitions in the current room whose guards pass. Does not include implicit moves."""
    room = world.rooms[world.player.location]
    return [tr for tr in room.transitions if all(evaluate_guard(g, world) for g in tr.guards)]


def apply_transition(world: WorldState, transition: Transition) -> WorldState:
    """Return a new WorldState with ``transition`` applied. Raises IllegalAction if guards fail."""
    for g in transition.guards:
        if not evaluate_guard(g, world):
            raise IllegalAction(f"guard failed for transition {transition.id!r}: {g!r}")

    new_world = world
    for eff in transition.effects:
        new_world = apply_effect(eff, new_world)

    next_turn = new_world.turn + 1
    marker = Event(
        id=EventId(f"evt_t{next_turn:06d}_{transition.id}"),
        turn=next_turn,
        kind=EventKind.TRANSITION_APPLIED,
        payload={"transition_id": transition.id},
    )
    return new_world.model_copy(
        update={
            "turn": next_turn,
            "event_log": [*new_world.event_log, marker],
        }
    )


def apply_action(world: WorldState, action: Action) -> WorldState:
    """Find and apply a verb-object transition. Raises IllegalAction if none matches."""
    tr = find_transition(world, action)
    if tr is None:
        raise IllegalAction(f"no transition matches action: {action!r}")
    return apply_transition(world, tr)


def apply_direction(world: WorldState, direction: Direction) -> WorldState:
    """Find and apply a direction transition. Raises IllegalAction if no exit or transition."""
    tr = find_direction_transition(world, direction)
    if tr is None:
        raise IllegalAction(
            f"no exit or transition {direction.value} from {world.player.location!r}"
        )
    return apply_transition(world, tr)
