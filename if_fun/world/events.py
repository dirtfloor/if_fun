"""Event records appended to the world event log."""

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
