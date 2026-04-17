"""Room state.

For Phase A, RoomState combines static structural data (id, description,
exits, transitions) with dynamic fields (visited, items_present, occupants,
event_ids, flags). A later phase may split these into RoomDef + RoomState
when generation lands; the design spec's §5.1 only mandates the dynamic
fields, so we extend it for Phase A convenience.

RoomState is frozen. ``items_present`` and ``occupants`` are frozensets
for deep immutability; ``flags`` is a dict whose contents remain mutable.
"""

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
    items_present: frozenset[ItemId] = Field(default_factory=lambda: frozenset())
    occupants: frozenset[MobId] = Field(default_factory=lambda: frozenset())
    event_ids: tuple[EventId, ...] = ()
    flags: dict[str, Any] = Field(default_factory=dict)
