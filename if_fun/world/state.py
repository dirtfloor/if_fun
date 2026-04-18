"""Top-level WorldState and WinCondition."""

from typing import Any, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field

from if_fun.ids import ItemId, RoomId
from if_fun.world.events import Event
from if_fun.world.items import ItemDef
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
    items: dict[ItemId, ItemDef] = Field(default_factory=dict)
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
                return (
                    self.globals.get(self.win_condition.args["flag"])
                    == self.win_condition.args["value"]
                )
            case "has_item":
                return self.win_condition.args["item_id"] in self.player.inventory
            case _ as unreachable:
                assert_never(unreachable)
