"""Triggers, Actions, and Transitions."""

from typing import Annotated, Literal

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
    VerbObjectTrigger | DirectionTrigger | TimeTrigger,
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
