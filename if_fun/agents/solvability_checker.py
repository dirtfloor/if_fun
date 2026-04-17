"""BFS model checker over the composed WorldState machine."""

import time
from collections import deque
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from if_fun.ids import Direction
from if_fun.world.state import WorldState
from if_fun.world.store import (
    IllegalAction,
    apply_transition,
    find_direction_transition,
    legal_transitions,
)
from if_fun.world.transitions import Transition


class SolvabilityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    solvable: bool
    winning_trace: tuple[str, ...] | None
    states_explored: int
    timed_out: bool


def _candidate_transitions(world: WorldState) -> Iterable[Transition]:
    yield from legal_transitions(world)
    # Implicit direction moves: bare exits without a declared DirectionTrigger.
    # legal_transitions already yielded any explicit DirectionTrigger transitions,
    # so gate on the synthetic id prefix to avoid double-yielding.
    for direction in Direction:
        tr = find_direction_transition(world, direction)
        if tr is None:
            continue
        if tr.id.startswith("_implicit_move_"):
            yield tr


def _fingerprint(world: WorldState) -> str:
    # event_log and turn are bookkeeping; two states that differ only in those
    # fields are equivalent for reachability purposes.
    return world.model_dump_json(exclude={"event_log", "turn"})


def check_solvability(
    world: WorldState,
    *,
    max_states: int = 50_000,
    timeout_seconds: float = 60.0,
) -> SolvabilityReport:
    if world.is_won():
        return SolvabilityReport(
            solvable=True, winning_trace=(), states_explored=1, timed_out=False
        )

    start_fp = _fingerprint(world)
    queue: deque[tuple[WorldState, tuple[str, ...]]] = deque([(world, ())])
    seen: dict[str, tuple[str, ...]] = {start_fp: ()}
    started = time.monotonic()

    while queue:
        if len(seen) >= max_states:
            return SolvabilityReport(
                solvable=False, winning_trace=None, states_explored=len(seen), timed_out=True
            )
        if time.monotonic() - started > timeout_seconds:
            return SolvabilityReport(
                solvable=False, winning_trace=None, states_explored=len(seen), timed_out=True
            )

        state, trace = queue.popleft()

        for tr in _candidate_transitions(state):
            try:
                next_state = apply_transition(state, tr)
            except IllegalAction:
                continue
            fp = _fingerprint(next_state)
            if fp in seen:
                continue
            next_trace = (*trace, tr.id)
            if next_state.is_won():
                return SolvabilityReport(
                    solvable=True,
                    winning_trace=next_trace,
                    states_explored=len(seen) + 1,
                    timed_out=False,
                )
            seen[fp] = next_trace
            queue.append((next_state, next_trace))

    return SolvabilityReport(
        solvable=False, winning_trace=None, states_explored=len(seen), timed_out=False
    )
