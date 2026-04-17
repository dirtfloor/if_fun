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

Locked doors are modeled as bare-exit geometry plus a guarded DirectionTrigger
transition. find_direction_transition prefers the explicit transition, so the
lock is not bypassed even though the geometric connection is declared.

Win condition: player reaches treasury.
"""

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
            Direction.NORTH: RoomId("ritual_chamber"),
        },
        transitions=(_locked_north("entry_hall", "ritual_chamber", "brass_key"),),
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
        exits={
            Direction.SOUTH: RoomId("entry_hall"),
            Direction.NORTH: RoomId("treasury"),
        },
        transitions=(_locked_north("ritual_chamber", "treasury", "silver_key"),),
    )
    treasury = RoomState(
        id=RoomId("treasury"),
        description="Gold gleams in torchlight. You have found the treasury.",
        exits={Direction.SOUTH: RoomId("ritual_chamber")},
    )

    rooms = {r.id: r for r in (entry_hall, vault, library, ritual_chamber, treasury)}

    return WorldState(
        rooms=rooms,
        player=PlayerState(location=RoomId("entry_hall")),
        win_condition=WinCondition(kind="player_in_room", args={"room_id": "treasury"}),
    )
