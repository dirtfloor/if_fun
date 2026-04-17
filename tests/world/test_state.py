from if_fun.ids import EventId, ItemId, RoomId
from if_fun.world.events import Event, EventKind
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState
from if_fun.world.state import WinCondition, WorldState


def _minimal_world() -> WorldState:
    return WorldState(
        rooms={
            RoomId("entry_hall"): RoomState(
                id=RoomId("entry_hall"),
                description="A dim stone hallway.",
            ),
        },
        player=PlayerState(location=RoomId("entry_hall")),
        globals={},
        turn=0,
        event_log=[],
        win_condition=WinCondition(
            kind="player_in_room",
            args={"room_id": "entry_hall"},
        ),
        schema_version=1,
    )


def test_world_roundtrips_through_json() -> None:
    w = _minimal_world()
    restored = WorldState.model_validate_json(w.model_dump_json())
    assert restored == w


def test_world_event_log_preserves_order() -> None:
    w = _minimal_world().model_copy(
        update={
            "event_log": [
                Event(id=EventId("evt_001"), turn=0, kind=EventKind.PLAYER_MOVED, payload={}),
                Event(id=EventId("evt_002"), turn=1, kind=EventKind.ITEM_TAKEN, payload={}),
            ]
        }
    )
    restored = WorldState.model_validate_json(w.model_dump_json())
    assert [e.id for e in restored.event_log] == ["evt_001", "evt_002"]


def test_win_condition_player_in_room() -> None:
    wc = WinCondition(kind="player_in_room", args={"room_id": "treasury"})
    w = _minimal_world().model_copy(update={"win_condition": wc})
    assert not w.is_won()  # player starts in entry_hall, not treasury

    w2 = w.model_copy(update={"player": PlayerState(location=RoomId("treasury"))})
    assert w2.is_won()


def test_win_condition_global_flag_equals() -> None:
    wc = WinCondition(kind="global_flag_equals", args={"flag": "crystal_recovered", "value": True})
    w = _minimal_world().model_copy(update={"win_condition": wc})
    assert not w.is_won()
    w2 = w.model_copy(update={"globals": {"crystal_recovered": True}})
    assert w2.is_won()


def test_win_condition_has_item() -> None:
    wc = WinCondition(kind="has_item", args={"item_id": "crystal_shard"})
    w = _minimal_world().model_copy(update={"win_condition": wc})
    assert not w.is_won()
    w2 = w.model_copy(
        update={
            "player": PlayerState(
                location=RoomId("entry_hall"),
                inventory=frozenset({ItemId("crystal_shard")}),
            )
        }
    )
    assert w2.is_won()
