import pytest
from pydantic import TypeAdapter, ValidationError

from if_fun.ids import Direction, EventId, ItemId, RoomId
from if_fun.world.effects import EmitEventEffect, MovePlayerEffect
from if_fun.world.events import EventKind
from if_fun.world.guards import HasItemGuard, PlayerInRoomGuard
from if_fun.world.transitions import (
    Action,
    DirectionTrigger,
    TimeTrigger,
    Transition,
    Trigger,
    VerbObjectTrigger,
)

TriggerAdapter = TypeAdapter(Trigger)


def test_trigger_discriminates_on_type_field() -> None:
    t = TriggerAdapter.validate_python({"type": "direction", "direction": "north"})
    assert isinstance(t, DirectionTrigger)
    assert t.direction is Direction.NORTH


def test_unknown_trigger_rejected() -> None:
    with pytest.raises(ValidationError):
        TriggerAdapter.validate_python({"type": "smoke_signal"})


def test_action_equality_is_by_value() -> None:
    a = Action(verb="take", direct_object=ItemId("brass_key"))
    b = Action(verb="take", direct_object=ItemId("brass_key"))
    assert a == b


def test_transition_minimal_roundtrip() -> None:
    tr = Transition(
        id="move_hall_to_library",
        name="move north",
        trigger=DirectionTrigger(direction=Direction.NORTH),
        guards=[PlayerInRoomGuard(room_id=RoomId("entry_hall"))],
        effects=[MovePlayerEffect(room_id=RoomId("library"))],
        narration_hint="You step north.",
    )
    restored = Transition.model_validate_json(tr.model_dump_json())
    assert restored == tr


def test_time_trigger_validates_positive_period() -> None:
    assert TimeTrigger(period=1).period == 1
    with pytest.raises(ValidationError):
        TimeTrigger(period=0)


def test_transition_rejects_empty_effects_list() -> None:
    with pytest.raises(ValidationError):
        Transition(
            id="noop",
            name="no-op",
            trigger=DirectionTrigger(direction=Direction.NORTH),
            effects=[],
        )


def test_transition_complex_roundtrip_with_verb_object_trigger() -> None:
    tr = Transition(
        id="take_key",
        name="take brass key",
        trigger=VerbObjectTrigger(verb="take", direct_object=ItemId("brass_key")),
        guards=[
            PlayerInRoomGuard(room_id=RoomId("entry_hall")),
            HasItemGuard(item_id=ItemId("lantern")),
        ],
        effects=[
            MovePlayerEffect(room_id=RoomId("entry_hall")),
            EmitEventEffect(
                event_id=EventId("evt_take_key"),
                kind=EventKind.ITEM_TAKEN,
                payload={"item": "brass_key"},
            ),
        ],
        narration_hint="You take the brass key.",
    )
    restored = Transition.model_validate_json(tr.model_dump_json())
    assert restored == tr
