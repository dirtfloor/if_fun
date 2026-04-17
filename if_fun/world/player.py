"""Player character state.

PlayerState is frozen (fields cannot be reassigned), but ``flags`` is a
plain dict — its contents remain mutable. Callers should not rely on deep
immutability. PlayerState instances are never hashable because ``flags``
is a dict; do not use them as dict keys or set members.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import ItemId, RoomId


class PlayerState(BaseModel):
    model_config = ConfigDict(frozen=True)

    location: RoomId
    inventory: frozenset[ItemId] = Field(default_factory=lambda: frozenset())
    flags: dict[str, Any] = Field(default_factory=dict)
