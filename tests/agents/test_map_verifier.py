from if_fun.agents.map_verifier import verify_map
from if_fun.ids import Direction, RoomId
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState
from if_fun.world.state import WinCondition, WorldState


def _rooms(*pairs: tuple[str, dict[Direction, str]]) -> dict[RoomId, RoomState]:
    return {
        RoomId(rid): RoomState(
            id=RoomId(rid),
            description=f"Room {rid}.",
            exits={d: RoomId(target) for d, target in exits.items()},
        )
        for rid, exits in pairs
    }


def _world(rooms: dict[RoomId, RoomState], start: str = "a") -> WorldState:
    return WorldState(
        rooms=rooms,
        player=PlayerState(location=RoomId(start)),
        win_condition=WinCondition(kind="player_in_room", args={"room_id": start}),
    )


def test_connected_two_room_map_passes() -> None:
    rooms = _rooms(
        ("a", {Direction.NORTH: "b"}),
        ("b", {Direction.SOUTH: "a"}),
    )
    verdict = verify_map(_world(rooms))
    assert verdict.ok
    assert verdict.issues == ()


def test_orphan_room_flagged() -> None:
    rooms = _rooms(
        ("a", {Direction.NORTH: "b"}),
        ("b", {Direction.SOUTH: "a"}),
        ("c", {}),  # unreachable from a
    )
    verdict = verify_map(_world(rooms))
    assert not verdict.ok
    assert any("unreachable" in issue for issue in verdict.issues)


def test_orphan_exit_flagged() -> None:
    rooms = _rooms(
        ("a", {Direction.NORTH: "phantom"}),  # 'phantom' not a real room
    )
    verdict = verify_map(_world(rooms))
    assert not verdict.ok
    assert any("unknown target" in issue for issue in verdict.issues)


def test_geometry_asymmetry_flagged() -> None:
    rooms = _rooms(
        ("a", {Direction.NORTH: "b"}),
        ("b", {}),  # missing the expected SOUTH back to a
    )
    verdict = verify_map(_world(rooms))
    assert not verdict.ok
    assert any("asymmetric" in issue for issue in verdict.issues)


def test_empty_map_flagged() -> None:
    verdict = verify_map(
        WorldState(
            rooms={},
            player=PlayerState(location=RoomId("nowhere")),
            win_condition=WinCondition(kind="player_in_room", args={"room_id": "nowhere"}),
        )
    )
    assert not verdict.ok
    assert verdict.issues == ("map has no rooms",)
