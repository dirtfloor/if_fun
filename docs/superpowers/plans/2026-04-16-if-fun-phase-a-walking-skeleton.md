# if_fun Phase A — Walking Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a deterministic, fully TDD-covered substrate for `if_fun` — state model, parser, save/load, map verification, solvability checking, and a minimal Textual UI that can play a hardcoded 5-room world to completion. **No LLM code in this phase.**

**Architecture:** A composed pydantic state machine (`WorldState` = rooms × player × globals × event log). Transitions are discriminated-union guards and effects over that state. A deterministic parser maps canonical verbs to `Action`s. `StateStore` applies transitions with guard checks. A BFS model checker verifies solvability. The Textual app drives a minimal turn loop over the hardcoded world.

**Tech Stack:** Python 3.12+, `uv`, `pydantic` v2, `textual`, `typer`, `platformdirs`, `pytest`, `ruff`, `ty`, `pre-commit`.

**Package boundary invariant (enforced by a test):** `if_fun/world/`, `if_fun/parser/`, and `if_fun/save/` **must not import** from `if_fun/agents/` or any LLM-calling code. Phase A contains nothing in `agents/` — the two deterministic modules that the spec files under `agents/` (Map Verifier, Solvability Checker) are placed there under the naming convention, and the boundary test explicitly exempts them.

---

## File Structure

Created in this phase:

```
pyproject.toml                              # project config + script entry + ruff/ty/pytest
uv.lock                                     # dependency lock (generated)
.pre-commit-config.yaml                     # ruff format/check + local ty + pytest
.env.example                                # Phase A has no secrets; placeholder for B

if_fun/
  __init__.py
  cli.py                                    # typer entry: `if_fun play`
  ids.py                                    # RoomId, ItemId, MobId, EventId, Direction
  world/
    __init__.py
    events.py                               # Event, EventKind
    player.py                               # PlayerState
    guards.py                               # Guard union + evaluate()
    effects.py                              # Effect union + apply()
    transitions.py                          # Trigger, Action, Transition
    rooms.py                                # RoomState
    state.py                                # WorldState + WinCondition
    store.py                                # StateStore service
  parser/
    __init__.py
    grammar.py                              # canonical verb table + aliases
    parser.py                               # tokenize → Action | ParseError
  save/
    __init__.py
    paths.py                                # platformdirs-based save paths
    save_format.py                          # write_save / read_save
    schema_migrations/
      __init__.py                           # registry; empty for v1
  agents/
    __init__.py
    map_verifier.py                         # deterministic; no LLM calls
    solvability_checker.py                  # deterministic BFS; no LLM calls
  tui/
    __init__.py
    app.py                                  # Textual App: prose pane + input line
    turn_engine.py                          # parser → transition → render (no LLM)
  worlds/
    __init__.py
    five_room.py                            # hardcoded playable test world

tests/
  conftest.py                               # shared fixtures (tmp save dir, five-room world)
  world/
    test_events.py
    test_player.py
    test_guards.py
    test_effects.py
    test_transitions.py
    test_rooms.py
    test_state.py
    test_store.py
  parser/
    test_grammar.py
    test_parser.py
  save/
    test_save_format.py
  agents/
    test_map_verifier.py
    test_solvability_checker.py
  worlds/
    test_five_room.py
  tui/
    test_turn_engine.py
    test_app.py
  architecture/
    test_package_boundaries.py
  e2e/
    test_smoke_five_room.py
```

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.pre-commit-config.yaml`
- Create: `.env.example`
- Create: `if_fun/__init__.py`
- Create: `tests/test_smoke.py` (scaffolding sanity test, removed at end of task)

- [ ] **Step 1: Initialize uv project**

Run:

```bash
uv init --package --name if_fun --no-readme
```

Expected: `pyproject.toml` and `if_fun/__init__.py` created. Delete any generated `main.py` or example code — we'll add our own files.

- [ ] **Step 2: Write `pyproject.toml`**

Overwrite the generated `pyproject.toml` with:

```toml
[project]
name = "if_fun"
version = "0.1.0"
description = "Interactive Fiction game in the Infocom tradition, built as a showcase of agentic AI patterns."
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.7",
    "textual>=0.60",
    "typer>=0.12",
    "platformdirs>=4.2",
]

[project.scripts]
if_fun = "if_fun.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "ty>=0.0.1a1",
    "pre-commit>=3.7",
]

[tool.hatch.build.targets.wheel]
packages = ["if_fun"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF"]
ignore = ["E501"]  # line-too-long is covered by the formatter

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "eval_smoke: small live-LLM eval suite, nightly (Phase B+)",
    "eval_full: full live-LLM eval suite, manual or weekly (Phase B+)",
]
```

- [ ] **Step 3: Create `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10
    hooks:
      - id: ruff-format
      - id: ruff
        args: [--fix]

  - repo: local
    hooks:
      - id: ty
        name: ty type check
        entry: uv run ty check
        language: system
        pass_filenames: false
        types: [python]
      - id: pytest
        name: pytest (deterministic only)
        entry: uv run pytest -q
        language: system
        pass_filenames: false
        types: [python]
```

- [ ] **Step 4: Create `.env.example`**

```
# Phase B+ will require these; placeholder for Phase A:
OPENROUTER_API_KEY=
LANGFUSE_HOST=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

- [ ] **Step 5: Write a scaffolding sanity test**

Create `tests/test_smoke.py`:

```python
"""Sanity check that the test harness and package import work."""

import if_fun


def test_package_imports() -> None:
    assert if_fun.__name__ == "if_fun"
```

- [ ] **Step 6: Install deps and verify tooling**

Run each and check for clean output:

```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest -q
```

Expected: `uv sync` resolves the lockfile; ruff passes; ty passes; pytest collects and passes 1 test. If ty emits warnings about missing stubs for third-party packages, that is acceptable at this stage — we address them if they block real code in later tasks.

- [ ] **Step 7: Install the pre-commit hook**

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Expected: all hooks pass.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock .pre-commit-config.yaml .env.example if_fun/__init__.py tests/test_smoke.py
git commit -m "chore: scaffold Phase A project (uv, ruff, ty, pytest, pre-commit)"
```

---

## Task 2: Core ID types and enums

**Files:**
- Create: `if_fun/ids.py`
- Test: `tests/test_ids.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ids.py`:

```python
from if_fun.ids import Direction, EventId, ItemId, MobId, RoomId


def test_ids_are_distinct_str_subtypes() -> None:
    r = RoomId("entry_hall")
    i = ItemId("brass_key")
    m = MobId("rat")
    e = EventId("evt_0001")
    assert str(r) == "entry_hall"
    assert str(i) == "brass_key"
    assert str(m) == "rat"
    assert str(e) == "evt_0001"


def test_direction_opposite() -> None:
    assert Direction.NORTH.opposite() is Direction.SOUTH
    assert Direction.SOUTH.opposite() is Direction.NORTH
    assert Direction.EAST.opposite() is Direction.WEST
    assert Direction.WEST.opposite() is Direction.EAST
    assert Direction.UP.opposite() is Direction.DOWN
    assert Direction.DOWN.opposite() is Direction.UP


def test_direction_from_token_accepts_full_and_short() -> None:
    assert Direction.from_token("n") is Direction.NORTH
    assert Direction.from_token("NORTH") is Direction.NORTH
    assert Direction.from_token("up") is Direction.UP
    assert Direction.from_token("xyzzy") is None
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_ids.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `if_fun/ids.py`**

```python
"""Typed identifiers and direction enum for the if_fun world."""

from __future__ import annotations

from enum import StrEnum
from typing import NewType

RoomId = NewType("RoomId", str)
ItemId = NewType("ItemId", str)
MobId = NewType("MobId", str)
EventId = NewType("EventId", str)


class Direction(StrEnum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    UP = "up"
    DOWN = "down"

    _OPPOSITES: dict[str, str] = {}  # populated below

    def opposite(self) -> Direction:
        return _OPPOSITES[self]

    @classmethod
    def from_token(cls, token: str) -> Direction | None:
        t = token.strip().lower()
        if t in _TOKEN_TO_DIRECTION:
            return _TOKEN_TO_DIRECTION[t]
        return None


_OPPOSITES: dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
}

_TOKEN_TO_DIRECTION: dict[str, Direction] = {
    "n": Direction.NORTH, "north": Direction.NORTH,
    "s": Direction.SOUTH, "south": Direction.SOUTH,
    "e": Direction.EAST,  "east":  Direction.EAST,
    "w": Direction.WEST,  "west":  Direction.WEST,
    "u": Direction.UP,    "up":    Direction.UP,
    "d": Direction.DOWN,  "down":  Direction.DOWN,
}
```

(The inner `_OPPOSITES: dict[str, str] = {}` class-level line is removed in the final; only the module-level `_OPPOSITES` is used — drop the placeholder so `ty` doesn't flag the unused annotation.)

Final module body (without the placeholder line):

```python
from __future__ import annotations

from enum import StrEnum
from typing import NewType

RoomId = NewType("RoomId", str)
ItemId = NewType("ItemId", str)
MobId = NewType("MobId", str)
EventId = NewType("EventId", str)


class Direction(StrEnum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    UP = "up"
    DOWN = "down"

    def opposite(self) -> "Direction":
        return _OPPOSITES[self]

    @classmethod
    def from_token(cls, token: str) -> "Direction | None":
        return _TOKEN_TO_DIRECTION.get(token.strip().lower())


_OPPOSITES: dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
}

_TOKEN_TO_DIRECTION: dict[str, Direction] = {
    "n": Direction.NORTH, "north": Direction.NORTH,
    "s": Direction.SOUTH, "south": Direction.SOUTH,
    "e": Direction.EAST,  "east":  Direction.EAST,
    "w": Direction.WEST,  "west":  Direction.WEST,
    "u": Direction.UP,    "up":    Direction.UP,
    "d": Direction.DOWN,  "down":  Direction.DOWN,
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_ids.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add if_fun/ids.py tests/test_ids.py
git commit -m "feat(world): add typed IDs and Direction enum"
```

---

## Task 3: Event model

**Files:**
- Create: `if_fun/world/__init__.py` (empty)
- Create: `if_fun/world/events.py`
- Test: `tests/world/test_events.py`
- Create: `tests/world/__init__.py` (empty)

- [ ] **Step 1: Write the failing test**

Create `tests/world/test_events.py`:

```python
import pytest
from pydantic import ValidationError

from if_fun.ids import EventId
from if_fun.world.events import Event, EventKind


def test_event_roundtrips_through_json() -> None:
    ev = Event(
        id=EventId("evt_0001"),
        turn=3,
        kind=EventKind.TRANSITION_APPLIED,
        payload={"transition_id": "unlock_north_door"},
    )
    restored = Event.model_validate_json(ev.model_dump_json())
    assert restored == ev


def test_event_turn_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        Event(
            id=EventId("evt_0002"),
            turn=-1,
            kind=EventKind.PLAYER_MOVED,
            payload={},
        )


def test_event_kind_enum_values_are_stable() -> None:
    # Treat these string values as a contract — saves depend on them.
    assert EventKind.TRANSITION_APPLIED.value == "transition_applied"
    assert EventKind.PLAYER_MOVED.value == "player_moved"
    assert EventKind.ITEM_TAKEN.value == "item_taken"
    assert EventKind.ITEM_DROPPED.value == "item_dropped"
    assert EventKind.ROOM_FLAG_CHANGED.value == "room_flag_changed"
    assert EventKind.GLOBAL_FLAG_CHANGED.value == "global_flag_changed"
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/world/test_events.py -q`
Expected: collection error — module not found.

- [ ] **Step 3: Implement the module**

Create `if_fun/world/__init__.py` as empty. Create `if_fun/world/events.py`:

```python
"""Event records appended to the world event log."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import EventId


class EventKind(StrEnum):
    TRANSITION_APPLIED = "transition_applied"
    PLAYER_MOVED = "player_moved"
    ITEM_TAKEN = "item_taken"
    ITEM_DROPPED = "item_dropped"
    ROOM_FLAG_CHANGED = "room_flag_changed"
    GLOBAL_FLAG_CHANGED = "global_flag_changed"


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: EventId
    turn: int = Field(ge=0)
    kind: EventKind
    payload: dict[str, Any] = Field(default_factory=dict)
```

Also create `tests/world/__init__.py` as empty and `tests/__init__.py` as empty if it does not exist.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/world/test_events.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add if_fun/world tests/world tests/__init__.py
git commit -m "feat(world): add Event model with stable EventKind enum"
```

---

## Task 4: PlayerState

**Files:**
- Create: `if_fun/world/player.py`
- Test: `tests/world/test_player.py`

- [ ] **Step 1: Write the failing test**

Create `tests/world/test_player.py`:

```python
from if_fun.ids import ItemId, RoomId
from if_fun.world.player import PlayerState


def test_player_default_flags_and_inventory_are_empty() -> None:
    p = PlayerState(location=RoomId("entry_hall"))
    assert p.location == "entry_hall"
    assert p.inventory == set()
    assert p.flags == {}


def test_player_holds_items() -> None:
    p = PlayerState(
        location=RoomId("entry_hall"),
        inventory={ItemId("brass_key"), ItemId("lantern")},
    )
    assert ItemId("brass_key") in p.inventory
    assert ItemId("lantern") in p.inventory


def test_player_roundtrips_through_json() -> None:
    p = PlayerState(
        location=RoomId("library"),
        inventory={ItemId("scroll")},
        flags={"torch_lit": True},
    )
    restored = PlayerState.model_validate_json(p.model_dump_json())
    assert restored == p
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/world/test_player.py -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/world/player.py`:

```python
"""Player character state."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import ItemId, RoomId


class PlayerState(BaseModel):
    model_config = ConfigDict(frozen=True)

    location: RoomId
    inventory: frozenset[ItemId] = Field(default_factory=frozenset)
    flags: dict[str, Any] = Field(default_factory=dict)
```

Note: we use `frozenset` because `frozen=True` on the model is violated if we hold a mutable `set`. For round-trip, pydantic serializes frozenset as a JSON array and parses it back.

The test expected `p.inventory == set()`; adjust the test to `p.inventory == frozenset()` OR leave the set literals in the test — a frozenset compares equal to a set of the same elements. Re-run to confirm.

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/world/test_player.py -q`
Expected: 3 passed. If `p.inventory == set()` fails because `frozenset() != set()` — they *do* compare equal in Python, so this should pass. If it does not, change `set()` to `frozenset()` in the test.

- [ ] **Step 5: Commit**

```bash
git add if_fun/world/player.py tests/world/test_player.py
git commit -m "feat(world): add PlayerState model"
```

---

## Task 5: Guards

**Files:**
- Create: `if_fun/world/guards.py`
- Test: `tests/world/test_guards.py`

Guards are pure predicates over `WorldState`. For Phase A we need four guard types:

- `HasItemGuard` — player inventory contains `item_id`
- `PlayerInRoomGuard` — player is in `room_id`
- `RoomFlagEqualsGuard` — `world.rooms[room_id].flags[flag_name] == value`
- `GlobalFlagEqualsGuard` — `world.globals[flag_name] == value`

To evaluate guards we need `WorldState`, but `WorldState` is defined in Task 8. We break the cycle by typing the `evaluate` argument as `"WorldState"` (forward ref) and importing under `TYPE_CHECKING`. The tests for this task use a **minimal stub world** built from `dict`-like access, or we defer guard *tests that require a live WorldState* until after Task 8.

For Task 5 we test *only* the pydantic validation and discrimination, with a placeholder `evaluate` that we re-test in Task 9 against a real `WorldState`.

- [ ] **Step 1: Write the failing test**

Create `tests/world/test_guards.py`:

```python
import pytest
from pydantic import TypeAdapter, ValidationError

from if_fun.ids import ItemId, RoomId
from if_fun.world.guards import (
    Guard,
    GlobalFlagEqualsGuard,
    HasItemGuard,
    PlayerInRoomGuard,
    RoomFlagEqualsGuard,
)


GuardAdapter = TypeAdapter(Guard)


def test_guard_discriminates_on_type_field() -> None:
    data = {"type": "has_item", "item_id": "brass_key"}
    g = GuardAdapter.validate_python(data)
    assert isinstance(g, HasItemGuard)
    assert g.item_id == ItemId("brass_key")


def test_guard_unknown_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GuardAdapter.validate_python({"type": "hovercraft_full_of_eels"})


def test_all_guard_types_roundtrip() -> None:
    guards: list[Guard] = [
        HasItemGuard(item_id=ItemId("brass_key")),
        PlayerInRoomGuard(room_id=RoomId("entry_hall")),
        RoomFlagEqualsGuard(room_id=RoomId("library"), flag="door_north", value="unlocked"),
        GlobalFlagEqualsGuard(flag="alarm_raised", value=False),
    ]
    for g in guards:
        restored = GuardAdapter.validate_python(g.model_dump())
        assert restored == g
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/world/test_guards.py -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/world/guards.py`:

```python
"""Guard predicates for transitions. Pure; no I/O."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import ItemId, RoomId

if TYPE_CHECKING:
    from if_fun.world.state import WorldState


class _GuardBase(BaseModel):
    model_config = ConfigDict(frozen=True)


class HasItemGuard(_GuardBase):
    type: Literal["has_item"] = "has_item"
    item_id: ItemId


class PlayerInRoomGuard(_GuardBase):
    type: Literal["player_in_room"] = "player_in_room"
    room_id: RoomId


class RoomFlagEqualsGuard(_GuardBase):
    type: Literal["room_flag_equals"] = "room_flag_equals"
    room_id: RoomId
    flag: str
    value: Any


class GlobalFlagEqualsGuard(_GuardBase):
    type: Literal["global_flag_equals"] = "global_flag_equals"
    flag: str
    value: Any


Guard = Annotated[
    Union[HasItemGuard, PlayerInRoomGuard, RoomFlagEqualsGuard, GlobalFlagEqualsGuard],
    Field(discriminator="type"),
]


def evaluate(guard: Guard, world: "WorldState") -> bool:
    match guard:
        case HasItemGuard(item_id=item_id):
            return item_id in world.player.inventory
        case PlayerInRoomGuard(room_id=room_id):
            return world.player.location == room_id
        case RoomFlagEqualsGuard(room_id=room_id, flag=flag, value=value):
            room = world.rooms.get(room_id)
            return room is not None and room.flags.get(flag) == value
        case GlobalFlagEqualsGuard(flag=flag, value=value):
            return world.globals.get(flag) == value
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/world/test_guards.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add if_fun/world/guards.py tests/world/test_guards.py
git commit -m "feat(world): add Guard discriminated union and pure evaluator"
```

---

## Task 6: Effects

**Files:**
- Create: `if_fun/world/effects.py`
- Test: `tests/world/test_effects.py`

Effects are pure functions over `WorldState` that return a new `WorldState`. Since `WorldState` lands in Task 8, we again use forward references and defer behavioural testing to Task 9's StateStore. In Task 6 we test **schema discrimination and roundtrip** only.

- [ ] **Step 1: Write the failing test**

Create `tests/world/test_effects.py`:

```python
import pytest
from pydantic import TypeAdapter, ValidationError

from if_fun.ids import EventId, ItemId, RoomId
from if_fun.world.effects import (
    AddItemToInventoryEffect,
    Effect,
    EmitEventEffect,
    MovePlayerEffect,
    RemoveItemFromRoomEffect,
    SetGlobalFlagEffect,
    SetRoomFlagEffect,
)
from if_fun.world.events import EventKind

EffectAdapter = TypeAdapter(Effect)


def test_effect_discriminates_on_type_field() -> None:
    data = {"type": "move_player", "room_id": "library"}
    e = EffectAdapter.validate_python(data)
    assert isinstance(e, MovePlayerEffect)
    assert e.room_id == RoomId("library")


def test_effect_unknown_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EffectAdapter.validate_python({"type": "rain_toads"})


def test_all_effect_types_roundtrip() -> None:
    effects: list[Effect] = [
        MovePlayerEffect(room_id=RoomId("library")),
        AddItemToInventoryEffect(item_id=ItemId("scroll")),
        RemoveItemFromRoomEffect(room_id=RoomId("library"), item_id=ItemId("scroll")),
        SetRoomFlagEffect(room_id=RoomId("entry_hall"), flag="door_north", value="unlocked"),
        SetGlobalFlagEffect(flag="alarm_raised", value=True),
        EmitEventEffect(
            event_id=EventId("evt_manual"),
            kind=EventKind.TRANSITION_APPLIED,
            payload={"note": "manual"},
        ),
    ]
    for e in effects:
        restored = EffectAdapter.validate_python(e.model_dump())
        assert restored == e
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/world/test_effects.py -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/world/effects.py`:

```python
"""Effects produced by transitions. Pure; return a new WorldState."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import EventId, ItemId, RoomId
from if_fun.world.events import Event, EventKind

if TYPE_CHECKING:
    from if_fun.world.state import WorldState


class _EffectBase(BaseModel):
    model_config = ConfigDict(frozen=True)


class MovePlayerEffect(_EffectBase):
    type: Literal["move_player"] = "move_player"
    room_id: RoomId


class AddItemToInventoryEffect(_EffectBase):
    type: Literal["add_item_to_inventory"] = "add_item_to_inventory"
    item_id: ItemId


class RemoveItemFromRoomEffect(_EffectBase):
    type: Literal["remove_item_from_room"] = "remove_item_from_room"
    room_id: RoomId
    item_id: ItemId


class SetRoomFlagEffect(_EffectBase):
    type: Literal["set_room_flag"] = "set_room_flag"
    room_id: RoomId
    flag: str
    value: Any


class SetGlobalFlagEffect(_EffectBase):
    type: Literal["set_global_flag"] = "set_global_flag"
    flag: str
    value: Any


class EmitEventEffect(_EffectBase):
    type: Literal["emit_event"] = "emit_event"
    event_id: EventId
    kind: EventKind
    payload: dict[str, Any] = Field(default_factory=dict)


Effect = Annotated[
    Union[
        MovePlayerEffect,
        AddItemToInventoryEffect,
        RemoveItemFromRoomEffect,
        SetRoomFlagEffect,
        SetGlobalFlagEffect,
        EmitEventEffect,
    ],
    Field(discriminator="type"),
]


def apply(effect: Effect, world: "WorldState") -> "WorldState":
    """Return a new WorldState with `effect` applied. The input is not mutated."""

    from if_fun.world.state import WorldState  # local import to avoid cycle

    match effect:
        case MovePlayerEffect(room_id=room_id):
            new_player = world.player.model_copy(update={"location": room_id})
            return world.model_copy(update={"player": new_player})

        case AddItemToInventoryEffect(item_id=item_id):
            new_inv = world.player.inventory | {item_id}
            new_player = world.player.model_copy(update={"inventory": new_inv})
            return world.model_copy(update={"player": new_player})

        case RemoveItemFromRoomEffect(room_id=room_id, item_id=item_id):
            room = world.rooms[room_id]
            new_items = room.items_present - {item_id}
            new_room = room.model_copy(update={"items_present": new_items})
            new_rooms = {**world.rooms, room_id: new_room}
            return world.model_copy(update={"rooms": new_rooms})

        case SetRoomFlagEffect(room_id=room_id, flag=flag, value=value):
            room = world.rooms[room_id]
            new_flags = {**room.flags, flag: value}
            new_room = room.model_copy(update={"flags": new_flags})
            new_rooms = {**world.rooms, room_id: new_room}
            return world.model_copy(update={"rooms": new_rooms})

        case SetGlobalFlagEffect(flag=flag, value=value):
            new_globals = {**world.globals, flag: value}
            return world.model_copy(update={"globals": new_globals})

        case EmitEventEffect(event_id=event_id, kind=kind, payload=payload):
            ev = Event(id=event_id, turn=world.turn, kind=kind, payload=payload)
            new_log = [*world.event_log, ev]
            return world.model_copy(update={"event_log": new_log})

    raise AssertionError(f"unhandled effect: {effect!r}")  # pragma: no cover
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/world/test_effects.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add if_fun/world/effects.py tests/world/test_effects.py
git commit -m "feat(world): add Effect discriminated union and pure apply()"
```

---

## Task 7: Trigger, Action, Transition

**Files:**
- Create: `if_fun/world/transitions.py`
- Test: `tests/world/test_transitions.py`

Triggers name *how* a transition fires. For Phase A we need:

- `VerbObjectTrigger` — player enters a verb + optional direct object
- `DirectionTrigger` — player moves in a direction
- `TimeTrigger` — fires every N turns (used for future mob code; we include it for completeness)

An `Action` is the parsed player input. A `Transition` is `id + name + trigger + guards + effects + narration_hint`.

- [ ] **Step 1: Write the failing test**

Create `tests/world/test_transitions.py`:

```python
import pytest
from pydantic import TypeAdapter, ValidationError

from if_fun.ids import Direction, ItemId, RoomId
from if_fun.world.effects import MovePlayerEffect
from if_fun.world.guards import PlayerInRoomGuard
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
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/world/test_transitions.py -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/world/transitions.py`:

```python
"""Triggers, Actions, and Transitions."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import Direction, ItemId, MobId, RoomId
from if_fun.world.effects import Effect
from if_fun.world.guards import Guard


class _TriggerBase(BaseModel):
    model_config = ConfigDict(frozen=True)


class VerbObjectTrigger(_TriggerBase):
    type: Literal["verb_object"] = "verb_object"
    verb: str
    direct_object: ItemId | MobId | RoomId | None = None


class DirectionTrigger(_TriggerBase):
    type: Literal["direction"] = "direction"
    direction: Direction


class TimeTrigger(_TriggerBase):
    type: Literal["time"] = "time"
    period: int = Field(gt=0)


Trigger = Annotated[
    Union[VerbObjectTrigger, DirectionTrigger, TimeTrigger],
    Field(discriminator="type"),
]


class Action(BaseModel):
    model_config = ConfigDict(frozen=True)

    verb: str
    direct_object: ItemId | MobId | RoomId | None = None
    indirect_object: ItemId | MobId | RoomId | None = None


class Transition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    trigger: Trigger
    guards: list[Guard] = Field(default_factory=list)
    effects: list[Effect]
    narration_hint: str | None = None
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/world/test_transitions.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add if_fun/world/transitions.py tests/world/test_transitions.py
git commit -m "feat(world): add Trigger/Action/Transition models"
```

---

## Task 8: RoomState and WorldState

**Files:**
- Create: `if_fun/world/rooms.py`
- Create: `if_fun/world/state.py`
- Test: `tests/world/test_rooms.py`
- Test: `tests/world/test_state.py`

For Phase A, `RoomState` carries *both* static structural data (id, description, exits, transitions) and dynamic state. A later phase may split these into `RoomDef` + `RoomState` when generation lands; the spec's §5.1 only mandates the dynamic fields, so we are extending it for Phase A convenience. We document the intent inline.

`WorldState` holds `rooms`, `player`, `globals`, `turn`, `event_log`, `win_condition`, `schema_version`.

- [ ] **Step 1: Write the failing tests**

Create `tests/world/test_rooms.py`:

```python
from if_fun.ids import Direction, ItemId, RoomId
from if_fun.world.effects import AddItemToInventoryEffect, RemoveItemFromRoomEffect
from if_fun.world.guards import PlayerInRoomGuard
from if_fun.world.rooms import RoomState
from if_fun.world.transitions import DirectionTrigger, Transition, VerbObjectTrigger


def test_room_defaults_are_empty() -> None:
    r = RoomState(
        id=RoomId("entry_hall"),
        description="A dim stone hallway.",
    )
    assert r.items_present == frozenset()
    assert r.occupants == frozenset()
    assert r.event_ids == ()
    assert r.flags == {}
    assert r.exits == {}
    assert r.transitions == ()
    assert r.visited is False


def test_room_with_exits_and_transitions() -> None:
    r = RoomState(
        id=RoomId("entry_hall"),
        description="A dim stone hallway.",
        exits={Direction.NORTH: RoomId("library")},
        items_present=frozenset({ItemId("brass_key")}),
        transitions=(
            Transition(
                id="take_key",
                name="take brass key",
                trigger=VerbObjectTrigger(verb="take", direct_object=ItemId("brass_key")),
                guards=[PlayerInRoomGuard(room_id=RoomId("entry_hall"))],
                effects=[
                    RemoveItemFromRoomEffect(room_id=RoomId("entry_hall"), item_id=ItemId("brass_key")),
                    AddItemToInventoryEffect(item_id=ItemId("brass_key")),
                ],
            ),
        ),
    )
    restored = RoomState.model_validate_json(r.model_dump_json())
    assert restored == r
```

Create `tests/world/test_state.py`:

```python
from if_fun.ids import EventId, RoomId
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
    w = _minimal_world().model_copy(update={"event_log": [
        Event(id=EventId("evt_001"), turn=0, kind=EventKind.PLAYER_MOVED, payload={}),
        Event(id=EventId("evt_002"), turn=1, kind=EventKind.ITEM_TAKEN, payload={}),
    ]})
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
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/world/test_rooms.py tests/world/test_state.py -q`
Expected: collection errors.

- [ ] **Step 3: Implement**

`if_fun/world/rooms.py`:

```python
"""Room state. For Phase A, combines static (id, description, exits, transitions) and dynamic fields."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import Direction, EventId, ItemId, MobId, RoomId
from if_fun.world.transitions import Transition


class RoomState(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: RoomId
    description: str
    exits: dict[Direction, RoomId] = Field(default_factory=dict)
    transitions: tuple[Transition, ...] = ()

    visited: bool = False
    items_present: frozenset[ItemId] = Field(default_factory=frozenset)
    occupants: frozenset[MobId] = Field(default_factory=frozenset)
    event_ids: tuple[EventId, ...] = ()
    flags: dict[str, Any] = Field(default_factory=dict)
```

`if_fun/world/state.py`:

```python
"""Top-level WorldState and WinCondition."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import RoomId
from if_fun.world.events import Event
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState


WinConditionKind = Literal["player_in_room", "global_flag_equals", "has_item"]


class WinCondition(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: WinConditionKind
    args: dict[str, Any] = Field(default_factory=dict)


class WorldState(BaseModel):
    model_config = ConfigDict(frozen=True)

    rooms: dict[RoomId, RoomState]
    player: PlayerState
    globals: dict[str, Any] = Field(default_factory=dict)
    turn: int = Field(default=0, ge=0)
    event_log: list[Event] = Field(default_factory=list)
    win_condition: WinCondition
    schema_version: int = 1

    def is_won(self) -> bool:
        match self.win_condition.kind:
            case "player_in_room":
                return self.player.location == self.win_condition.args["room_id"]
            case "global_flag_equals":
                return self.globals.get(self.win_condition.args["flag"]) == self.win_condition.args["value"]
            case "has_item":
                return self.win_condition.args["item_id"] in self.player.inventory
        raise AssertionError(f"unhandled win kind: {self.win_condition.kind!r}")  # pragma: no cover
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/world -q`
Expected: all passing — events, player, guards, effects, transitions, rooms, state.

- [ ] **Step 5: Commit**

```bash
git add if_fun/world/rooms.py if_fun/world/state.py tests/world/test_rooms.py tests/world/test_state.py
git commit -m "feat(world): add RoomState and WorldState with WinCondition"
```

---

## Task 9: StateStore

**Files:**
- Create: `if_fun/world/store.py`
- Test: `tests/world/test_store.py`

`StateStore` is a pure-function service (no class needed; a module of functions is fine). Responsibilities:

- `find_transition(world, action)` → `Transition | None` — matches an `Action` or direction to a transition in the player's current room.
- `legal_transitions(world)` → `list[Transition]` — transitions whose guards all pass in `world`.
- `apply_transition(world, transition)` → `WorldState` — validates guards, applies effects in order, bumps `turn`, always appends a `TRANSITION_APPLIED` event (distinct from any explicit `EmitEventEffect`s).
- `apply_action(world, action)` → `WorldState` — `find_transition` + `apply_transition`, raises `IllegalAction` if no match or guards fail.

- [ ] **Step 1: Write the failing tests**

Create `tests/world/test_store.py`:

```python
import pytest

from if_fun.ids import Direction, EventId, ItemId, RoomId
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
        win_condition=WinCondition(kind="global_flag_equals", args={"flag": "entered_library", "value": True}),
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
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/world/test_store.py -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/world/store.py`:

```python
"""StateStore service: matches actions to transitions, applies them purely."""

from __future__ import annotations

from if_fun.ids import Direction, EventId
from if_fun.world.effects import apply as apply_effect
from if_fun.world.events import Event, EventKind
from if_fun.world.guards import evaluate as evaluate_guard
from if_fun.world.state import WorldState
from if_fun.world.transitions import Action, DirectionTrigger, Transition, VerbObjectTrigger


class IllegalAction(Exception):
    """Raised when an action does not match a legal transition in the current state."""


def find_transition(world: WorldState, action: Action) -> Transition | None:
    """Match a verb-object action to a transition in the player's current room."""
    room = world.rooms[world.player.location]
    for tr in room.transitions:
        if isinstance(tr.trigger, VerbObjectTrigger):
            if tr.trigger.verb == action.verb and tr.trigger.direct_object == action.direct_object:
                return tr
    return None


def find_direction_transition(world: WorldState, direction: Direction) -> Transition | None:
    """Match a direction to a transition in the player's current room."""
    room = world.rooms[world.player.location]
    for tr in room.transitions:
        if isinstance(tr.trigger, DirectionTrigger) and tr.trigger.direction is direction:
            return tr
    # Fallback: a bare exit with no guarded transition becomes a free MovePlayerEffect.
    if direction in room.exits:
        from if_fun.world.effects import MovePlayerEffect

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
    """Return a new WorldState with `transition` applied. Raises IllegalAction if guards fail."""
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
    return new_world.model_copy(update={
        "turn": next_turn,
        "event_log": [*new_world.event_log, marker],
    })


def apply_action(world: WorldState, action: Action) -> WorldState:
    tr = find_transition(world, action)
    if tr is None:
        raise IllegalAction(f"no transition matches action: {action!r}")
    return apply_transition(world, tr)


def apply_direction(world: WorldState, direction: Direction) -> WorldState:
    tr = find_direction_transition(world, direction)
    if tr is None:
        raise IllegalAction(f"no exit or transition {direction.value} from {world.player.location!r}")
    return apply_transition(world, tr)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/world -q`
Expected: all store tests pass, alongside prior tests.

- [ ] **Step 5: Commit**

```bash
git add if_fun/world/store.py tests/world/test_store.py
git commit -m "feat(world): add StateStore with pure transition application and guard checking"
```

---

## Task 10: Save format

**Files:**
- Create: `if_fun/save/__init__.py` (empty)
- Create: `if_fun/save/paths.py`
- Create: `if_fun/save/save_format.py`
- Create: `if_fun/save/schema_migrations/__init__.py`
- Test: `tests/save/test_save_format.py`
- Create: `tests/save/__init__.py` (empty)

- [ ] **Step 1: Write the failing test**

Create `tests/save/test_save_format.py`:

```python
from pathlib import Path

import pytest

from if_fun.ids import RoomId
from if_fun.save.paths import save_path, saves_dir
from if_fun.save.save_format import (
    SaveFormatError,
    SchemaVersionMismatch,
    read_save,
    write_save,
)
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState
from if_fun.world.state import WinCondition, WorldState


def _tiny_world() -> WorldState:
    return WorldState(
        rooms={
            RoomId("r1"): RoomState(id=RoomId("r1"), description="A room."),
        },
        player=PlayerState(location=RoomId("r1")),
        win_condition=WinCondition(kind="player_in_room", args={"room_id": "r1"}),
    )


def test_saves_dir_resolves_under_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    assert saves_dir() == tmp_path / "saves"


def test_save_path_joins_slot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    assert save_path("slot1") == tmp_path / "saves" / "slot1.json"


def test_write_and_read_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    w = _tiny_world()
    write_save("slot1", w)
    restored = read_save("slot1")
    assert restored == w


def test_read_save_future_version_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    p = save_path("future")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"schema_version": 9999}')
    with pytest.raises(SchemaVersionMismatch):
        read_save("future")


def test_read_save_garbage_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    p = save_path("garbage")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("this is not json")
    with pytest.raises(SaveFormatError):
        read_save("garbage")
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/save -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/save/paths.py`:

```python
"""Filesystem paths for saves, templates, and logs."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_state_dir


def state_dir() -> Path:
    """Return the if_fun state directory, respecting IF_FUN_STATE_DIR for tests."""
    override = os.environ.get("IF_FUN_STATE_DIR")
    if override:
        return Path(override)
    return Path(user_state_dir("if_fun", appauthor=False))


def saves_dir() -> Path:
    return state_dir() / "saves"


def save_path(slot: str) -> Path:
    return saves_dir() / f"{slot}.json"
```

`if_fun/save/schema_migrations/__init__.py`:

```python
"""Save schema migration registry. Empty for v1."""

from __future__ import annotations

from typing import Callable

CURRENT_SCHEMA_VERSION = 1

# Mapping: version_from -> (version_to, migrate_fn).
# migrate_fn takes a dict and returns a dict.
MIGRATIONS: dict[int, tuple[int, Callable[[dict], dict]]] = {}
```

`if_fun/save/save_format.py`:

```python
"""Save read/write with schema versioning."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from if_fun.save.paths import save_path
from if_fun.save.schema_migrations import CURRENT_SCHEMA_VERSION, MIGRATIONS
from if_fun.world.state import WorldState


class SaveFormatError(Exception):
    """Raised when a save file is malformed or unreadable."""


class SchemaVersionMismatch(SaveFormatError):
    """Raised when a save file's schema_version is newer than we understand."""


def write_save(slot: str, world: WorldState) -> Path:
    p = save_path(slot)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(world.model_dump_json(indent=2))
    return p


def read_save(slot: str) -> WorldState:
    p = save_path(slot)
    try:
        raw = p.read_text()
    except FileNotFoundError as exc:
        raise SaveFormatError(f"save not found: {slot!r}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SaveFormatError(f"save {slot!r} is not valid JSON") from exc

    version = data.get("schema_version", 1)
    while version != CURRENT_SCHEMA_VERSION:
        if version > CURRENT_SCHEMA_VERSION:
            raise SchemaVersionMismatch(
                f"save {slot!r} has schema_version={version}, "
                f"but this build understands up to {CURRENT_SCHEMA_VERSION}"
            )
        if version not in MIGRATIONS:
            raise SaveFormatError(f"no migration registered for schema version {version}")
        target, migrate = MIGRATIONS[version]
        data = migrate(data)
        version = target

    try:
        return WorldState.model_validate(data)
    except ValidationError as exc:
        raise SaveFormatError(f"save {slot!r} failed validation: {exc}") from exc
```

Create `tests/save/__init__.py` as empty.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/save -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add if_fun/save tests/save
git commit -m "feat(save): add JSON save format with schema versioning"
```

---

## Task 11: Parser grammar

**Files:**
- Create: `if_fun/parser/__init__.py` (empty)
- Create: `if_fun/parser/grammar.py`
- Test: `tests/parser/test_grammar.py`
- Create: `tests/parser/__init__.py` (empty)

The grammar is a table of canonical verbs and aliases. The parser's job is to normalize an input string into an `Action` or a `DirectionCommand` or a `MetaCommand`.

- [ ] **Step 1: Write the failing test**

Create `tests/parser/test_grammar.py`:

```python
import pytest

from if_fun.parser.grammar import CANONICAL_VERBS, MetaVerb, canonical_verb


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("take", "take"),
        ("get", "take"),
        ("pick", "take"),
        ("drop", "drop"),
        ("examine", "examine"),
        ("x", "examine"),
        ("look", "look"),
        ("l", "look"),
        ("inventory", "inventory"),
        ("i", "inventory"),
        ("open", "open"),
        ("unlock", "unlock"),
        ("use", "use"),
        ("wait", "wait"),
        ("z", "wait"),
    ],
)
def test_canonical_verb_from_alias(token: str, expected: str) -> None:
    assert canonical_verb(token) == expected


def test_canonical_verb_unknown_returns_none() -> None:
    assert canonical_verb("hovercraft") is None


def test_canonical_verbs_has_a_dozen_entries() -> None:
    assert len(CANONICAL_VERBS) >= 12


def test_meta_verb_values_are_stable() -> None:
    assert MetaVerb.SAVE.value == "save"
    assert MetaVerb.LOAD.value == "load"
    assert MetaVerb.QUIT.value == "quit"
    assert MetaVerb.HELP.value == "help"
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/parser -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/parser/grammar.py`:

```python
"""Canonical verb grammar for the Phase A parser."""

from __future__ import annotations

from enum import StrEnum

CANONICAL_VERBS: dict[str, frozenset[str]] = {
    "take":      frozenset({"take", "get", "grab", "pick"}),
    "drop":      frozenset({"drop", "put"}),
    "examine":   frozenset({"examine", "x", "look at"}),
    "look":      frozenset({"look", "l"}),
    "inventory": frozenset({"inventory", "i", "inv"}),
    "open":      frozenset({"open"}),
    "close":     frozenset({"close", "shut"}),
    "unlock":    frozenset({"unlock"}),
    "lock":      frozenset({"lock"}),
    "use":       frozenset({"use"}),
    "wait":      frozenset({"wait", "z"}),
    "go":        frozenset({"go", "walk", "move"}),
}


class MetaVerb(StrEnum):
    SAVE = "save"
    LOAD = "load"
    QUIT = "quit"
    HELP = "help"


_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: verb
    for verb, aliases in CANONICAL_VERBS.items()
    for alias in aliases
}


def canonical_verb(token: str) -> str | None:
    return _ALIAS_TO_CANONICAL.get(token.strip().lower())
```

Also create `tests/parser/__init__.py` as empty.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/parser -q`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git add if_fun/parser/__init__.py if_fun/parser/grammar.py tests/parser/__init__.py tests/parser/test_grammar.py
git commit -m "feat(parser): add canonical verb grammar and alias table"
```

---

## Task 12: Deterministic parser

**Files:**
- Create: `if_fun/parser/parser.py`
- Test: `tests/parser/test_parser.py`

The parser takes a raw input string and returns:

- `DirectionCommand(Direction)` for movement words (`n`, `north`, `go north`)
- `MetaCommand(MetaVerb, arg)` for `save`, `load`, `quit`, `help`
- `Action(verb, direct_object=...)` for world verbs
- `ParseError("message")` for gibberish

The parser has **no knowledge of which items/rooms exist** — it just normalizes. The caller (StateStore) decides legality. Object tokens are taken at face value (the player types `take brass_key` or `take brass key`; for Phase A we accept single-token objects and join multi-token objects with `_`).

Real IF parsers disambiguate against the world model; Phase A is deliberately dumb and leans on the hardcoded world to use simple one-word objects.

- [ ] **Step 1: Write the failing test**

Create `tests/parser/test_parser.py`:

```python
import pytest

from if_fun.ids import Direction, ItemId
from if_fun.parser.grammar import MetaVerb
from if_fun.parser.parser import (
    DirectionCommand,
    MetaCommand,
    ParseError,
    ParsedCommand,
    parse,
)
from if_fun.world.transitions import Action


def _unwrap(cmd: ParsedCommand) -> object:
    assert not isinstance(cmd, ParseError), cmd.message
    return cmd


@pytest.mark.parametrize(
    ("raw", "direction"),
    [
        ("n", Direction.NORTH),
        ("north", Direction.NORTH),
        ("go north", Direction.NORTH),
        ("walk south", Direction.SOUTH),
        ("u", Direction.UP),
    ],
)
def test_parse_direction_words(raw: str, direction: Direction) -> None:
    cmd = _unwrap(parse(raw))
    assert isinstance(cmd, DirectionCommand)
    assert cmd.direction is direction


def test_parse_single_verb_action() -> None:
    cmd = _unwrap(parse("look"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "look"
    assert cmd.direct_object is None


def test_parse_verb_object_action() -> None:
    cmd = _unwrap(parse("take brass_key"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "take"
    assert cmd.direct_object == ItemId("brass_key")


def test_parse_verb_alias_normalized() -> None:
    cmd = _unwrap(parse("get brass_key"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "take"


def test_parse_multi_word_object_joined_with_underscore() -> None:
    cmd = _unwrap(parse("take brass key"))
    assert isinstance(cmd, Action)
    assert cmd.verb == "take"
    assert cmd.direct_object == ItemId("brass_key")


def test_parse_meta_save_with_slot() -> None:
    cmd = _unwrap(parse("save slot1"))
    assert isinstance(cmd, MetaCommand)
    assert cmd.verb is MetaVerb.SAVE
    assert cmd.arg == "slot1"


def test_parse_meta_load_with_slot() -> None:
    cmd = _unwrap(parse("load slot1"))
    assert isinstance(cmd, MetaCommand)
    assert cmd.verb is MetaVerb.LOAD
    assert cmd.arg == "slot1"


def test_parse_meta_quit() -> None:
    cmd = _unwrap(parse("quit"))
    assert isinstance(cmd, MetaCommand)
    assert cmd.verb is MetaVerb.QUIT
    assert cmd.arg is None


def test_parse_empty_is_error() -> None:
    cmd = parse("")
    assert isinstance(cmd, ParseError)


def test_parse_unknown_verb_is_error() -> None:
    cmd = parse("hovercraft eels")
    assert isinstance(cmd, ParseError)
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/parser/test_parser.py -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/parser/parser.py`:

```python
"""Deterministic Phase A parser. Input string → ParsedCommand."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from if_fun.ids import Direction, ItemId
from if_fun.parser.grammar import MetaVerb, canonical_verb
from if_fun.world.transitions import Action


@dataclass(frozen=True)
class DirectionCommand:
    direction: Direction


@dataclass(frozen=True)
class MetaCommand:
    verb: MetaVerb
    arg: str | None = None


@dataclass(frozen=True)
class ParseError:
    message: str


ParsedCommand = Union[Action, DirectionCommand, MetaCommand, ParseError]


_META_VERBS = {v.value for v in MetaVerb}


def parse(raw: str) -> ParsedCommand:
    tokens = raw.strip().lower().split()
    if not tokens:
        return ParseError("empty input")

    # Meta commands (save / load / quit / help) with optional single arg.
    if tokens[0] in _META_VERBS:
        verb = MetaVerb(tokens[0])
        arg = tokens[1] if len(tokens) >= 2 else None
        return MetaCommand(verb=verb, arg=arg)

    # Bare direction word: "n", "north".
    if len(tokens) == 1:
        d = Direction.from_token(tokens[0])
        if d is not None:
            return DirectionCommand(direction=d)

    # "go north" / "walk south".
    if len(tokens) == 2 and canonical_verb(tokens[0]) == "go":
        d = Direction.from_token(tokens[1])
        if d is not None:
            return DirectionCommand(direction=d)

    # Verb only: "look", "inventory", "wait".
    if len(tokens) == 1:
        verb = canonical_verb(tokens[0])
        if verb is not None:
            return Action(verb=verb)
        return ParseError(f"unknown verb: {tokens[0]!r}")

    # Verb + one-or-more-token object: join object tokens with underscore.
    verb = canonical_verb(tokens[0])
    if verb is None:
        return ParseError(f"unknown verb: {tokens[0]!r}")
    obj_token = "_".join(tokens[1:])
    return Action(verb=verb, direct_object=ItemId(obj_token))
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/parser -q`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git add if_fun/parser/parser.py tests/parser/test_parser.py
git commit -m "feat(parser): add deterministic parser for directions, verbs, and meta-commands"
```

---

## Task 13: Map Verifier

**Files:**
- Create: `if_fun/agents/__init__.py` (empty)
- Create: `if_fun/agents/map_verifier.py`
- Test: `tests/agents/test_map_verifier.py`
- Create: `tests/agents/__init__.py` (empty)

Note: `agents/` in Phase A contains only two deterministic modules (Map Verifier, Solvability Checker). Neither calls an LLM. They live here to match §13's directory layout in the spec. The package-boundary test (Task 19) treats them as permitted dependencies from no one in Phase A — they are called from `tests/` and eventually from Phase B's Editor.

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_map_verifier.py`:

```python
import pytest

from if_fun.agents.map_verifier import MapVerdict, verify_map
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
    assert verdict.issues == []


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
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/agents -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/agents/map_verifier.py`:

```python
"""Deterministic map verifier: reachability + geometry consistency."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from if_fun.ids import RoomId
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
                issues.append(f"room {rid!r} has exit {direction.value} to unknown target {target!r}")

    # 2. Geometry: if A→B is direction d, B→A should be d.opposite() (unless it's a one-way
    # exit, which Phase A does not model — treat all exits as two-way).
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


def _bfs_reachable(
    rooms: dict[RoomId, "RoomState"],  # type: ignore[name-defined]
    start: RoomId,
) -> set[RoomId]:
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
```

Also create `tests/agents/__init__.py` as empty.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/agents/test_map_verifier.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add if_fun/agents tests/agents
git commit -m "feat(agents): add deterministic Map Verifier"
```

---

## Task 14: Solvability Checker (BFS model checker)

**Files:**
- Create: `if_fun/agents/solvability_checker.py`
- Test: `tests/agents/test_solvability_checker.py`

The checker does BFS over the composed world state machine. At each state, it enumerates legal actions:

- Every transition in the current room whose guards pass (via `legal_transitions`).
- Every direction in the current room's `exits` dict — produces an implicit `MovePlayerEffect` (via `find_direction_transition`).

It terminates when `world.is_won()` returns True. It bounds runtime with a configurable `max_states` and `timeout_seconds`.

Output:

```python
@dataclass(frozen=True)
class SolvabilityReport:
    solvable: bool
    winning_trace: tuple[str, ...] | None   # ordered transition ids
    states_explored: int
    timed_out: bool
```

State hashing: we use `world.model_dump_json(exclude={"event_log", "turn"})` as a canonical fingerprint. The event log and turn counter are bookkeeping that doesn't affect reachability.

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_solvability_checker.py`:

```python
import pytest

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
        win_condition=WinCondition(kind="global_flag_equals", args={"flag": "entered_library", "value": True}),
    )


def _unsolvable_world() -> WorldState:
    # Same structure, but no way to acquire the key → go_north guard never passes.
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
                exits={},  # no free exit either
                transitions=(go_north,),
            ),
            RoomId("library"): RoomState(
                id=RoomId("library"),
                description="Unreachable.",
            ),
        },
        player=PlayerState(location=RoomId("entry_hall")),
        win_condition=WinCondition(kind="global_flag_equals", args={"flag": "entered_library", "value": True}),
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
    # With only 1 state allowed, BFS cannot reach the win state.
    assert report.timed_out
    assert not report.solvable
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/agents/test_solvability_checker.py -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/agents/solvability_checker.py`:

```python
"""BFS model checker over the composed WorldState machine."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Iterable

from if_fun.ids import Direction
from if_fun.world.state import WorldState
from if_fun.world.store import IllegalAction, apply_transition, find_direction_transition, legal_transitions
from if_fun.world.transitions import Transition


@dataclass(frozen=True)
class SolvabilityReport:
    solvable: bool
    winning_trace: tuple[str, ...] | None
    states_explored: int
    timed_out: bool


def _candidate_transitions(world: WorldState) -> Iterable[Transition]:
    yield from legal_transitions(world)
    # Implicit direction moves (rooms with bare exits and no guarded go_<dir> transition).
    for direction in Direction:
        tr = find_direction_transition(world, direction)
        if tr is None:
            continue
        # Only yield implicit moves (those have ids like "_implicit_move_*").
        if tr.id.startswith("_implicit_move_"):
            yield tr


def _fingerprint(world: WorldState) -> str:
    # Exclude bookkeeping fields from the state fingerprint.
    return world.model_dump_json(exclude={"event_log", "turn"})


def check_solvability(
    world: WorldState,
    *,
    max_states: int = 50_000,
    timeout_seconds: float = 60.0,
) -> SolvabilityReport:
    if world.is_won():
        return SolvabilityReport(True, (), 1, False)

    start_fp = _fingerprint(world)
    queue: deque[tuple[WorldState, tuple[str, ...]]] = deque([(world, ())])
    seen: dict[str, tuple[str, ...]] = {start_fp: ()}
    started = time.monotonic()

    while queue:
        if len(seen) >= max_states:
            return SolvabilityReport(False, None, len(seen), True)
        if time.monotonic() - started > timeout_seconds:
            return SolvabilityReport(False, None, len(seen), True)

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
                return SolvabilityReport(True, next_trace, len(seen) + 1, False)
            seen[fp] = next_trace
            queue.append((next_state, next_trace))

    return SolvabilityReport(False, None, len(seen), False)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/agents -q`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git add if_fun/agents/solvability_checker.py tests/agents/test_solvability_checker.py
git commit -m "feat(agents): add BFS solvability checker with timeout and state cap"
```

---

## Task 15: Hardcoded 5-room test world

**Files:**
- Create: `if_fun/worlds/__init__.py` (empty)
- Create: `if_fun/worlds/five_room.py`
- Test: `tests/worlds/test_five_room.py`
- Create: `tests/worlds/__init__.py` (empty)

The five-room world is the Phase A playable fixture. Design:

```
       [treasury]
           |
           N (requires silver_key)
           |
         [ritual_chamber]
           |                 (inscribed altar triggers win when player places crystal)
           N (unlocks with brass_key)
           |
[antechamber] ── E ── [entry_hall] ── W ── [vault]
                          |                      items: brass_key
                          S
                          |
                       [library]
                          items: silver_key, crystal
```

Slightly simpler layout we'll actually ship (still 5 rooms, one linear progression):

- `entry_hall` (start)
  - E → `vault` (contains `brass_key`)
  - S → `library` (contains `silver_key` and `crystal`)
  - N → `ritual_chamber` (locked; requires `brass_key` to go N)
- `ritual_chamber`
  - N → `treasury` (locked; requires `silver_key` to go N)
  - S → `entry_hall`
- `treasury`
  - S → `ritual_chamber`
  - Contains nothing; the win condition fires when player `use crystal` in `treasury`.

**Win condition:** `global_flag_equals("crystal_placed", True)`.

Winning trace: `E` → `take brass_key` → `W` → `S` → `take silver_key` → `take crystal` → `N` → `N` (requires brass_key) → `N` (requires silver_key) → `use crystal` → win. That's long enough to exercise real turns but BFS solves instantly.

Actually, simpler: `N` from entry to ritual_chamber requires brass_key; `N` from ritual_chamber to treasury requires silver_key; win = arrive in treasury.

- [ ] **Step 1: Write the failing test**

Create `tests/worlds/test_five_room.py`:

```python
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
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/worlds -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/worlds/five_room.py`:

```python
"""Hardcoded 5-room test world for Phase A. No LLM involvement.

Layout:

       [treasury]
           |
           N (requires silver_key)
           |
    [ritual_chamber]
           |
           N (requires brass_key)
           |
  [vault] -W- [entry_hall] -S- [library]

Win condition: player reaches treasury.
"""

from __future__ import annotations

from if_fun.ids import Direction, ItemId, RoomId
from if_fun.world.effects import (
    AddItemToInventoryEffect,
    MovePlayerEffect,
    RemoveItemFromRoomEffect,
)
from if_fun.world.guards import HasItemGuard, PlayerInRoomGuard
from if_fun.world.player import PlayerState
from if_fun.world.rooms import RoomState
from if_fun.world.state import WinCondition, WorldState
from if_fun.world.transitions import DirectionTrigger, Transition, VerbObjectTrigger


def _take(room_id: str, item_id: str) -> Transition:
    return Transition(
        id=f"take_{item_id}_in_{room_id}",
        name=f"take {item_id}",
        trigger=VerbObjectTrigger(verb="take", direct_object=ItemId(item_id)),
        guards=[PlayerInRoomGuard(room_id=RoomId(room_id))],
        effects=[
            RemoveItemFromRoomEffect(room_id=RoomId(room_id), item_id=ItemId(item_id)),
            AddItemToInventoryEffect(item_id=ItemId(item_id)),
        ],
    )


def _locked_north(from_room: str, to_room: str, required_item: str) -> Transition:
    return Transition(
        id=f"go_north_{from_room}_to_{to_room}",
        name=f"move north to {to_room}",
        trigger=DirectionTrigger(direction=Direction.NORTH),
        guards=[
            PlayerInRoomGuard(room_id=RoomId(from_room)),
            HasItemGuard(item_id=ItemId(required_item)),
        ],
        effects=[MovePlayerEffect(room_id=RoomId(to_room))],
    )


def build_five_room_world() -> WorldState:
    entry_hall = RoomState(
        id=RoomId("entry_hall"),
        description=(
            "A stone antechamber. Heavy doors lie to the north. "
            "Corridors lead east to a vault and south to a library."
        ),
        exits={
            Direction.EAST: RoomId("vault"),
            Direction.SOUTH: RoomId("library"),
        },
        transitions=(
            _locked_north("entry_hall", "ritual_chamber", "brass_key"),
        ),
    )
    vault = RoomState(
        id=RoomId("vault"),
        description="Cold stone walls. A tarnished brass key rests on a plinth.",
        exits={Direction.WEST: RoomId("entry_hall")},
        items_present=frozenset({ItemId("brass_key")}),
        transitions=(_take("vault", "brass_key"),),
    )
    library = RoomState(
        id=RoomId("library"),
        description="Shelves of brittle books. A silver key and a pale crystal sit on a desk.",
        exits={Direction.NORTH: RoomId("entry_hall")},
        items_present=frozenset({ItemId("silver_key"), ItemId("crystal")}),
        transitions=(
            _take("library", "silver_key"),
            _take("library", "crystal"),
        ),
    )
    ritual_chamber = RoomState(
        id=RoomId("ritual_chamber"),
        description="Circles etched into the floor glow faintly. Another door lies north.",
        exits={Direction.SOUTH: RoomId("entry_hall")},
        transitions=(
            _locked_north("ritual_chamber", "treasury", "silver_key"),
        ),
    )
    treasury = RoomState(
        id=RoomId("treasury"),
        description="Gold gleams in torchlight. You have found the treasury.",
        exits={Direction.SOUTH: RoomId("ritual_chamber")},
    )

    rooms = {
        r.id: r
        for r in (entry_hall, vault, library, ritual_chamber, treasury)
    }

    return WorldState(
        rooms=rooms,
        player=PlayerState(location=RoomId("entry_hall")),
        win_condition=WinCondition(kind="player_in_room", args={"room_id": "treasury"}),
    )
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/worlds -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add if_fun/worlds tests/worlds
git commit -m "feat(worlds): add hardcoded 5-room walking-skeleton world"
```

---

## Task 16: Turn engine

**Files:**
- Create: `if_fun/tui/__init__.py` (empty)
- Create: `if_fun/tui/turn_engine.py`
- Test: `tests/tui/test_turn_engine.py`
- Create: `tests/tui/__init__.py` (empty)

The turn engine is a thin, non-UI class that wires together parser + StateStore + save/load + render. Phase A has no LLM narrator — narration is `room.description` plus a canonical outcome message.

API:

```python
class TurnEngine:
    def __init__(self, world: WorldState) -> None: ...
    @property
    def world(self) -> WorldState: ...
    def describe_current_room(self) -> str: ...
    def submit(self, raw_input: str) -> str: ...  # returns display text for this turn
    def save(self, slot: str) -> None: ...
    def load(self, slot: str) -> None: ...
```

The `submit` method:

1. Parses input.
2. Dispatches by command kind:
   - `DirectionCommand` → `apply_direction`
   - `Action(verb="look")` → current room description
   - `Action(verb="inventory")` → inventory listing
   - other `Action` → `apply_action`
   - `MetaCommand(SAVE|LOAD)` → save/load
   - `MetaCommand(QUIT)` → return the string `"__QUIT__"` (TUI checks for it)
   - `ParseError` → error message
3. On `IllegalAction` → user-facing "You can't do that." message.
4. On win → append `"** You have won. **"` to the output.

- [ ] **Step 1: Write the failing tests**

Create `tests/tui/test_turn_engine.py`:

```python
from pathlib import Path

import pytest

from if_fun.tui.turn_engine import TurnEngine
from if_fun.worlds.five_room import build_five_room_world


def test_describe_current_room_returns_start_description() -> None:
    eng = TurnEngine(build_five_room_world())
    text = eng.describe_current_room()
    assert "antechamber" in text.lower()


def test_submit_move_east_then_take_key() -> None:
    eng = TurnEngine(build_five_room_world())
    out1 = eng.submit("east")
    assert "vault" in out1.lower()
    out2 = eng.submit("take brass_key")
    assert "brass_key" in eng.world.player.inventory


def test_submit_look_returns_current_room_description() -> None:
    eng = TurnEngine(build_five_room_world())
    text = eng.submit("look")
    assert text == eng.describe_current_room()


def test_submit_inventory_lists_held_items() -> None:
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass_key")
    text = eng.submit("inventory")
    assert "brass_key" in text


def test_submit_illegal_returns_friendly_message() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("north")  # locked without brass_key
    assert "can't" in out.lower() or "cannot" in out.lower()


def test_submit_parse_error_returns_message() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("hovercraft eels")
    assert "don't" in out.lower() or "unknown" in out.lower()


def test_submit_quit_returns_sentinel() -> None:
    eng = TurnEngine(build_five_room_world())
    assert eng.submit("quit") == "__QUIT__"


def test_save_and_load_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IF_FUN_STATE_DIR", str(tmp_path))
    eng = TurnEngine(build_five_room_world())
    eng.submit("east")
    eng.submit("take brass_key")
    eng.save("slot1")

    eng2 = TurnEngine(build_five_room_world())
    eng2.load("slot1")
    assert eng2.world == eng.world


def test_winning_adds_win_message() -> None:
    eng = TurnEngine(build_five_room_world())
    for cmd in [
        "east", "take brass_key", "west",
        "south", "take silver_key", "take crystal", "north",
        "north", "north",
    ]:
        out = eng.submit(cmd)
    assert "won" in out.lower()
    assert eng.world.is_won()
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/tui -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/tui/turn_engine.py`:

```python
"""Turn engine: parser + state store + save/load. No UI, no LLM."""

from __future__ import annotations

from if_fun.parser.grammar import MetaVerb
from if_fun.parser.parser import DirectionCommand, MetaCommand, ParseError, parse
from if_fun.save.save_format import read_save, write_save
from if_fun.world.state import WorldState
from if_fun.world.store import IllegalAction, apply_action, apply_direction
from if_fun.world.transitions import Action


WIN_MESSAGE = "\n** You have won. **"
QUIT_SENTINEL = "__QUIT__"


class TurnEngine:
    def __init__(self, world: WorldState) -> None:
        self._world = world

    @property
    def world(self) -> WorldState:
        return self._world

    def describe_current_room(self) -> str:
        room = self._world.rooms[self._world.player.location]
        exits = ", ".join(d.value for d in room.exits) or "none"
        items = ", ".join(room.items_present) or "none"
        return f"{room.description}\n\nExits: {exits}\nItems: {items}"

    def submit(self, raw_input: str) -> str:
        cmd = parse(raw_input)

        if isinstance(cmd, ParseError):
            return f"I don't understand that. ({cmd.message})"

        if isinstance(cmd, MetaCommand):
            return self._handle_meta(cmd)

        if isinstance(cmd, DirectionCommand):
            try:
                self._world = apply_direction(self._world, cmd.direction)
            except IllegalAction:
                return "You can't go that way."
            return self._post_turn()

        assert isinstance(cmd, Action)

        if cmd.verb == "look" and cmd.direct_object is None:
            return self.describe_current_room()
        if cmd.verb == "inventory" and cmd.direct_object is None:
            items = ", ".join(self._world.player.inventory) or "nothing"
            return f"You carry: {items}"

        try:
            self._world = apply_action(self._world, cmd)
        except IllegalAction:
            return "You can't do that."
        return self._post_turn()

    def save(self, slot: str) -> None:
        write_save(slot, self._world)

    def load(self, slot: str) -> None:
        self._world = read_save(slot)

    def _handle_meta(self, cmd: MetaCommand) -> str:
        if cmd.verb is MetaVerb.QUIT:
            return QUIT_SENTINEL
        if cmd.verb is MetaVerb.HELP:
            return (
                "Verbs: look, take <item>, drop <item>, use <item>, open, unlock, "
                "examine <item>, inventory, wait.\n"
                "Directions: n, s, e, w, u, d (or 'go north' etc.).\n"
                "Meta: save <slot>, load <slot>, quit."
            )
        if cmd.verb is MetaVerb.SAVE:
            if cmd.arg is None:
                return "Usage: save <slot>"
            self.save(cmd.arg)
            return f"Saved to slot {cmd.arg!r}."
        if cmd.verb is MetaVerb.LOAD:
            if cmd.arg is None:
                return "Usage: load <slot>"
            self.load(cmd.arg)
            return f"Loaded slot {cmd.arg!r}.\n\n" + self.describe_current_room()
        raise AssertionError(f"unhandled meta verb: {cmd.verb!r}")  # pragma: no cover

    def _post_turn(self) -> str:
        text = self.describe_current_room()
        if self._world.is_won():
            text += WIN_MESSAGE
        return text
```

Also create `tests/tui/__init__.py` as empty.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/tui -q`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add if_fun/tui/__init__.py if_fun/tui/turn_engine.py tests/tui/__init__.py tests/tui/test_turn_engine.py
git commit -m "feat(tui): add deterministic TurnEngine wiring parser, store, save/load"
```

---

## Task 17: Minimal Textual App

**Files:**
- Create: `if_fun/tui/app.py`
- Test: `tests/tui/test_app.py`

A minimal Textual app. Two widgets vertically stacked:

- `ProsePane` — scrolling RichLog of turn outputs.
- `InputLine` — an `Input` widget, submits on Enter.

`IfFunApp(TurnEngine)` — the Textual App that binds them.

Textual has a `Pilot` test harness (`App.run_test()`) that lets us drive the app headless and inspect its state.

- [ ] **Step 1: Write the failing test**

Create `tests/tui/test_app.py`:

```python
import pytest

from if_fun.tui.app import IfFunApp
from if_fun.tui.turn_engine import TurnEngine
from if_fun.worlds.five_room import build_five_room_world


@pytest.mark.asyncio
async def test_app_starts_and_shows_initial_prose() -> None:
    eng = TurnEngine(build_five_room_world())
    app = IfFunApp(eng)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert "antechamber" in app.last_output.lower()


@pytest.mark.asyncio
async def test_app_accepts_input_and_updates_prose() -> None:
    eng = TurnEngine(build_five_room_world())
    app = IfFunApp(eng)
    async with app.run_test() as pilot:
        await pilot.pause()
        input_widget = app.query_one("#command-input")
        input_widget.value = "east"
        await pilot.press("enter")
        await pilot.pause()
        assert "vault" in app.last_output.lower()


@pytest.mark.asyncio
async def test_app_exits_on_quit() -> None:
    eng = TurnEngine(build_five_room_world())
    app = IfFunApp(eng)
    async with app.run_test() as pilot:
        await pilot.pause()
        input_widget = app.query_one("#command-input")
        input_widget.value = "quit"
        await pilot.press("enter")
        await pilot.pause()
        assert app.return_value is None  # app exits cleanly
```

Add `pytest-asyncio` config to `pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
asyncio_mode = "auto"
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/tui/test_app.py -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/tui/app.py`:

```python
"""Minimal Textual app for Phase A: prose pane + input line."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, RichLog

from if_fun.tui.turn_engine import QUIT_SENTINEL, TurnEngine


class IfFunApp(App[None]):
    CSS = """
    Screen { layout: vertical; }
    RichLog { height: 1fr; border: solid grey; }
    Input { dock: bottom; }
    """

    def __init__(self, engine: TurnEngine) -> None:
        super().__init__()
        self._engine = engine
        self.last_output: str = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield RichLog(id="prose", wrap=True, markup=False, highlight=False)
            yield Input(id="command-input", placeholder="What do you do?")

    def on_mount(self) -> None:
        self._append(self._engine.describe_current_room())
        self.query_one("#command-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value
        event.input.value = ""
        if not raw.strip():
            return
        self._append(f"> {raw}")
        result = self._engine.submit(raw)
        if result == QUIT_SENTINEL:
            self.exit()
            return
        self._append(result)

    def _append(self, text: str) -> None:
        self.last_output = text
        self.query_one("#prose", RichLog).write(text)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/tui/test_app.py -q`
Expected: 3 passed. If Textual's test harness triggers warnings about an event loop policy, that is acceptable. If tests hang, add a `timeout` to `run_test`.

- [ ] **Step 5: Commit**

```bash
git add if_fun/tui/app.py tests/tui/test_app.py pyproject.toml
git commit -m "feat(tui): add minimal Textual app (prose pane + input line)"
```

---

## Task 18: CLI entry point

**Files:**
- Create: `if_fun/cli.py`
- Test: `tests/test_cli.py`

`if_fun play` launches the TUI on the hardcoded 5-room world. Phase A has no world-generation; this is the only command that does anything real.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
from typer.testing import CliRunner

from if_fun.cli import app

runner = CliRunner()


def test_cli_shows_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "play" in result.stdout.lower()


def test_cli_play_command_exists() -> None:
    result = runner.invoke(app, ["play", "--help"])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/test_cli.py -q`
Expected: collection error.

- [ ] **Step 3: Implement**

`if_fun/cli.py`:

```python
"""CLI entry point. Phase A: only `if_fun play` is implemented."""

from __future__ import annotations

import typer

from if_fun.tui.app import IfFunApp
from if_fun.tui.turn_engine import TurnEngine
from if_fun.worlds.five_room import build_five_room_world

app = typer.Typer(help="Interactive Fiction game (Phase A walking skeleton).")


@app.command()
def play() -> None:
    """Launch the Textual TUI on the hardcoded 5-room world."""
    engine = TurnEngine(build_five_room_world())
    IfFunApp(engine).run()


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_cli.py -q`
Expected: 2 passed.

Also smoke-test manually (optional):

```bash
uv run if_fun --help
uv run if_fun play
# (press "quit" + Enter to exit)
```

- [ ] **Step 5: Commit**

```bash
git add if_fun/cli.py tests/test_cli.py
git commit -m "feat(cli): add typer entry point with `play` command"
```

---

## Task 19: Package-boundary enforcement test

**Files:**
- Create: `tests/architecture/__init__.py` (empty)
- Create: `tests/architecture/test_package_boundaries.py`

The invariant from spec §13.1: `world/`, `parser/`, and `save/` **must not import** from `agents/` or any LLM-calling code. Phase A has no LLM-calling code, but we enforce the boundary now so it holds as Phase B lands.

This is a purely static check. We walk the AST of every file in the three deterministic packages and assert no top-level import names match the forbidden prefixes.

- [ ] **Step 1: Write the failing test**

Create `tests/architecture/__init__.py` as empty. Create `tests/architecture/test_package_boundaries.py`:

```python
import ast
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DETERMINISTIC_PACKAGES = ["if_fun/world", "if_fun/parser", "if_fun/save"]
FORBIDDEN_PREFIXES = ("if_fun.agents",)


def _imports_in(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


@pytest.mark.parametrize("package", DETERMINISTIC_PACKAGES)
def test_deterministic_package_has_no_forbidden_imports(package: str) -> None:
    offences: list[str] = []
    pkg_path = REPO_ROOT / package
    for py_file in pkg_path.rglob("*.py"):
        for imp in _imports_in(py_file):
            if imp.startswith(FORBIDDEN_PREFIXES):
                offences.append(f"{py_file.relative_to(REPO_ROOT)}: imports {imp}")
    assert not offences, "forbidden imports found:\n" + "\n".join(offences)
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/architecture -q`
Expected: PASS — no current offences.

Now *verify the test actually catches violations* by temporarily adding `from if_fun.agents import map_verifier` to the top of `if_fun/world/state.py` and rerunning. Expected: FAIL. Remove the offending line and rerun. Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/architecture
git commit -m "test(architecture): enforce world/parser/save may not import agents/"
```

---

## Task 20: End-to-end smoke test

**Files:**
- Create: `tests/e2e/__init__.py` (empty)
- Create: `tests/e2e/test_smoke_five_room.py`

A scripted 10-command playthrough of the hardcoded world, asserting it wins. This catches the class of regression where individual components pass but the composition breaks.

- [ ] **Step 1: Write the test**

Create `tests/e2e/__init__.py` as empty. Create `tests/e2e/test_smoke_five_room.py`:

```python
from if_fun.tui.turn_engine import TurnEngine
from if_fun.worlds.five_room import build_five_room_world


WINNING_SCRIPT = [
    "east",              # entry_hall → vault
    "take brass_key",
    "west",              # vault → entry_hall
    "south",             # entry_hall → library
    "take silver_key",
    "take crystal",
    "north",             # library → entry_hall
    "north",             # entry_hall → ritual_chamber (requires brass_key)
    "north",             # ritual_chamber → treasury (requires silver_key)
]


def test_scripted_playthrough_wins() -> None:
    eng = TurnEngine(build_five_room_world())
    last = ""
    for cmd in WINNING_SCRIPT:
        last = eng.submit(cmd)
    assert eng.world.is_won(), f"final state not won; last output: {last}"
    assert "won" in last.lower()


def test_scripted_playthrough_fails_without_brass_key() -> None:
    eng = TurnEngine(build_five_room_world())
    out = eng.submit("north")  # locked without brass_key
    assert "can't" in out.lower()
    assert not eng.world.is_won()
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/e2e -q`
Expected: 2 passed.

- [ ] **Step 3: Full suite green check**

Run: `uv run pytest -q`
Expected: every test in the repo passes.

Run: `uv run pre-commit run --all-files`
Expected: every hook passes.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e
git commit -m "test(e2e): add scripted playthrough smoke test for five-room world"
```

---

## Task 21: Phase A wrap-up

**Files:**
- Modify: `README.md` (create if missing; describe how to run)

- [ ] **Step 1: Write a minimal README**

Create `README.md` with the following content:

```markdown
# if_fun

Interactive Fiction game in the Infocom tradition, built as a showcase of agentic AI patterns.

## Current status: Phase A (Walking Skeleton)

A deterministic substrate with a hardcoded 5-room test world. No LLM code yet.

## Running

```
uv sync
uv run if_fun play
```

Type `help` inside the game for commands.

## Development

```
uv run pre-commit run --all-files
uv run pytest
```

## Architecture

See `docs/architecture-overview.html` for the canonical design and `docs/superpowers/specs/2026-04-16-if-fun-design.md` for the spec.

Phase A implementation plan: `docs/superpowers/plans/2026-04-16-if-fun-phase-a-walking-skeleton.md`.
```

- [ ] **Step 2: Final gate check**

Run in sequence:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest -q
uv run pre-commit run --all-files
```

All must be green.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Phase A README"
```

- [ ] **Step 4: Push**

```bash
git push
```

---

## Phase A Exit Gate

Phase A is complete when all of the following hold:

- Every task above is committed on `main`.
- `uv run pre-commit run --all-files` passes.
- `uv run pytest -q` passes with zero LLM calls and zero network access.
- `uv run if_fun play` launches the TUI and allows winning the five-room world by hand.
- The package boundary test passes (no `if_fun.world`, `if_fun.parser`, or `if_fun.save` module imports from `if_fun.agents`).

Phase B (Agentic Generation) begins with a fresh plan document.
