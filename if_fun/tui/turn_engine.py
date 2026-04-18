"""Turn engine: parser + state store + save/load. No UI, no LLM."""

from typing import assert_never

from if_fun.ids import Direction, ItemId
from if_fun.parser.grammar import MetaVerb
from if_fun.parser.parser import DirectionCommand, MetaCommand, ParseError, parse
from if_fun.save.save_format import read_save, write_save
from if_fun.world.effects import AddItemToRoomEffect, RemoveItemFromInventoryEffect
from if_fun.world.state import WorldState
from if_fun.world.store import (
    DirectionStatus,
    IllegalAction,
    apply_action,
    apply_direction,
    apply_transition,
    classify_direction,
    find_transition,
)
from if_fun.world.transitions import Action, DirectionTrigger, Transition, VerbObjectTrigger

WIN_MESSAGE = "\n** You have won. **"
GAME_OVER_MESSAGE = (
    "The game is over. Type 'quit' to exit, or 'save <slot>' to preserve your state."
)
QUIT_SENTINEL = "__QUIT__"


class TurnEngine:
    def __init__(self, world: WorldState) -> None:
        self._world = world

    @property
    def world(self) -> WorldState:
        return self._world

    def describe_current_room(self) -> str:
        room = self._world.rooms[self._world.player.location]
        exits = self._render_exits()
        items = self._render_item_list(room.items_present) or "none"
        return f"[{room.id}]\n{room.description}\n\nExits: {exits}\nItems: {items}"

    def _render_item_list(self, ids: frozenset[ItemId] | set[ItemId]) -> str:
        """Render a collection of item ids as a comma-separated display string.

        Falls back to the raw id if no ItemDef is registered — keeps tests
        for worlds without an item registry working.
        """
        parts: list[str] = []
        for item_id in sorted(ids):
            definition = self._world.items.get(item_id)
            parts.append(definition.indefinite() if definition is not None else str(item_id))
        return ", ".join(parts)

    def _render_exits(self) -> str:
        room = self._world.rooms[self._world.player.location]
        # Union of bare exits and any declared DirectionTrigger transitions —
        # a room may list a locked door *only* as a guarded transition with no
        # entry in the exits dict, and we still want to surface it.
        directions: list[Direction] = []
        seen: set[Direction] = set()
        for d in room.exits:
            if d not in seen:
                directions.append(d)
                seen.add(d)
        for tr in room.transitions:
            if isinstance(tr.trigger, DirectionTrigger) and tr.trigger.direction not in seen:
                directions.append(tr.trigger.direction)
                seen.add(tr.trigger.direction)

        if not directions:
            return "none"

        parts: list[str] = []
        for d in directions:
            status = classify_direction(self._world, d)
            if status is DirectionStatus.LOCKED:
                parts.append(f"{d.value} (locked)")
            else:
                parts.append(d.value)
        return ", ".join(parts)

    def submit(self, raw_input: str) -> str:
        cmd = parse(raw_input)

        if isinstance(cmd, ParseError):
            return f"I don't understand that. ({cmd.message})"

        if isinstance(cmd, MetaCommand):
            return self._handle_meta(cmd)

        # After a win, the world is frozen for non-meta interaction.
        # Meta commands (save/load/quit/help) still work above this gate.
        if self._world.is_won():
            return GAME_OVER_MESSAGE

        if isinstance(cmd, DirectionCommand):
            try:
                self._world = apply_direction(self._world, cmd.direction)
            except IllegalAction:
                if classify_direction(self._world, cmd.direction) is DirectionStatus.LOCKED:
                    return f"The way {cmd.direction.value} is locked."
                return "You can't go that way."
            return self._post_turn()

        if isinstance(cmd, Action):
            if cmd.verb == "look" and cmd.direct_object is None:
                return self.describe_current_room()
            if cmd.verb == "inventory" and cmd.direct_object is None:
                items = self._render_item_list(self._world.player.inventory) or "nothing"
                return f"You carry: {items}"
            if cmd.verb == "open":
                return self._handle_open(cmd)
            if cmd.verb == "unlock":
                return self._handle_unlock(cmd)
            if cmd.verb == "drop":
                return self._handle_drop(cmd)
            if cmd.verb == "examine":
                return self._handle_examine(cmd)

            matched = find_transition(self._world, cmd)
            try:
                self._world = apply_action(self._world, cmd)
            except IllegalAction:
                return "You can't do that."
            return self._post_turn(narration=matched.narration_hint if matched else None)

        # Static exhaustiveness over ParsedCommand: if the union grows, ty
        # flags this call site before runtime.
        assert_never(cmd)

    def save(self, slot: str) -> None:
        write_save(slot, self._world)

    def load(self, slot: str) -> None:
        self._world = read_save(slot)

    def _handle_meta(self, cmd: MetaCommand) -> str:
        if cmd.verb is MetaVerb.QUIT:
            return QUIT_SENTINEL
        if cmd.verb is MetaVerb.HELP:
            return (
                "Verbs: look, take <item>, drop <item>, examine <item>, "
                "open <direction>, unlock <direction>, inventory.\n"
                "Directions: n, s, e, w, u, d (or 'go north' etc.).\n"
                "Meta: save <slot>, load <slot>, quit, help."
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

    def _handle_open(self, cmd: Action) -> str:
        d = self._direction_argument(cmd)
        if d is None:
            return "What do you want to open? Try 'open <direction>'."
        status = classify_direction(self._world, d)
        if status is DirectionStatus.LOCKED:
            return f"The way {d.value} is locked."
        if status is DirectionStatus.WALL:
            return "You see nothing to open."
        return f"There is nothing to open to the {d.value}."

    def _handle_examine(self, cmd: Action) -> str:
        if cmd.direct_object is None:
            return "What do you want to examine?"
        item_id = ItemId(str(cmd.direct_object))
        here = self._world.rooms[self._world.player.location]
        visible = item_id in self._world.player.inventory or item_id in here.items_present
        if not visible:
            return "You don't see that here."
        definition = self._world.items.get(item_id)
        if definition is None:
            # Item is visible but has no registered ItemDef — fall back to the id.
            return str(item_id)
        return definition.short_description

    def _handle_drop(self, cmd: Action) -> str:
        if cmd.direct_object is None:
            return "What do you want to drop?"
        item_id = ItemId(str(cmd.direct_object))
        if item_id not in self._world.player.inventory:
            return "You aren't carrying that."

        room_id = self._world.player.location
        tr = Transition(
            id=f"_drop_{item_id}",
            name=f"drop {item_id}",
            trigger=VerbObjectTrigger(verb="drop", direct_object=item_id),
            guards=[],
            effects=[
                RemoveItemFromInventoryEffect(item_id=item_id),
                AddItemToRoomEffect(room_id=room_id, item_id=item_id),
            ],
            narration_hint="Dropped.",
        )
        self._world = apply_transition(self._world, tr)
        return f"Dropped.\n{self.describe_current_room()}"

    def _handle_unlock(self, cmd: Action) -> str:
        d = self._direction_argument(cmd)
        if d is None:
            return "What do you want to unlock? Try 'unlock <direction>'."
        status = classify_direction(self._world, d)
        if status is DirectionStatus.LOCKED:
            return f"The way {d.value} is locked. You'll need the right key."
        if status is DirectionStatus.WALL:
            return "You see nothing to unlock."
        return f"The way {d.value} isn't locked."

    @staticmethod
    def _direction_argument(cmd: Action) -> Direction | None:
        """Interpret cmd.direct_object as a direction token, if possible.

        The parser wraps any post-verb tokens as an ItemId regardless of type,
        so we re-parse the string value here before dispatching direction
        semantics.
        """
        if cmd.direct_object is None:
            return None
        return Direction.from_token(str(cmd.direct_object))

    def _post_turn(self, narration: str | None = None) -> str:
        text = self.describe_current_room()
        if narration:
            text = f"{narration}\n{text}"
        if self._world.is_won():
            text += WIN_MESSAGE
        return text
