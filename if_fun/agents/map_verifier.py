"""Deterministic map verifier: reachability + geometry consistency."""

from collections import deque
from dataclasses import dataclass, field

from if_fun.ids import RoomId
from if_fun.world.rooms import RoomState
from if_fun.world.state import WorldState


@dataclass(frozen=True)
class MapVerdict:
    ok: bool
    issues: list[str] = field(default_factory=list)


def verify_map(world: WorldState) -> MapVerdict:
    issues: list[str] = []

    if not world.rooms:
        return MapVerdict(ok=False, issues=["map has no rooms"])

    # 1. All exit targets must reference real rooms.
    for rid, room in world.rooms.items():
        for direction, target in room.exits.items():
            if target not in world.rooms:
                issues.append(
                    f"room {rid!r} has exit {direction.value} to unknown target {target!r}"
                )

    # 2. Geometry: A -d-> B implies B -d.opposite()-> A. Phase A treats all
    # exits as two-way; one-way exits are a Phase B concern.
    for rid, room in world.rooms.items():
        for direction, target in room.exits.items():
            if target not in world.rooms:
                continue
            back = world.rooms[target].exits.get(direction.opposite())
            if back != rid:
                issues.append(
                    f"asymmetric exit: {rid!r} -{direction.value}-> {target!r}, "
                    f"but {target!r} -{direction.opposite().value}-> {back!r}"
                )

    # 3. Reachability from player start.
    reachable = _bfs_reachable(world.rooms, world.player.location)
    for rid in world.rooms:
        if rid not in reachable:
            issues.append(f"room {rid!r} is unreachable from start {world.player.location!r}")

    return MapVerdict(ok=not issues, issues=issues)


def _bfs_reachable(rooms: dict[RoomId, RoomState], start: RoomId) -> set[RoomId]:
    visited: set[RoomId] = set()
    if start not in rooms:
        return visited
    queue: deque[RoomId] = deque([start])
    while queue:
        rid = queue.popleft()
        if rid in visited:
            continue
        visited.add(rid)
        for target in rooms[rid].exits.values():
            if target in rooms and target not in visited:
                queue.append(target)
    return visited
