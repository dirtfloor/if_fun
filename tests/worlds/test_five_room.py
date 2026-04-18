from if_fun.agents.map_verifier import verify_map
from if_fun.agents.solvability_checker import check_solvability
from if_fun.ids import ItemId, RoomId
from if_fun.worlds.five_room import build_five_room_world


def test_five_room_world_has_five_rooms() -> None:
    w = build_five_room_world()
    assert len(w.rooms) == 5


def test_five_room_world_map_is_valid() -> None:
    w = build_five_room_world()
    verdict = verify_map(w)
    assert verdict.ok, verdict.issues


def test_five_room_world_is_solvable() -> None:
    w = build_five_room_world()
    report = check_solvability(w)
    assert report.solvable
    assert report.winning_trace is not None
    assert len(report.winning_trace) >= 5  # non-trivial puzzle chain


def test_five_room_world_starts_in_entry_hall() -> None:
    w = build_five_room_world()
    assert w.player.location == RoomId("entry_hall")


def test_five_room_world_has_brass_key_in_vault() -> None:
    w = build_five_room_world()
    vault = w.rooms[RoomId("vault")]
    assert ItemId("brass_key") in vault.items_present


def test_five_room_descriptions_do_not_mention_movable_items() -> None:
    """Room prose must not reference items that can be moved.

    The items registry renders item presence in the Items: line, so prose
    that hard-codes "the brass key rests on a plinth" goes stale the moment
    the player takes it. Guard against regressions by checking each room's
    description against each moveable item's display name and id.
    """
    w = build_five_room_world()
    movable = {it.id for it in w.items.values()}
    for room in w.rooms.values():
        desc = room.description.lower()
        for item_id in movable:
            assert item_id not in desc, f"room {room.id} prose mentions id {item_id}"
            definition = w.items[item_id]
            assert definition.display_name.lower() not in desc, (
                f"room {room.id} prose mentions display_name {definition.display_name!r}"
            )
