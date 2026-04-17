"""Player character state."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import ItemId, RoomId


class PlayerState(BaseModel):
    model_config = ConfigDict(frozen=True)

    location: RoomId
    inventory: frozenset[ItemId] = Field(default_factory=lambda: frozenset())
    flags: dict[str, Any] = Field(default_factory=dict)
